import zipfile
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from common.request_safety import fixed_window_allow, token_bucket_allow

from .middleware import StudentSessionMiddleware
from .models import Class, Material, StudentIdentity
from .services.markdown_content import (
    load_course_manifest,
    load_lesson_markdown,
    render_markdown_to_safe_html,
    split_lesson_markdown_for_audiences,
)
from .services.content_links import (
    build_asset_url,
    normalize_lesson_videos,
    parse_course_lesson_url,
)
from .services.filenames import safe_filename
from .services.ip_privacy import minimize_student_event_ip
from .services.release_state import (
    lesson_available_on,
    lesson_release_state,
    parse_release_date,
)
from .services.teacher_tracker import _build_lesson_tracker_rows
from .services.upload_policy import (
    front_matter_submission,
    parse_extensions,
)
from .services.upload_scan import scan_uploaded_file
from .services.upload_validation import validate_upload_content
from .services.zip_exports import (
    reserve_archive_path,
    temporary_zip_archive,
    write_submission_file_to_archive,
)


def _sample_sb3_upload() -> SimpleUploadedFile:
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", '{"targets":[],"meta":{"semver":"3.0.0"}}')
    return SimpleUploadedFile("project.sb3", buf.getvalue())


class UploadPolicyServiceTests(SimpleTestCase):
    def test_parse_extensions_normalizes_unique_list(self):
        self.assertEqual(parse_extensions("sb3, .PNG, .sb3"), [".sb3", ".png"])

    def test_front_matter_submission_parses_pipe_or_csv(self):
        row = front_matter_submission(
            {
                "submission": {
                    "type": "file",
                    "accepted": "sb3|png",
                    "naming": "studentname_session",
                }
            }
        )
        self.assertEqual(row["type"], "file")
        self.assertEqual(row["accepted_exts"], [".sb3", ".png"])
        self.assertEqual(row["naming"], "studentname_session")


class _FailingCache:
    def get(self, key):
        raise RuntimeError("cache down")

    def set(self, key, value, timeout=None):
        raise RuntimeError("cache down")

    def incr(self, key):
        raise RuntimeError("cache down")


class _CorruptCache:
    def __init__(self, value):
        self.value = value

    def get(self, key):
        return self.value

    def set(self, key, value, timeout=None):
        self.value = value

    def incr(self, key):
        raise RuntimeError("cache incr down")


class RequestSafetyRateLimitResilienceTests(SimpleTestCase):
    def test_fixed_window_allow_fails_open_when_cache_backend_errors(self):
        allowed = fixed_window_allow(
            "rl:test:key",
            limit=1,
            window_seconds=60,
            cache_backend=_FailingCache(),
            request_id="req-cache-down",
        )
        self.assertTrue(allowed)
        with self.assertLogs("common.request_safety", level="WARNING") as logs:
            allowed = fixed_window_allow(
                "rl:test:key",
                limit=1,
                window_seconds=60,
                cache_backend=_FailingCache(),
                request_id="req-cache-down",
            )
        self.assertTrue(allowed)
        self.assertTrue(any("request_id=req-cache-down" in line for line in logs.output))

    def test_token_bucket_allow_fails_open_when_cache_backend_errors(self):
        allowed = token_bucket_allow(
            "tb:test:key",
            capacity=10,
            refill_per_second=1.0,
            cache_backend=_FailingCache(),
            request_id="req-cache-down",
        )
        self.assertTrue(allowed)

    def test_fixed_window_allow_tolerates_corrupt_cache_state(self):
        cache_backend = _CorruptCache("not-an-int")
        with self.assertLogs("common.request_safety", level="WARNING") as logs:
            allowed = fixed_window_allow(
                "rl:test:key",
                limit=3,
                window_seconds=60,
                cache_backend=cache_backend,
                request_id="req-corrupt-int",
            )
        self.assertTrue(allowed)
        self.assertTrue(any("coerce_int" in line for line in logs.output))

    def test_token_bucket_allow_tolerates_corrupt_cache_state(self):
        cache_backend = _CorruptCache({"tokens": "bad", "last": "bad"})
        with self.assertLogs("common.request_safety", level="WARNING") as logs:
            allowed = token_bucket_allow(
                "tb:test:key",
                capacity=10,
                refill_per_second=1.0,
                cache_backend=cache_backend,
                request_id="req-corrupt-float",
            )
        self.assertTrue(allowed)
        self.assertTrue(any("coerce_float" in line for line in logs.output))


