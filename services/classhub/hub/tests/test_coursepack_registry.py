from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from hub.services.coursepack_registry import (
    CoursepackRegistryError,
    RegistrySource,
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

            read_payload, source = read_registry_document(index_path.as_uri())
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

    @override_settings(CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"])
    @patch("hub.services.coursepack_registry.urlopen")
    def test_read_registry_document_allows_allowlisted_https_host(self, urlopen_mock):
        response = Mock()
        response.read.return_value = json.dumps(new_registry_document()).encode("utf-8")
        urlopen_mock.return_value.__enter__.return_value = response

        payload, source = read_registry_document("https://registry.example.org/index.json")

        self.assertEqual(payload["entries"], [])
        self.assertEqual(source.base_url, "https://registry.example.org/index.json")
        urlopen_mock.assert_called_once_with("https://registry.example.org/index.json")

    @patch("hub.services.coursepack_registry.urlopen")
    def test_read_registry_document_rejects_unallowlisted_https_host_before_fetch(self, urlopen_mock):
        with self.assertRaises(CoursepackRegistryError) as exc:
            read_registry_document("https://registry.example.org/index.json")

        self.assertIn("Remote registry fetch is disabled", str(exc.exception))
        urlopen_mock.assert_not_called()

    def test_read_registry_document_rejects_absolute_local_path_without_file_url(self):
        with TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "index.json"
            index_path.write_text(json.dumps(new_registry_document()), encoding="utf-8")

            with self.assertRaises(CoursepackRegistryError) as exc:
                read_registry_document(str(index_path))

        self.assertIn("absolute local paths must use file://", str(exc.exception))

    @override_settings(CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"])
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_rejects_cross_origin_remote_artifact_url(self, urlopen_mock):
        source = RegistrySource(
            location="https://registry.example.org/index.json",
            base_url="https://registry.example.org/index.json",
        )
        entry = {
            "slug": "demo_course",
            "version": "20260609T010000Z",
            "artifact": {
                "url": "https://evil.example.org/demo.zip",
                "sha256": "a" * 64,
                "bytes": 4,
                "checksum_url": "https://evil.example.org/demo.zip.sha256",
            },
        }

        with self.assertRaises(CoursepackRegistryError) as exc:
            fetch_registry_artifact(source, entry)

        self.assertIn("not in CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS", str(exc.exception))
        urlopen_mock.assert_not_called()

    def test_fetch_registry_artifact_rejects_local_absolute_path_escape(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry_root = root / "registry"
            registry_root.mkdir(parents=True)
            source = RegistrySource(location=str(registry_root / "index.json"), base_path=registry_root)
            entry = {
                "slug": "demo_course",
                "version": "20260609T020000Z",
                "artifact": {
                    "url": "/etc/passwd",
                    "sha256": "a" * 64,
                    "bytes": 4,
                    "checksum_url": "artifacts/demo.zip.sha256",
                },
            }

            with self.assertRaises(CoursepackRegistryError) as exc:
                fetch_registry_artifact(source, entry)

            self.assertIn("relative path inside the registry directory", str(exc.exception))
