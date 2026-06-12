from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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


class FakeHTTPResponse:
    def __init__(
        self,
        payload: bytes = b"",
        *,
        chunks: list[bytes] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.headers = headers or {}
        self._chunks = list(chunks) if chunks is not None else [payload]

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False

    def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


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

    @override_settings(
        CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"],
        CLASSHUB_COURSEPACK_REGISTRY_FETCH_TIMEOUT_SECONDS=7,
    )
    @patch("hub.services.coursepack_registry.urlopen")
    def test_read_registry_document_allows_allowlisted_https_host(self, urlopen_mock):
        payload = json.dumps(new_registry_document()).encode("utf-8")
        urlopen_mock.return_value = FakeHTTPResponse(
            payload,
            headers={"Content-Length": str(len(payload))},
        )

        payload, source = read_registry_document("https://registry.example.org/index.json")

        self.assertEqual(payload["entries"], [])
        self.assertEqual(source.base_url, "https://registry.example.org/index.json")
        urlopen_mock.assert_called_once_with("https://registry.example.org/index.json", timeout=7)

    @override_settings(
        CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"],
        CLASSHUB_COURSEPACK_REGISTRY_INDEX_MAX_BYTES=4,
    )
    @patch("hub.services.coursepack_registry.urlopen")
    def test_read_registry_document_rejects_remote_index_content_length_over_limit(self, urlopen_mock):
        urlopen_mock.return_value = FakeHTTPResponse(
            b"{}",
            headers={"Content-Length": "5"},
        )

        with self.assertRaises(CoursepackRegistryError) as exc:
            read_registry_document("https://registry.example.org/index.json")

        self.assertIn("Registry index response is too large", str(exc.exception))

    @override_settings(
        CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"],
        CLASSHUB_COURSEPACK_REGISTRY_INDEX_MAX_BYTES=4,
    )
    @patch("hub.services.coursepack_registry.urlopen")
    def test_read_registry_document_rejects_remote_index_stream_over_limit(self, urlopen_mock):
        urlopen_mock.return_value = FakeHTTPResponse(chunks=[b"1234", b"5"])

        with self.assertRaises(CoursepackRegistryError) as exc:
            read_registry_document("https://registry.example.org/index.json")

        self.assertIn("Registry index response exceeded limit 4 bytes", str(exc.exception))

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

    @override_settings(
        CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"],
        CLASSHUB_COURSEPACK_REGISTRY_FETCH_TIMEOUT_SECONDS=9,
    )
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_streams_remote_payload_and_verifies_checksum_sidecar(self, urlopen_mock):
        with TemporaryDirectory() as tmpdir:
            payload = b"registry artifact"
            digest = hashlib.sha256(payload).hexdigest()
            source = RegistrySource(
                location="https://registry.example.org/index.json",
                base_url="https://registry.example.org/index.json",
            )
            entry = {
                "slug": "demo_course",
                "version": "20260609T030000Z",
                "artifact": {
                    "url": "artifacts/demo.zip",
                    "sha256": digest,
                    "bytes": len(payload),
                    "checksum_url": "artifacts/demo.zip.sha256",
                    "filename": "demo.zip",
                },
            }
            checksum_payload = f"{digest}  demo.zip\n".encode("utf-8")
            urlopen_mock.side_effect = [
                FakeHTTPResponse(
                    checksum_payload,
                    headers={"Content-Length": str(len(checksum_payload))},
                ),
                FakeHTTPResponse(
                    chunks=[b"registry ", b"artifact"],
                    headers={"Content-Length": str(len(payload))},
                ),
            ]

            result = fetch_registry_artifact(
                source,
                entry,
                output_path=Path(tmpdir) / "download.zip",
            )

            self.assertEqual(result["bytes"], len(payload))
            self.assertEqual(result["sha256"], digest)
            self.assertEqual(Path(result["artifact"]).read_bytes(), payload)
            self.assertEqual(urlopen_mock.call_count, 2)
            urlopen_mock.assert_any_call("https://registry.example.org/artifacts/demo.zip.sha256", timeout=9)
            urlopen_mock.assert_any_call("https://registry.example.org/artifacts/demo.zip", timeout=9)

    @override_settings(CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"])
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_rejects_remote_checksum_sidecar_mismatch(self, urlopen_mock):
        payload = b"registry artifact"
        digest = hashlib.sha256(payload).hexdigest()
        source = RegistrySource(
            location="https://registry.example.org/index.json",
            base_url="https://registry.example.org/index.json",
        )
        entry = {
            "slug": "demo_course",
            "version": "20260609T040000Z",
            "artifact": {
                "url": "artifacts/demo.zip",
                "sha256": digest,
                "bytes": len(payload),
                "checksum_url": "artifacts/demo.zip.sha256",
            },
        }
        urlopen_mock.return_value = FakeHTTPResponse((("b" * 64) + "  demo.zip\n").encode("utf-8"))

        with self.assertRaises(CoursepackRegistryError) as exc:
            fetch_registry_artifact(source, entry)

        self.assertIn("checksum sidecar does not match", str(exc.exception))
        self.assertEqual(urlopen_mock.call_count, 1)

    @override_settings(
        CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"],
        CLASSHUB_COURSEPACK_REGISTRY_ARTIFACT_MAX_BYTES=3,
    )
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_rejects_declared_size_over_configured_limit(self, urlopen_mock):
        payload = b"abcd"
        digest = hashlib.sha256(payload).hexdigest()
        source = RegistrySource(
            location="https://registry.example.org/index.json",
            base_url="https://registry.example.org/index.json",
        )
        entry = {
            "slug": "demo_course",
            "version": "20260609T045000Z",
            "artifact": {
                "url": "artifacts/demo.zip",
                "sha256": digest,
                "bytes": len(payload),
                "checksum_url": "artifacts/demo.zip.sha256",
            },
        }

        with self.assertRaises(CoursepackRegistryError) as exc:
            fetch_registry_artifact(source, entry)

        self.assertIn("declared size 4 bytes exceeds limit 3", str(exc.exception))
        urlopen_mock.assert_not_called()

    @override_settings(CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"])
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_rejects_remote_content_length_over_expected_size(self, urlopen_mock):
        with TemporaryDirectory() as tmpdir:
            payload = b"abcd"
            digest = hashlib.sha256(payload).hexdigest()
            source = RegistrySource(
                location="https://registry.example.org/index.json",
                base_url="https://registry.example.org/index.json",
            )
            entry = {
                "slug": "demo_course",
                "version": "20260609T050000Z",
                "artifact": {
                    "url": "artifacts/demo.zip",
                    "sha256": digest,
                    "bytes": len(payload),
                    "checksum_url": "artifacts/demo.zip.sha256",
                },
            }
            urlopen_mock.side_effect = [
                FakeHTTPResponse(f"{digest}  demo.zip\n".encode("utf-8")),
                FakeHTTPResponse(b"abcde", headers={"Content-Length": "5"}),
            ]

            with self.assertRaises(CoursepackRegistryError) as exc:
                fetch_registry_artifact(
                    source,
                    entry,
                    output_path=Path(tmpdir) / "download.zip",
                )

        self.assertIn("Registry artifact response is too large", str(exc.exception))

    @override_settings(CLASSHUB_COURSEPACK_REGISTRY_ALLOWED_HOSTS=["registry.example.org"])
    @patch("hub.services.coursepack_registry.urlopen")
    def test_fetch_registry_artifact_rejects_remote_stream_over_expected_size(self, urlopen_mock):
        with TemporaryDirectory() as tmpdir:
            payload = b"abcd"
            digest = hashlib.sha256(payload).hexdigest()
            output_path = Path(tmpdir) / "download.zip"
            source = RegistrySource(
                location="https://registry.example.org/index.json",
                base_url="https://registry.example.org/index.json",
            )
            entry = {
                "slug": "demo_course",
                "version": "20260609T060000Z",
                "artifact": {
                    "url": "artifacts/demo.zip",
                    "sha256": digest,
                    "bytes": len(payload),
                    "checksum_url": "artifacts/demo.zip.sha256",
                },
            }
            urlopen_mock.side_effect = [
                FakeHTTPResponse(f"{digest}  demo.zip\n".encode("utf-8")),
                FakeHTTPResponse(chunks=[b"abcd", b"e"]),
            ]

            with self.assertRaises(CoursepackRegistryError) as exc:
                fetch_registry_artifact(source, entry, output_path=output_path)

            self.assertFalse(output_path.exists())

        self.assertIn("Registry artifact response exceeded limit 4 bytes", str(exc.exception))

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