class ReleaseStateServiceTests(SimpleTestCase):
    def test_parse_release_date_handles_invalid(self):
        self.assertIsNone(parse_release_date("not-a-date"))
        self.assertIsNotNone(parse_release_date("2026-02-17"))

    def test_lesson_available_on_prefers_front_matter(self):
        available = lesson_available_on(
            {"available_on": "2026-02-20"},
            {"available_on": "2026-03-01"},
        )
        self.assertEqual(str(available), "2026-02-20")

    def test_lesson_release_state_defaults_open_without_dates(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False, is_staff=False))
        state = lesson_release_state(request, {}, {}, classroom_id=0)
        self.assertFalse(state["is_locked"])
        self.assertIsNone(state["available_on"])


class MarkdownContentServiceTests(SimpleTestCase):
    def test_split_lesson_markdown_for_audiences(self):
        learner, teacher = split_lesson_markdown_for_audiences(
            "## Intro\nLearner content\n\n## Teacher prep\nTeacher notes"
        )
        self.assertIn("Learner content", learner)
        self.assertIn("Teacher notes", teacher)

    def test_render_markdown_to_safe_html_strips_script(self):
        html = render_markdown_to_safe_html("Hi<script>alert(1)</script>")
        self.assertIn("Hi", html)
        self.assertNotIn("<script", html)

    def test_render_markdown_to_safe_html_keeps_heading_anchor_ids(self):
        html = render_markdown_to_safe_html("# Intro Heading")
        self.assertIn('id="intro-heading"', html)

    def test_render_markdown_to_safe_html_blocks_images_by_default(self):
        html = render_markdown_to_safe_html('![diagram](https://cdn.example.org/d.png)')
        self.assertNotIn("<img", html)

    @override_settings(
        CLASSHUB_MARKDOWN_ALLOW_IMAGES=True,
        CLASSHUB_MARKDOWN_ALLOWED_IMAGE_HOSTS=["cdn.example.org"],
    )
    def test_render_markdown_allows_images_for_allowed_host(self):
        html = render_markdown_to_safe_html('![diagram](https://cdn.example.org/d.png)')
        self.assertIn("<img", html)
        self.assertIn('src="https://cdn.example.org/d.png"', html)

    @override_settings(
        CLASSHUB_MARKDOWN_ALLOW_IMAGES=True,
        CLASSHUB_MARKDOWN_ALLOWED_IMAGE_HOSTS=["cdn.example.org"],
    )
    def test_render_markdown_blocks_images_for_disallowed_host(self):
        html = render_markdown_to_safe_html('![diagram](https://evil.example.org/d.png)')
        self.assertNotIn("<img", html)

    @override_settings(
        CLASSHUB_MARKDOWN_ALLOW_IMAGES=True,
        CLASSHUB_MARKDOWN_ALLOWED_IMAGE_HOSTS=[],
    )
    def test_render_markdown_allows_relative_images_when_enabled(self):
        html = render_markdown_to_safe_html("![diagram](/lesson-asset/12/download)")
        self.assertIn("<img", html)
        self.assertIn('src="/lesson-asset/12/download"', html)

    @override_settings(
        CLASSHUB_MARKDOWN_ALLOW_IMAGES=True,
        CLASSHUB_MARKDOWN_ALLOWED_IMAGE_HOSTS=[],
        CLASSHUB_ASSET_BASE_URL="https://assets.example.org",
    )
    def test_render_markdown_rewrites_relative_media_urls_to_asset_origin(self):
        html = render_markdown_to_safe_html(
            "![diagram](/lesson-asset/12/download)\n\n[Watch](/lesson-video/4/stream)"
        )
        self.assertIn('src="https://assets.example.org/lesson-asset/12/download"', html)
        self.assertIn('href="https://assets.example.org/lesson-video/4/stream"', html)

    @override_settings(CONTENT_ROOT="/tmp/does-not-exist")
    def test_load_course_manifest_rejects_invalid_course_slug(self):
        self.assertEqual(load_course_manifest("../bad"), {})

    def test_load_lesson_markdown_blocks_manifest_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content_root = Path(tmpdir) / "content"
            course_dir = content_root / "courses" / "demo"
            course_dir.mkdir(parents=True, exist_ok=True)
            outside = content_root / "outside.md"
            outside.write_text("# outside\n", encoding="utf-8")
            (course_dir / "course.yaml").write_text(
                "lessons:\n"
                "  - slug: lesson-1\n"
                "    file: ../outside.md\n",
                encoding="utf-8",
            )
            with override_settings(CONTENT_ROOT=str(content_root)):
                fm, body, meta = load_lesson_markdown("demo", "lesson-1")

        self.assertEqual(fm, {})
        self.assertEqual(body, "")
        self.assertEqual(meta.get("slug"), "lesson-1")


