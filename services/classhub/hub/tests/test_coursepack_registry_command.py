from io import BytesIO, StringIO
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from ._shared import *  # noqa: F401,F403
from ..services.coursepack_import import CoursepackImportResult, import_coursepack_registry
from ..services.coursepack_registry import RegistrySource
from ..services.coursepack_registry import build_registry_entry, new_registry_document, upsert_registry_entry, write_registry_document


class RegistryCoursepackImportCommandTests(TestCase):
    def _coursepack_zip(self, *, slug: str, title: str) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                f"{slug}/course.yaml",
                f"""slug: {slug}
title: "{title}"
ui_level: advanced
program_profile: advanced
lessons:
  - session: 1
    slug: s01-build
    title: "Build"
    file: lessons/01-build.md
""",
            )
            archive.writestr(
                f"{slug}/lessons/01-build.md",
                f"""---
course: {slug}
session: 1
slug: s01-build
title: "Build"
submission:
  type: file
  accepted:
    - .sb3
---
# Build
""",
            )
        return buffer.getvalue()

    def _write_registry_index(self, *, root: Path, slug: str, title: str, version: str) -> Path:
        courses_root = root / "courses"
        course_dir = courses_root / slug
        course_dir.mkdir(parents=True)
        (course_dir / "course.yaml").write_text(
            f"""slug: {slug}
title: "{title}"
ui_level: advanced
program_profile: advanced
lessons:
  - session: 1
    slug: s01-build
    title: "Build"
    file: lessons/01-build.md
""",
            encoding="utf-8",
        )

        artifact_dir = root / "registry" / "artifacts"
        artifact_dir.mkdir(parents=True)
        artifact_path = artifact_dir / f"{slug}_{version}.zip"
        artifact_path.write_bytes(self._coursepack_zip(slug=slug, title=title))

        entry = build_registry_entry(
            slug=slug,
            artifact_path=artifact_path,
            version=version,
            artifact_url=f"artifacts/{artifact_path.name}",
            source_url=f"https://example.org/coursepacks/{slug}",
            sdk_version="0.1.0",
            courses_root=courses_root,
        )
        payload = upsert_registry_entry(new_registry_document(), entry)
        index_path = root / "registry" / "index.json"
        write_registry_document(index_path, payload)
        return index_path

    def test_command_imports_requested_registry_version_into_created_class(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = self._write_registry_index(
                root=root,
                slug="registry_import_course",
                title="Registry Import Course",
                version="20260608T210000Z",
            )
            content_root = root / "content"

            with override_settings(CONTENT_ROOT=content_root):
                out = StringIO()
                call_command(
                    "import_coursepack_registry",
                    index=index_path.as_uri(),
                    course_slug="registry_import_course",
                    registry_version="20260608T210000Z",
                    class_name="Registry Cohort",
                    create_class=True,
                    stdout=out,
                )

            classroom = Class.objects.get(name="Registry Cohort")
            self.assertTrue((content_root / "courses" / "registry_import_course" / "course.yaml").exists())
            self.assertEqual(classroom.modules.count(), 1)
            self.assertTrue(Material.objects.filter(module__classroom=classroom, title="Open lesson").exists())
            self.assertTrue(Material.objects.filter(module__classroom=classroom, title="Homework dropbox").exists())
            self.assertIn("Version: 20260608T210000Z", out.getvalue())
            event = AuditEvent.objects.filter(action="coursepack.registry.import", classroom=classroom).first()
            self.assertIsNotNone(event)
            self.assertIsNone(event.actor_user_id)
            self.assertEqual(event.metadata["import_channel"], "management_command")
            self.assertEqual(event.metadata["source_metadata"]["registry_version"], "20260608T210000Z")

    def test_command_errors_when_registry_entry_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = self._write_registry_index(
                root=root,
                slug="registry_import_course",
                title="Registry Import Course",
                version="20260608T210000Z",
            )
            content_root = root / "content"

            with override_settings(CONTENT_ROOT=content_root):
                with self.assertRaises(CommandError):
                    call_command(
                        "import_coursepack_registry",
                        index=index_path.as_uri(),
                        course_slug="missing_course",
                        class_name="Missing Registry Cohort",
                        create_class=True,
                    )

    @patch("hub.services.coursepack_import.import_coursepack_zip")
    @patch("hub.services.coursepack_import.fetch_registry_artifact")
    @patch("hub.services.coursepack_import.select_registry_entry")
    @patch("hub.services.coursepack_import.read_registry_document")
    def test_import_service_uses_deterministic_registry_download_name(
        self,
        read_registry_document_mock,
        select_registry_entry_mock,
        fetch_registry_artifact_mock,
        import_coursepack_zip_mock,
    ):
        classroom = Class.objects.create(name="Registry Deterministic Cohort", join_code="RGSAFE01")
        read_registry_document_mock.return_value = (
            new_registry_document(),
            RegistrySource(location="/tmp/index.json", base_path=Path("/tmp")),
        )
        select_registry_entry_mock.return_value = {
            "slug": "registry_import_course",
            "title": "Registry Import Course",
            "version": "20260609T040000Z",
            "artifact": {
                "url": "artifacts/registry_import_course.zip",
                "filename": "../../escape.zip",
                "sha256": "a" * 64,
                "bytes": 4,
                "checksum_url": "artifacts/registry_import_course.zip.sha256",
            },
        }

        def _fake_fetch(_source, _entry, *, output_path):
            self.assertEqual(output_path.name, "registry-import.zip")
            output_path.write_bytes(b"PK\x03\x04")
            return {
                "source_artifact_url": "artifacts/registry_import_course.zip",
                "resolved_artifact_location": "/tmp/registry/artifacts/registry_import_course.zip",
                "resolved_checksum_location": "/tmp/registry/artifacts/registry_import_course.zip.sha256",
                "sha256": "a" * 64,
                "bytes": 4,
            }

        fetch_registry_artifact_mock.side_effect = _fake_fetch
        import_coursepack_zip_mock.return_value = CoursepackImportResult(
            course_slug="registry_import_course",
            course_title="Registry Import Course",
            classroom=classroom,
            course_dir=Path("/tmp/content/courses/registry_import_course"),
            created_modules=1,
            created_materials=2,
            created_assets=0,
        )

        result = import_coursepack_registry(
            index_location="/tmp/index.json",
            course_slug="registry_import_course",
            version="20260609T040000Z",
            class_name="Registry Deterministic Cohort",
            create_class=True,
        )

        self.assertEqual(result.course_slug, "registry_import_course")
