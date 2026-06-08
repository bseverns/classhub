from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from hub.services.coursepack_registry import (
    build_registry_entry,
    fetch_registry_artifact,
    new_registry_document,
    read_registry_document,
    select_registry_entry,
    upsert_registry_entry,
    validate_registry_document,
    write_registry_document,
)


class CoursepackRegistryServiceTests(SimpleTestCase):
    def test_build_registry_entry_writes_checksum_and_exposes_compatibility_metadata(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            courses_root = root / "courses"
            course_dir = courses_root / "demo_course"
            course_dir.mkdir(parents=True)
            (course_dir / "course.yaml").write_text(
                "\n".join(
                    [
                        'slug: "demo_course"',
                        'title: "Demo Course"',
                        'ui_level: "secondary"',
                        'program_profile: "advanced"',
                        "lessons:",
                        '  - slug: "s01-demo"',
                        '    title: "Demo Lesson"',
                        '    file: "lessons/01-demo.md"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            artifact_path = root / "demo_course_20260608T120000Z.zip"
            artifact_path.write_bytes(b"demo artifact")

            entry = build_registry_entry(
                slug="demo_course",
                artifact_path=artifact_path,
                version="20260608T120000Z",
                artifact_url="artifacts/demo_course_20260608T120000Z.zip",
                source_url="https://example.org/coursepacks/demo_course",
                sdk_version="0.1.0",
                courses_root=courses_root,
            )

            self.assertEqual(entry["slug"], "demo_course")
            self.assertEqual(entry["version"], "20260608T120000Z")
            self.assertEqual(entry["compatibility"]["ui_level"], "secondary")
            self.assertEqual(entry["compatibility"]["program_profile"], "advanced")
            self.assertEqual(
                entry["artifact"]["checksum_url"],
                "artifacts/demo_course_20260608T120000Z.zip.sha256",
            )
            checksum_path = Path(entry["checksum_file"])
            self.assertTrue(checksum_path.exists())
            self.assertIn(artifact_path.name, checksum_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_registry_document(new_registry_document(entries=[entry])), [])

    def test_local_registry_fetch_verifies_checksum_and_writes_download_copy(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            courses_root = root / "courses"
            course_dir = courses_root / "demo_course"
            course_dir.mkdir(parents=True)
            (course_dir / "course.yaml").write_text(
                "\n".join(
                    [
                        'slug: "demo_course"',
                        'title: "Demo Course"',
                        'ui_level: "secondary"',
                        'program_profile: "secondary"',
                        "lessons:",
                        '  - slug: "s01-demo"',
                        '    title: "Demo Lesson"',
                        '    file: "lessons/01-demo.md"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            artifact_dir = root / "registry" / "artifacts"
            artifact_dir.mkdir(parents=True)
            artifact_path = artifact_dir / "demo_course_20260608T120000Z.zip"
            artifact_path.write_bytes(b"registry artifact")

            entry = build_registry_entry(
                slug="demo_course",
                artifact_path=artifact_path,
                version="20260608T120000Z",
                artifact_url="artifacts/demo_course_20260608T120000Z.zip",
                source_url="https://example.org/coursepacks/demo_course",
                sdk_version="0.1.0",
                courses_root=courses_root,
            )
            index_path = root / "registry" / "index.json"
            payload = upsert_registry_entry(new_registry_document(), entry)
            write_registry_document(index_path, payload)

            read_payload, source = read_registry_document(str(index_path))
            selected = select_registry_entry(read_payload, slug="demo_course", version="20260608T120000Z")
            result = fetch_registry_artifact(
                source,
                selected,
                output_path=root / "downloads" / "demo_course_download.zip",
            )

            self.assertEqual(result["slug"], "demo_course")
            self.assertTrue(Path(result["artifact"]).exists())
            self.assertTrue(Path(result["checksum_file"]).exists())
            self.assertEqual(Path(result["artifact"]).read_bytes(), b"registry artifact")
            self.assertEqual(
                json.loads(index_path.read_text(encoding="utf-8"))["entries"][0]["artifact"]["url"],
                "artifacts/demo_course_20260608T120000Z.zip",
            )

    def test_select_registry_entry_prefers_newest_generated_at_when_version_omitted(self):
        payload = {
            "schema_version": "2026-06-08",
            "generated_at": "2026-06-08T12:00:00Z",
            "entries": [
                {
                    "slug": "demo_course",
                    "title": "Demo Course",
                    "version": "1.0.0",
                    "release_channel": "stable",
                    "source_url": "https://example.org/coursepacks/demo_course",
                    "generated_at": "2026-06-08T11:00:00Z",
                    "compatibility": {"ui_level": "secondary", "program_profile": "secondary"},
                    "artifact": {
                        "url": "artifacts/demo_course_1.0.0.zip",
                        "sha256": "a" * 64,
                        "bytes": 10,
                        "checksum_url": "artifacts/demo_course_1.0.0.zip.sha256",
                        "filename": "demo_course_1.0.0.zip",
                    },
                },
                {
                    "slug": "demo_course",
                    "title": "Demo Course",
                    "version": "0.9.9",
                    "release_channel": "stable",
                    "source_url": "https://example.org/coursepacks/demo_course",
                    "generated_at": "2026-06-08T12:30:00Z",
                    "compatibility": {"ui_level": "secondary", "program_profile": "secondary"},
                    "artifact": {
                        "url": "artifacts/demo_course_0.9.9.zip",
                        "sha256": "b" * 64,
                        "bytes": 10,
                        "checksum_url": "artifacts/demo_course_0.9.9.zip.sha256",
                        "filename": "demo_course_0.9.9.zip",
                    },
                },
            ],
        }

        selected = select_registry_entry(payload, slug="demo_course")

        self.assertEqual(selected["version"], "0.9.9")
