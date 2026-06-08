from io import BytesIO, StringIO
import tempfile
import zipfile
from pathlib import Path

from ._shared import *  # noqa: F401,F403
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
                    index=str(index_path),
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
                        index=str(index_path),
                        course_slug="missing_course",
                        class_name="Missing Registry Cohort",
                        create_class=True,
                    )