class UploadScanServiceTests(SimpleTestCase):
    @override_settings(CLASSHUB_UPLOAD_SCAN_ENABLED=False)
    def test_scan_disabled_returns_disabled(self):
        upload = SimpleUploadedFile("project.sb3", b"abc123")
        result = scan_uploaded_file(upload)
        self.assertEqual(result.status, "disabled")

    @override_settings(
        CLASSHUB_UPLOAD_SCAN_ENABLED=True,
        CLASSHUB_UPLOAD_SCAN_COMMAND="scanner-cli --check",
        CLASSHUB_UPLOAD_SCAN_TIMEOUT_SECONDS=5,
    )
    def test_scan_marks_clean_on_returncode_zero(self):
        upload = SimpleUploadedFile("project.sb3", b"abc123")
        with patch("hub.services.upload_scan.subprocess.run") as run_mock:
            run_mock.return_value.returncode = 0
            run_mock.return_value.stdout = ""
            run_mock.return_value.stderr = ""
            result = scan_uploaded_file(upload)
        self.assertEqual(result.status, "clean")

    @override_settings(
        CLASSHUB_UPLOAD_SCAN_ENABLED=True,
        CLASSHUB_UPLOAD_SCAN_COMMAND="scanner-cli --check",
        CLASSHUB_UPLOAD_SCAN_TIMEOUT_SECONDS=5,
    )
    def test_scan_marks_infected_on_returncode_one(self):
        upload = SimpleUploadedFile("project.sb3", b"abc123")
        with patch("hub.services.upload_scan.subprocess.run") as run_mock:
            run_mock.return_value.returncode = 1
            run_mock.return_value.stdout = "FOUND TEST VIRUS"
            run_mock.return_value.stderr = ""
            result = scan_uploaded_file(upload)
        self.assertEqual(result.status, "infected")


class TeacherTrackerServiceTests(TestCase):
    def _request_stub(self):
        return SimpleNamespace(user=SimpleNamespace(is_authenticated=False, is_staff=False))

    def _build_class_with_modules(self, *, name: str, join_code: str, module_count: int) -> Class:
        classroom = Class.objects.create(name=name, join_code=join_code)
        for idx in range(module_count):
            module = classroom.modules.create(title=f"Session {idx + 1}", order_index=idx)
            module.materials.create(
                title=f"Upload {idx + 1}",
                type=Material.TYPE_UPLOAD,
                accepted_extensions=".sb3",
                max_upload_mb=50,
                order_index=idx,
            )
        return classroom

    def _tracker_query_count(self, classroom: Class) -> int:
        modules = list(classroom.modules.prefetch_related("materials").all())
        modules.sort(key=lambda m: (m.order_index, m.id))
        request = self._request_stub()
        with CaptureQueriesContext(connection) as ctx:
            _build_lesson_tracker_rows(request, classroom.id, modules, student_count=0)
        return len(ctx.captured_queries)

    def test_lesson_tracker_query_count_is_stable_across_module_count(self):
        one = self._build_class_with_modules(name="One Module", join_code="TRK10001", module_count=1)
        many = self._build_class_with_modules(name="Many Modules", join_code="TRK10002", module_count=5)

        one_count = self._tracker_query_count(one)
        many_count = self._tracker_query_count(many)

        self.assertEqual(one_count, many_count)

    def test_lesson_tracker_requires_prefetched_materials(self):
        classroom = self._build_class_with_modules(name="No Prefetch", join_code="TRK10003", module_count=2)
        modules = list(classroom.modules.all())
        modules.sort(key=lambda m: (m.order_index, m.id))

        with self.assertRaisesMessage(ValueError, "prefetch_related('materials')"):
            _build_lesson_tracker_rows(self._request_stub(), classroom.id, modules, student_count=0)


class UploadValidationServiceTests(SimpleTestCase):
    def test_validate_upload_content_accepts_valid_sb3_archive(self):
        error = validate_upload_content(_sample_sb3_upload(), ".sb3")
        self.assertEqual(error, "")

    def test_validate_upload_content_rejects_non_zip_sb3(self):
        upload = SimpleUploadedFile("project.sb3", b"not-a-zip")
        error = validate_upload_content(upload, ".sb3")
        self.assertIn("does not match .sb3", error)


class _SubmissionFileWithoutPath:
    def __init__(self, payload: bytes):
        self._payload = payload

    @property
    def path(self):
        raise AttributeError("no filesystem path")

    def open(self, mode: str = "rb"):
        if "b" not in mode:
            raise ValueError("binary mode required")
        return BytesIO(self._payload)


class _SubmissionFileWithPath:
    def __init__(self, path: str):
        self.path = path

    def open(self, mode: str = "rb"):
        return open(self.path, mode)


class ZipExportServiceTests(SimpleTestCase):
    def test_reserve_archive_path_uses_fallback_for_duplicate(self):
        used = set()
        first = reserve_archive_path("files/project.sb3", used, fallback="files/project_1.sb3")
        second = reserve_archive_path("files/project.sb3", used, fallback="files/project_1.sb3")
        self.assertEqual(first, "files/project.sb3")
        self.assertEqual(second, "files/project_1.sb3")

    def test_write_submission_file_to_archive_uses_fallback_stream(self):
        submission = SimpleNamespace(file=_SubmissionFileWithoutPath(b"fallback-bytes"))
        with temporary_zip_archive() as (tmp, archive):
            ok = write_submission_file_to_archive(
                archive,
                submission=submission,
                arcname="files/fallback.sb3",
                allow_file_fallback=True,
            )
        self.assertTrue(ok)
        tmp.seek(0)
        with zipfile.ZipFile(tmp, "r") as archive:
            self.assertEqual(archive.read("files/fallback.sb3"), b"fallback-bytes")

    def test_write_submission_file_to_archive_returns_false_without_fallback(self):
        submission = SimpleNamespace(file=_SubmissionFileWithoutPath(b"fallback-bytes"))
        with temporary_zip_archive() as (_tmp, archive):
            ok = write_submission_file_to_archive(
                archive,
                submission=submission,
                arcname="files/fallback.sb3",
                allow_file_fallback=False,
            )
        self.assertFalse(ok)

    def test_write_submission_file_to_archive_uses_file_path_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "project.sb3"
            source.write_bytes(b"path-bytes")
            submission = SimpleNamespace(file=_SubmissionFileWithPath(str(source)))
            with temporary_zip_archive() as (tmp, archive):
                ok = write_submission_file_to_archive(
                    archive,
                    submission=submission,
                    arcname="files/project.sb3",
                    allow_file_fallback=False,
                )
            self.assertTrue(ok)
            tmp.seek(0)
            with zipfile.ZipFile(tmp, "r") as archive:
                self.assertEqual(archive.read("files/project.sb3"), b"path-bytes")


class ContentLinksServiceTests(SimpleTestCase):
    def test_parse_course_lesson_url_handles_local_or_absolute_urls(self):
        self.assertEqual(
            parse_course_lesson_url("/course/piper_scratch_12_session/01-welcome-private-workflow"),
            ("piper_scratch_12_session", "01-welcome-private-workflow"),
        )
        self.assertEqual(
            parse_course_lesson_url(
                "https://lms.example.org/course/piper_scratch_12_session/01-welcome-private-workflow/"
            ),
            ("piper_scratch_12_session", "01-welcome-private-workflow"),
        )
        self.assertIsNone(parse_course_lesson_url("/teach/lessons"))

    def test_normalize_lesson_videos_sets_expected_source_types(self):
        videos = normalize_lesson_videos(
            {
                "videos": [
                    {"id": "yt", "title": "YouTube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                    {"id": "native", "title": "Native", "url": "https://cdn.example.org/lesson.mp4"},
                    {"id": "link", "title": "Link", "url": "https://example.org/article"},
                ]
            }
        )
        self.assertEqual(videos[0]["source_type"], "youtube")
        self.assertEqual(videos[0]["embed_url"], "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
        self.assertEqual(videos[1]["source_type"], "native")
        self.assertEqual(videos[2]["source_type"], "link")

    def test_safe_filename_strips_unsafe_characters(self):
        self.assertEqual(safe_filename("../../Ada Lovelace?.png"), "Ada_Lovelace_.png")

    @override_settings(CLASSHUB_ASSET_BASE_URL="")
    def test_build_asset_url_uses_relative_path_without_base_url(self):
        self.assertEqual(build_asset_url("/lesson-asset/8/download"), "/lesson-asset/8/download")

    @override_settings(CLASSHUB_ASSET_BASE_URL="https://assets.example.org/")
    def test_build_asset_url_prefixes_configured_asset_origin(self):
        self.assertEqual(
            build_asset_url("/lesson-video/3/stream"),
            "https://assets.example.org/lesson-video/3/stream",
        )


class StudentSessionMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.classroom = Class.objects.create(name="Session Class", join_code="SESS1234")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.middleware = StudentSessionMiddleware(lambda _request: HttpResponse("ok"))

    def _request_with_student_session(self, path: str):
        request = self.factory.get(path)
        session_middleware = SessionMiddleware(lambda _request: HttpResponse("ok"))
        session_middleware.process_request(request)
        request.session["student_id"] = self.student.id
        request.session["class_id"] = self.classroom.id
        request.session["class_epoch"] = self.classroom.session_epoch
        request.session.save()
        return request

    def test_healthz_path_skips_student_lookup_queries(self):
        request = self._request_with_student_session("/healthz")
        with self.assertNumQueries(0):
            self.middleware(request)
        self.assertIsNone(request.student)
        self.assertIsNone(request.classroom)

    def test_static_path_skips_student_lookup_queries(self):
        request = self._request_with_student_session("/static/app.css")
        with self.assertNumQueries(0):
            self.middleware(request)
        self.assertIsNone(request.student)
        self.assertIsNone(request.classroom)

    def test_admin_path_skips_student_lookup_queries(self):
        request = self._request_with_student_session("/admin/")
        with self.assertNumQueries(0):
            self.middleware(request)
        self.assertIsNone(request.student)
        self.assertIsNone(request.classroom)

    def test_student_path_uses_single_query_and_attaches_student_context(self):
        request = self._request_with_student_session("/student")
        with self.assertNumQueries(1):
            self.middleware(request)
        self.assertIsNotNone(request.student)
        self.assertIsNotNone(request.classroom)
        self.assertEqual(request.student.id, self.student.id)
        self.assertEqual(request.classroom.id, self.classroom.id)


class IPPrivacyServiceTests(SimpleTestCase):
    def test_minimize_student_event_ip_truncates_ipv4_by_default(self):
        self.assertEqual(minimize_student_event_ip("203.0.113.25"), "203.0.113.0")

    def test_minimize_student_event_ip_truncates_ipv6_by_default(self):
        self.assertEqual(minimize_student_event_ip("2001:db8:abcd:1234:5678:90ab:cdef:1234"), "2001:db8:abcd:1200::")

    @override_settings(CLASSHUB_STUDENT_EVENT_IP_MODE="full")
    def test_minimize_student_event_ip_can_keep_full_value(self):
        self.assertEqual(minimize_student_event_ip("203.0.113.25"), "203.0.113.25")

    @override_settings(CLASSHUB_STUDENT_EVENT_IP_MODE="none")
    def test_minimize_student_event_ip_can_disable_storage(self):
        self.assertEqual(minimize_student_event_ip("203.0.113.25"), "")
