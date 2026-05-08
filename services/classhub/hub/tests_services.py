import zipfile
import tempfile
import urllib.error
import re
import subprocess
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import IntegrityError, connection
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from common.request_safety import fixed_window_allow, token_bucket_allow

from .middleware import StudentSessionMiddleware
from .models import Class, ClassStaffAssignment, Material, Module, StudentEvent, StudentIdentity, StudentMaterialResponse, Submission
from .services.markdown_content import (
    is_teacher_section_heading,
    load_course_manifest,
    load_lesson_markdown,
    render_markdown_to_safe_html,
    split_lesson_markdown_for_audiences,
)
from .services.syllabus_ingest_contracts import SyllabusIngestError
from .services.syllabus_ingest_zip_helpers import _safe_lesson_filename, _safe_zip_path
from .services.content_links import (
    build_asset_url,
    extract_youtube_id,
    normalize_lesson_videos,
    parse_course_lesson_url,
    youtube_embed_url,
)
from .services.data_lifespan import (
    _count_event_policy_overdue_rows,
    _count_submission_policy_overdue_rows,
)
from .services.filenames import safe_filename
from .services.helper_control import (
    HelperRemoteComputeEvidenceResult,
    HelperRemoteComputeStatusResult,
    _safe_json_dict,
    _safe_reference_rows,
    fetch_rag_status,
)
from .services.helper_topics import build_allowed_topics, build_lesson_topics, split_helper_topics_text
from .services.ip_privacy import minimize_student_event_ip
from .services.remote_compute_signals import build_remote_compute_signal_summary
from .services.release_state import (
    lesson_available_on,
    lesson_release_state,
    parse_release_date,
)
from .services.student_home import build_material_response_map
from .services.student_join import create_student_identity
from .services.teacher_roster_class import build_dashboard_context
from .services.teacher_tracker import (
    _build_class_digest_rows,
    _build_helper_signal_snapshot,
    _build_lesson_tracker_rows,
)
from .services.teacher_home_templates import generate_authoring_templates_from_form
from .services.teacher_home_context_data import build_teacher_home_context_data
from .services.upload_policy import (
    front_matter_submission,
    parse_extensions,
)
from .services.upload_scan import scan_uploaded_file
from .services.upload_validation import validate_upload_content
from .services.ui_density import (
    default_ui_density_mode,
    resolve_ui_density_mode,
    resolve_ui_density_mode_for_modules,
)
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

    def test_parse_extensions_ignores_blanks_and_preserves_first_seen_order(self):
        self.assertEqual(parse_extensions(" , PNG, ,jpg, .png "), [".png", ".jpg"])

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

    def test_front_matter_submission_returns_defaults_for_invalid_root(self):
        self.assertEqual(
            front_matter_submission(None),
            {"type": "", "accepted_exts": [], "naming": ""},
        )
        self.assertEqual(
            front_matter_submission("bad"),
            {"type": "", "accepted_exts": [], "naming": ""},
        )

    def test_front_matter_submission_returns_defaults_for_invalid_submission_payload(self):
        self.assertEqual(
            front_matter_submission({"submission": "bad"}),
            {"type": "", "accepted_exts": [], "naming": ""},
        )

    def test_front_matter_submission_normalizes_missing_optional_keys(self):
        row = front_matter_submission({"submission": {"accepted": ["sb3", ".PNG", "sb3"]}})
        self.assertEqual(row["type"], "")
        self.assertEqual(row["accepted_exts"], [".sb3", ".png"])
        self.assertEqual(row["naming"], "")


class TeacherHomeTemplatesServiceTests(SimpleTestCase):
    def _parse_positive_int(self, raw: str, *, min_value: int, max_value: int) -> int | None:
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            return None
        if parsed < min_value or parsed > max_value:
            return None
        return parsed

    def test_generate_authoring_templates_from_form_rejects_invalid_slug(self):
        generation_mock = MagicMock()
        result = generate_authoring_templates_from_form(
            post_data={
                "template_slug": "Bad Slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
            template_slug_re=re.compile(r"^[a-z0-9_-]+$"),
            parse_positive_int_fn=self._parse_positive_int,
            generate_authoring_templates_fn=generation_mock,
        )
        self.assertEqual(
            result.error,
            "Course slug can use lowercase letters, numbers, underscores, and dashes.",
        )
        generation_mock.assert_not_called()

    @override_settings(
        CLASSHUB_AUTHORING_TEMPLATE_AGE_BAND_DEFAULT="8th-10th",
        CLASSHUB_AUTHORING_TEMPLATE_DIR="/tmp/template-out",
    )
    def test_generate_authoring_templates_from_form_returns_generation_metadata(self):
        generation_mock = MagicMock(
            return_value=SimpleNamespace(
                output_paths=[
                    Path("/tmp/template-out/sample_slug-teacher-plan-template.md"),
                    Path("/tmp/template-out/sample_slug-public-overview-template.md"),
                ]
            )
        )
        result = generate_authoring_templates_from_form(
            post_data={
                "template_slug": "sample_slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
            template_slug_re=re.compile(r"^[a-z0-9_-]+$"),
            parse_positive_int_fn=self._parse_positive_int,
            generate_authoring_templates_fn=generation_mock,
        )
        self.assertEqual(result.error, "")
        self.assertEqual(result.slug, "sample_slug")
        self.assertEqual(result.title, "Sample Course")
        self.assertEqual(result.sessions, 12)
        self.assertEqual(result.duration, 75)
        self.assertEqual(result.output_dir, Path("/tmp/template-out"))
        self.assertEqual(
            list(result.output_paths),
            [
                "/tmp/template-out/sample_slug-teacher-plan-template.md",
                "/tmp/template-out/sample_slug-public-overview-template.md",
            ],
        )
        self.assertEqual(
            result.notice,
            "Generated templates for sample_slug in /tmp/template-out.",
        )
        generation_mock.assert_called_once_with(
            slug="sample_slug",
            title="Sample Course",
            sessions=12,
            duration=75,
            age_band="8th-10th",
            out_dir=Path("/tmp/template-out"),
            overwrite=True,
        )


class TeacherHomeContextDataServiceTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="teacher_home_ctx",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.class_a = Class.objects.create(name="Context Class A", join_code="CTXA1234")
        self.class_b = Class.objects.create(name="Context Class B", join_code="CTXB1234")
        ClassStaffAssignment.objects.create(classroom=self.class_b, user=self.staff, is_active=True)
        module = Module.objects.create(classroom=self.class_b, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=25,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.class_b, display_name="Ada")
        self.submission = Submission.objects.create(
            material=material,
            student=student,
            original_filename="ada.sb3",
            file=_sample_sb3_upload(),
        )

    def test_build_teacher_home_context_data_returns_ranked_classes_and_submission_feed(self):
        context = build_teacher_home_context_data(user=self.staff)

        self.assertEqual([c.id for c in context["assigned_classes"]], [self.class_b.id])
        self.assertIn(self.class_b.id, context["assigned_class_ids"])
        self.assertEqual(int(context["recent_submissions"][0].id), int(self.submission.id))
        self.assertTrue(any(int(c.id) == int(self.class_a.id) for c in context["classes"]))
        self.assertTrue(any(int(c.id) == int(self.class_b.id) for c in context["classes"]))
        self.assertEqual(context["teacher_accounts"].model, get_user_model())

    def test_build_teacher_home_context_data_returns_empty_feed_for_user_without_classes(self):
        outsider = get_user_model().objects.create_user(
            username="teacher_home_outsider",
            password="pw12345",
            is_staff=False,
        )
        context = build_teacher_home_context_data(user=outsider)
        self.assertEqual(list(context["classes"]), [])
        self.assertEqual(context["assigned_class_ids"], set())
        self.assertEqual(context["assigned_classes"], [])
        self.assertEqual(context["recent_submissions"], [])


class HelperControlServiceTests(SimpleTestCase):
    def test_safe_json_dict_returns_empty_for_malformed_or_non_dict_json(self):
        self.assertEqual(_safe_json_dict("not-json"), {})
        self.assertEqual(_safe_json_dict("[]"), {})
        self.assertEqual(_safe_json_dict('"token"'), {})

    def test_safe_json_dict_returns_dict_for_valid_object_payload(self):
        self.assertEqual(_safe_json_dict('{"ok": true, "count": 3}'), {"ok": True, "count": 3})

    def test_safe_reference_rows_returns_empty_for_non_list(self):
        self.assertEqual(_safe_reference_rows(None), [])
        self.assertEqual(_safe_reference_rows("bad"), [])

    def test_safe_reference_rows_normalizes_missing_and_invalid_fields(self):
        rows = _safe_reference_rows(
            [
                "skip-me",
                {
                    "reference_key": "  alpha  ",
                    "chunk_count": "7",
                    "last_indexed_at": " 2026-03-06T10:00:00Z ",
                },
                {
                    "chunk_count": -4,
                },
                {
                    "reference_key": "x" * 120,
                    "chunk_count": "NaN",
                    "last_indexed_at": "y" * 120,
                },
            ]
        )
        self.assertEqual(
            rows,
            [
                {
                    "reference_key": "alpha",
                    "chunk_count": 7,
                    "last_indexed_at": "2026-03-06T10:00:00Z",
                },
                {
                    "reference_key": "",
                    "chunk_count": 0,
                    "last_indexed_at": "",
                },
                {
                    "reference_key": "x" * 80,
                    "chunk_count": 0,
                    "last_indexed_at": "y" * 64,
                },
            ],
        )

    def test_fetch_rag_status_returns_http_error_details(self):
        http_error = urllib.error.HTTPError(
            url="http://helper.internal/rag/status",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=BytesIO(b'{"error":"helper_backoff"}'),
        )
        with patch(
            "hub.services.helper_control.urllib.request.urlopen",
            side_effect=http_error,
        ):
            result = fetch_rag_status(
                endpoint_url="http://helper.internal/rag/status",
                internal_token="token",
                timeout_seconds=2.0,
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "helper_backoff")
        self.assertEqual(result.status_code, 503)

    def test_fetch_rag_status_returns_unreachable_on_url_error(self):
        with patch(
            "hub.services.helper_control.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = fetch_rag_status(
                endpoint_url="http://helper.internal/rag/status",
                internal_token="token",
                timeout_seconds=2.0,
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "helper_unreachable")
        self.assertEqual(result.status_code, 0)


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


class _MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout=None):
        self.values[key] = value

    def incr(self, key):
        self.values[key] = int(self.values[key]) + 1
        return self.values[key]


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

    def test_fixed_window_allow_enforces_burst_limit(self):
        cache_backend = _MemoryCache()

        self.assertTrue(
            fixed_window_allow(
                "rl:test:key",
                limit=2,
                window_seconds=60,
                cache_backend=cache_backend,
            )
        )
        self.assertTrue(
            fixed_window_allow(
                "rl:test:key",
                limit=2,
                window_seconds=60,
                cache_backend=cache_backend,
            )
        )
        self.assertFalse(
            fixed_window_allow(
                "rl:test:key",
                limit=2,
                window_seconds=60,
                cache_backend=cache_backend,
            )
        )

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
    def test_is_teacher_section_heading_requires_real_teacher_heading(self):
        self.assertTrue(is_teacher_section_heading(" Teacher notes "))
        self.assertFalse(is_teacher_section_heading("Teacherly examples"))

    def test_split_lesson_markdown_for_audiences(self):
        learner, teacher = split_lesson_markdown_for_audiences(
            "## Intro\nLearner content\n\n## Teacher prep\nTeacher notes"
        )
        self.assertIn("Learner content", learner)
        self.assertIn("Teacher notes", teacher)

    def test_split_lesson_markdown_keeps_teacher_like_learner_heading_visible(self):
        learner, teacher = split_lesson_markdown_for_audiences(
            "## Teacherly examples\nLearner-visible guidance\n\n## Teacher notes\nPrivate facilitation notes"
        )
        self.assertIn("Teacherly examples", learner)
        self.assertIn("Learner-visible guidance", learner)
        self.assertNotIn("Teacherly examples", teacher)
        self.assertIn("Private facilitation notes", teacher)

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


class UiDensityServiceTests(SimpleTestCase):
    def test_default_ui_density_mode_maps_program_profiles(self):
        self.assertEqual(default_ui_density_mode("elementary"), "compact")
        self.assertEqual(default_ui_density_mode("secondary"), "standard")
        self.assertEqual(default_ui_density_mode("advanced"), "expanded")

    def test_course_manifest_ui_level_overrides_program_profile(self):
        mode = resolve_ui_density_mode(
            program_profile="advanced",
            course_manifest={"ui_level": "elementary"},
        )
        self.assertEqual(mode, "compact")


class UiDensityModulePrefetchTests(TestCase):
    def test_resolve_ui_density_mode_for_modules_requires_prefetch(self):
        classroom = Class.objects.create(name="Density No Prefetch", join_code="DEN10001")
        classroom.modules.create(title="Session 1", order_index=0).materials.create(
            title="Lesson Link",
            type=Material.TYPE_LINK,
            url="/course/demo/lesson-1",
            order_index=0,
        )
        modules = list(classroom.modules.all())

        with self.assertRaisesMessage(ValueError, "prefetch_related('materials')"):
            resolve_ui_density_mode_for_modules(modules=modules, program_profile="secondary")

    def test_resolve_ui_density_mode_for_modules_uses_prefetched_materials_without_db_reads(self):
        classroom = Class.objects.create(name="Density Prefetch", join_code="DEN10002")
        classroom.modules.create(title="Session 1", order_index=0).materials.create(
            title="Lesson Link",
            type=Material.TYPE_LINK,
            url="/course/demo/lesson-1",
            order_index=0,
        )
        modules = list(classroom.modules.prefetch_related("materials").all())

        with CaptureQueriesContext(connection) as ctx:
            mode = resolve_ui_density_mode_for_modules(modules=modules, program_profile="secondary")

        self.assertEqual(mode, "standard")
        self.assertEqual(len(ctx.captured_queries), 0)

    def test_resolve_ui_density_mode_for_modules_caches_manifest_per_course_slug(self):
        material_a = SimpleNamespace(type="link", url="/course/demo/lesson-1")
        material_b = SimpleNamespace(type="link", url="/course/demo/lesson-2")
        material_c = SimpleNamespace(type="link", url="/course/other/lesson-1")
        modules = [
            SimpleNamespace(_prefetched_objects_cache={"materials": [material_a, material_b]}),
            SimpleNamespace(_prefetched_objects_cache={"materials": [material_c]}),
        ]

        with patch("hub.services.ui_density.load_course_manifest") as load_manifest:
            load_manifest.side_effect = [
                {"ui_level": "elementary"},
                {"ui_level": "secondary"},
            ]
            mode = resolve_ui_density_mode_for_modules(modules=modules, program_profile="advanced")

        self.assertEqual(mode, "compact")
        self.assertEqual(load_manifest.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in load_manifest.call_args_list],
            ["demo", "other"],
        )


class StudentHomeServiceTests(TestCase):
    def test_build_material_response_map_deduplicates_checklist_indexes_preserving_order(self):
        classroom = Class.objects.create(name="Checklist Class", join_code="CHK10001")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Checklist",
            type=Material.TYPE_CHECKLIST,
            body="- one\n- two\n- three",
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentMaterialResponse.objects.create(
            material=material,
            student=student,
            checklist_checked=["2", 2, "-1", "bad", 0, "0"],
            reflection_text="notes",
            rubric_scores=["4", "bad", 3],
            rubric_feedback="feedback",
        )

        result = build_material_response_map(student=student, material_ids=[material.id])

        self.assertEqual(
            result[material.id]["checklist_checked"],
            [2, 0],
        )
        self.assertEqual(result[material.id]["rubric_scores"], [4, 3])


class StudentJoinServiceTests(SimpleTestCase):
    def test_create_student_identity_retries_after_integrity_error(self):
        classroom = SimpleNamespace(id=1)
        created = SimpleNamespace(id=7, return_code="CODE2")

        with patch("hub.services.student_join.gen_student_return_code", side_effect=["code1", "code2"]):
            with patch(
                "hub.services.student_join.StudentIdentity.objects.create",
                side_effect=[IntegrityError("collision"), created],
            ) as create_mock:
                result = create_student_identity(classroom, "Ada")

        self.assertIs(result, created)
        self.assertEqual(create_mock.call_count, 2)
        self.assertEqual(create_mock.call_args_list[0].kwargs["return_code"], "CODE1")
        self.assertEqual(create_mock.call_args_list[1].kwargs["return_code"], "CODE2")

    def test_create_student_identity_raises_after_exhausting_retries(self):
        classroom = SimpleNamespace(id=1)

        with patch("hub.services.student_join.gen_student_return_code", return_value="code1"):
            with patch(
                "hub.services.student_join.StudentIdentity.objects.create",
                side_effect=IntegrityError("collision"),
            ):
                with self.assertRaisesMessage(RuntimeError, "could_not_allocate_unique_student_return_code"):
                    create_student_identity(classroom, "Ada")


class TeacherRosterClassServiceTests(SimpleTestCase):
    def test_build_dashboard_context_prefetches_modules_once(self):
        class _FakeMaterialsRelation:
            def __init__(self, materials):
                self._materials = materials

            def all(self):
                return self._materials

        class _FakeModulesManager:
            def __init__(self, modules):
                self._modules = modules
                self.prefetch_calls = 0

            def prefetch_related(self, *_args):
                self.prefetch_calls += 1
                return self

            def all(self):
                return self._modules

        class _FakeStudentsManager:
            def count(self):
                return 0

            def all(self):
                return self

            def order_by(self, *_args):
                return []

        module = SimpleNamespace(
            id=1,
            order_index=0,
            title="Session 1",
            materials=_FakeMaterialsRelation([]),
        )
        modules_manager = _FakeModulesManager([module])
        classroom = SimpleNamespace(
            id=1,
            session_epoch=0,
            modules=modules_manager,
            students=_FakeStudentsManager(),
        )

        with patch.multiple(
            "hub.services.teacher_roster_class",
            _build_lesson_tracker_rows=lambda *args, **kwargs: [],
            _build_helper_signal_snapshot=lambda *args, **kwargs: {},
            _support_tag_choices=lambda: [],
            _support_tags_by_student=lambda **kwargs: {},
            _material_submission_counts=lambda *_args, **_kwargs: {},
            _submission_counts_by_student=lambda **kwargs: {},
            _build_facilitator_support_snapshot=lambda **kwargs: {},
            _build_outcome_snapshot=lambda **kwargs: {},
        ):
            context = build_dashboard_context(
                request=SimpleNamespace(),
                classroom=classroom,
                normalize_order_fn=lambda _modules: None,
            )

        self.assertEqual(modules_manager.prefetch_calls, 1)
        self.assertEqual(len(context["modules"]), 1)


class RemoteComputeSignalServiceTests(SimpleTestCase):
    def test_build_remote_compute_signal_summary_returns_unavailable_when_status_is_not_ok(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(ok=False, error_code="helper_unreachable"),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=False),
        )
        self.assertEqual(summary["level"], "unavailable")
        self.assertEqual(summary["remote_attempt_count"], 0)
        self.assertIn("Local/default helper remains available", summary["detail"])

    def test_build_remote_compute_signal_summary_returns_quiet_without_activation_history(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=0,
                remote_route_count=0,
                fallback_local_count=0,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "quiet")
        self.assertEqual(summary["alerts"], [])

    def test_build_remote_compute_signal_summary_returns_calm_when_metrics_are_bounded(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=3,
                avg_ready_seconds=18,
                remote_route_count=6,
                fallback_local_count=1,
                degraded_transition_count=0,
                provider_unreachable_count=0,
                unused_activation_count=0,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True, recent_sessions=[{"lease_session_id": 1}]),
        )
        self.assertEqual(summary["level"], "calm")
        self.assertEqual(summary["fallback_rate_pct"], 14)
        self.assertEqual(summary["unused_activation_rate_pct"], 0)
        self.assertEqual(summary["alerts"], [])

    def test_build_remote_compute_signal_summary_returns_watch_at_degraded_threshold(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=2,
                avg_ready_seconds=18,
                remote_route_count=2,
                fallback_local_count=0,
                degraded_transition_count=2,
                provider_unreachable_count=0,
                unused_activation_count=0,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "watch")
        self.assertEqual(summary["summary"], "Remote path is not calm")
        self.assertEqual(len(summary["alerts"]), 1)
        self.assertEqual(summary["alerts"][0]["summary"], "Remote path has repeated degraded transitions")

    def test_build_remote_compute_signal_summary_returns_watch_at_slow_ready_threshold(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=1,
                avg_ready_seconds=30,
                remote_route_count=1,
                fallback_local_count=0,
                degraded_transition_count=0,
                provider_unreachable_count=0,
                unused_activation_count=0,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "watch")
        self.assertEqual(summary["alerts"][0]["summary"], "Warm-up is slow for class use")

    def test_build_remote_compute_signal_summary_returns_attention_at_fallback_threshold(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=2,
                avg_ready_seconds=18,
                remote_route_count=3,
                fallback_local_count=1,
                degraded_transition_count=0,
                provider_unreachable_count=0,
                unused_activation_count=0,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "attention")
        self.assertEqual(summary["fallback_rate_pct"], 25)
        self.assertEqual(summary["summary"], "Needs operator attention")

    def test_build_remote_compute_signal_summary_returns_attention_at_unused_activation_threshold(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=2,
                avg_ready_seconds=18,
                remote_route_count=1,
                fallback_local_count=0,
                degraded_transition_count=0,
                provider_unreachable_count=0,
                unused_activation_count=1,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "attention")
        self.assertEqual(summary["unused_activation_rate_pct"], 50)

    def test_build_remote_compute_signal_summary_returns_attention_for_waste_and_instability(self):
        summary = build_remote_compute_signal_summary(
            status_result=HelperRemoteComputeStatusResult(
                ok=True,
                activation_count=4,
                avg_ready_seconds=45,
                remote_route_count=4,
                fallback_local_count=2,
                degraded_transition_count=2,
                provider_unreachable_count=1,
                unused_activation_count=2,
            ),
            evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
        )
        self.assertEqual(summary["level"], "attention")
        self.assertEqual(summary["summary"], "Needs operator attention")
        self.assertEqual(summary["fallback_rate_pct"], 33)
        self.assertEqual(summary["unused_activation_rate_pct"], 50)
        self.assertGreaterEqual(len(summary["alerts"]), 3)


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
        self.assertEqual(run_mock.call_args.kwargs.get("shell"), False)

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

    @override_settings(
        CLASSHUB_UPLOAD_SCAN_ENABLED=True,
        CLASSHUB_UPLOAD_SCAN_COMMAND="scanner-cli --check",
        CLASSHUB_UPLOAD_SCAN_TIMEOUT_SECONDS=5,
    )
    def test_scan_timeout_returns_scanner_timeout(self):
        upload = SimpleUploadedFile("project.sb3", b"abc123")
        with patch(
            "hub.services.upload_scan.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="scanner-cli --check", timeout=5),
        ):
            result = scan_uploaded_file(upload)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.message, "scanner_timeout")


class DataLifespanServiceTests(TestCase):
    @override_settings(CLASSHUB_TELEMETRY_READ_MODE="core")
    def test_submission_overdue_count_uses_single_query_across_retention_groups(self):
        now = timezone.now()
        class_a = Class.objects.create(name="Retention A", join_code="RET10001")
        class_b = Class.objects.create(name="Retention B", join_code="RET10002")
        class_c = Class.objects.create(name="Retention C", join_code="RET10003")

        material_rows: list[Material] = []
        for classroom in (class_a, class_b, class_c):
            module = classroom.modules.create(title="Session 1", order_index=0)
            material_rows.append(
                module.materials.create(
                    title="Upload",
                    type=Material.TYPE_UPLOAD,
                    accepted_extensions=".sb3",
                    max_upload_mb=50,
                    order_index=0,
                )
            )
        student_a = StudentIdentity.objects.create(classroom=class_a, display_name="Ada")
        student_b = StudentIdentity.objects.create(classroom=class_b, display_name="Ben")
        student_c = StudentIdentity.objects.create(classroom=class_c, display_name="Cy")

        sub_a = Submission.objects.create(
            material=material_rows[0],
            student=student_a,
            original_filename="a.sb3",
            file=SimpleUploadedFile("a.sb3", b"a"),
        )
        sub_b_old = Submission.objects.create(
            material=material_rows[1],
            student=student_b,
            original_filename="b-old.sb3",
            file=SimpleUploadedFile("b-old.sb3", b"b-old"),
        )
        sub_b_new = Submission.objects.create(
            material=material_rows[1],
            student=student_b,
            original_filename="b-new.sb3",
            file=SimpleUploadedFile("b-new.sb3", b"b-new"),
        )
        sub_c = Submission.objects.create(
            material=material_rows[2],
            student=student_c,
            original_filename="c.sb3",
            file=SimpleUploadedFile("c.sb3", b"c"),
        )
        Submission.objects.filter(id=sub_a.id).update(uploaded_at=now - timedelta(days=40))
        Submission.objects.filter(id=sub_b_old.id).update(uploaded_at=now - timedelta(days=70))
        Submission.objects.filter(id=sub_b_new.id).update(uploaded_at=now - timedelta(days=10))
        Submission.objects.filter(id=sub_c.id).update(uploaded_at=now - timedelta(days=80))

        with CaptureQueriesContext(connection) as queries:
            total = _count_submission_policy_overdue_rows(
                grouped_submission_days={30: [class_a.id], 60: [class_b.id, class_c.id]},
                now=now,
            )
        self.assertEqual(total, 3)
        self.assertEqual(len(queries.captured_queries), 1)

    @override_settings(CLASSHUB_TELEMETRY_READ_MODE="core")
    def test_event_overdue_count_uses_single_query_with_fallback_group(self):
        now = timezone.now()
        class_a = Class.objects.create(name="Events A", join_code="RET20001")
        class_b = Class.objects.create(name="Events B", join_code="RET20002")

        event_a_old = StudentEvent.objects.create(
            classroom=class_a,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        event_a_new = StudentEvent.objects.create(
            classroom=class_a,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        event_b_old = StudentEvent.objects.create(
            classroom=class_b,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        fallback_old = StudentEvent.objects.create(
            classroom=None,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        fallback_new = StudentEvent.objects.create(
            classroom=None,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        StudentEvent.objects.filter(id=event_a_old.id).update(created_at=now - timedelta(days=40))
        StudentEvent.objects.filter(id=event_a_new.id).update(created_at=now - timedelta(days=5))
        StudentEvent.objects.filter(id=event_b_old.id).update(created_at=now - timedelta(days=70))
        StudentEvent.objects.filter(id=fallback_old.id).update(created_at=now - timedelta(days=50))
        StudentEvent.objects.filter(id=fallback_new.id).update(created_at=now - timedelta(days=10))

        with CaptureQueriesContext(connection) as queries:
            total = _count_event_policy_overdue_rows(
                grouped_event_days={30: [class_a.id], 60: [class_b.id]},
                fallback_event_days=45,
                now=now,
            )
        self.assertEqual(total, 3)
        self.assertEqual(len(queries.captured_queries), 1)


class TeacherTrackerServiceTests(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

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

    def test_class_digest_cache_disabled_returns_fresh_data(self):
        classroom = Class.objects.create(name="Digest Fresh", join_code="TRK10004")
        classes = [classroom]
        since = timezone.now()

        rows_before = _build_class_digest_rows(classes, since=since)
        self.assertEqual(rows_before[0]["student_total"], 0)

        StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        rows_after = _build_class_digest_rows(classes, since=since)
        self.assertEqual(rows_after[0]["student_total"], 1)

    @override_settings(CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS=30)
    def test_class_digest_cache_enabled_holds_value_until_evicted(self):
        classroom = Class.objects.create(name="Digest Cached", join_code="TRK10005")
        classes = [classroom]
        since = timezone.now()

        rows_before = _build_class_digest_rows(classes, since=since)
        self.assertEqual(rows_before[0]["student_total"], 0)

        StudentIdentity.objects.create(classroom=classroom, display_name="Lin")
        rows_cached = _build_class_digest_rows(classes, since=since)
        self.assertEqual(rows_cached[0]["student_total"], 0)

        cache.clear()
        rows_after_clear = _build_class_digest_rows(classes, since=since)
        self.assertEqual(rows_after_clear[0]["student_total"], 1)

    @override_settings(CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS=30)
    def test_helper_signal_cache_isolated_per_classroom(self):
        class_a = Class.objects.create(name="Signals A", join_code="TRK10006")
        class_b = Class.objects.create(name="Signals B", join_code="TRK10007")
        student_a = StudentIdentity.objects.create(classroom=class_a, display_name="Alex")
        student_b = StudentIdentity.objects.create(classroom=class_b, display_name="Blair")

        StudentEvent.objects.create(
            classroom=class_a,
            student=student_a,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            details={"intent": "hint"},
        )

        snapshot_a = _build_helper_signal_snapshot(
            classroom=class_a,
            students=[student_a],
            window_hours=24,
            top_students=5,
        )
        snapshot_b = _build_helper_signal_snapshot(
            classroom=class_b,
            students=[student_b],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(snapshot_a["total_events"], 1)
        self.assertEqual(snapshot_b["total_events"], 0)

    def test_helper_signal_cache_disabled_returns_fresh_data(self):
        classroom = Class.objects.create(name="Signals Fresh", join_code="TRK10008")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Casey")

        first = _build_helper_signal_snapshot(
            classroom=classroom,
            students=[student],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(first["total_events"], 0)

        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            details={"intent": "hint"},
        )
        second = _build_helper_signal_snapshot(
            classroom=classroom,
            students=[student],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(second["total_events"], 1)

    @override_settings(CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS=30)
    def test_helper_signal_cache_enabled_holds_value_until_evicted(self):
        classroom = Class.objects.create(name="Signals Cached", join_code="TRK10009")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Dana")

        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            details={"intent": "hint"},
        )
        first = _build_helper_signal_snapshot(
            classroom=classroom,
            students=[student],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(first["total_events"], 1)

        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            details={"intent": "hint"},
        )
        cached = _build_helper_signal_snapshot(
            classroom=classroom,
            students=[student],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(cached["total_events"], 1)

        cache.clear()
        refreshed = _build_helper_signal_snapshot(
            classroom=classroom,
            students=[student],
            window_hours=24,
            top_students=5,
        )
        self.assertEqual(refreshed["total_events"], 2)

    @override_settings(CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS=30)
    def test_class_digest_cache_payload_uses_classroom_id_not_model_instance(self):
        classroom = Class.objects.create(name="Digest Payload", join_code="TRK10010")
        classes = [classroom]
        since = timezone.now()

        with patch.object(cache, "set", wraps=cache.set) as cache_set_mock:
            rows = _build_class_digest_rows(classes, since=since)

        self.assertEqual(rows[0]["classroom"].id, classroom.id)
        cached_payload = cache_set_mock.call_args.args[1]
        self.assertIsInstance(cached_payload, list)
        self.assertTrue(cached_payload)
        self.assertIn("classroom_id", cached_payload[0])
        self.assertNotIn("classroom", cached_payload[0])

    @override_settings(CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS=30)
    def test_lesson_tracker_cache_payload_uses_module_id_not_model_instance(self):
        classroom = Class.objects.create(name="Lesson Payload", join_code="TRK10011")
        module = classroom.modules.create(title="Session 1", order_index=0)
        module.materials.create(
            title="Lesson Link",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/01-welcome-private-workflow",
            order_index=0,
        )
        modules = list(classroom.modules.prefetch_related("materials").all())
        modules.sort(key=lambda m: (m.order_index, m.id))

        with patch.object(cache, "set", wraps=cache.set) as cache_set_mock:
            rows = _build_lesson_tracker_rows(
                self._request_stub(),
                classroom.id,
                modules,
                student_count=0,
                class_session_epoch=classroom.session_epoch,
            )

        self.assertTrue(rows)
        self.assertEqual(rows[0]["module"].id, module.id)
        cached_payload = cache_set_mock.call_args.args[1]
        self.assertIsInstance(cached_payload, list)
        self.assertTrue(cached_payload)
        self.assertIn("module_id", cached_payload[0])
        self.assertNotIn("module", cached_payload[0])


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

    def test_extract_youtube_id_rejects_invalid_identifier_characters(self):
        self.assertEqual(extract_youtube_id("https://www.youtube.com/watch?v=bad.id"), "")

    def test_youtube_embed_url_rejects_invalid_identifier_characters(self):
        self.assertEqual(youtube_embed_url("bad.id"), "")

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
    def test_minimize_student_event_ip_returns_empty_for_blank_and_invalid_ip(self):
        self.assertEqual(minimize_student_event_ip(""), "")
        self.assertEqual(minimize_student_event_ip("not-an-ip"), "")

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

    @override_settings(CLASSHUB_STUDENT_EVENT_IP_MODE="drop")
    def test_minimize_student_event_ip_honors_drop_alias(self):
        self.assertEqual(minimize_student_event_ip("203.0.113.25"), "")

    @override_settings(CLASSHUB_STUDENT_EVENT_IP_MODE="disabled")
    def test_minimize_student_event_ip_honors_disabled_alias(self):
        self.assertEqual(minimize_student_event_ip("2001:db8::1"), "")

    @override_settings(CLASSHUB_STUDENT_EVENT_IP_MODE="unexpected")
    def test_minimize_student_event_ip_falls_back_to_truncate_for_unknown_mode(self):
        self.assertEqual(minimize_student_event_ip("203.0.113.25"), "203.0.113.0")


class HelperTopicsServiceTests(SimpleTestCase):
    def test_build_lesson_topics_returns_empty_for_non_dict(self):
        self.assertEqual(build_lesson_topics(None), [])
        self.assertEqual(build_lesson_topics("bad"), [])

    def test_build_lesson_topics_extracts_expected_sections(self):
        topics = build_lesson_topics(
            {
                "makes": "Arcade game",
                "needs": ["Scratch 3", " Keyboard ", ""],
                "videos": [{"id": "V01"}, {"title": "Debug pass"}, {"foo": "skip"}],
                "session": 4,
                "helper_notes": ["Stay private", " Ask first ", ""],
            }
        )
        self.assertEqual(
            topics,
            [
                "Makes: Arcade game",
                "Needs: Scratch 3, Keyboard",
                "Videos: V01, Debug pass",
                "Session: 4",
                "Notes: Stay private, Ask first",
            ],
        )

    def test_build_allowed_topics_accepts_pipe_string_and_list(self):
        self.assertEqual(
            build_allowed_topics({"helper_allowed_topics": "debug|loops | sprites"}),
            ["debug", "loops", "sprites"],
        )
        self.assertEqual(
            build_allowed_topics({"allowed_topics": ["debug", " sprites ", ""]}),
            ["debug", "sprites"],
        )

    def test_split_helper_topics_text_splits_newlines_and_pipe_delimiters(self):
        raw = "Debug loops | Add sprite\r\nFix bug|\n |Share build\rRetest"
        self.assertEqual(
            split_helper_topics_text(raw),
            ["Debug loops", "Add sprite", "Fix bug", "Share build", "Retest"],
        )


class SyllabusIngestSecurityTests(SimpleTestCase):
    def test_safe_zip_path_rejects_parent_traversal(self):
        self.assertFalse(_safe_zip_path("../sessions/01.md"))
        self.assertFalse(_safe_zip_path("sessions/../../etc/passwd"))
        self.assertFalse(_safe_zip_path("/absolute/path.md"))

    def test_safe_zip_path_accepts_normalized_relative_paths(self):
        self.assertTrue(_safe_zip_path("sessions/01-intro.md"))
        self.assertTrue(_safe_zip_path("lessons/unit-a/02-build.docx"))

    def test_safe_zip_path_rejects_null_byte_segment(self):
        self.assertFalse(_safe_zip_path("sessions/\x00hidden.md"))

    def test_safe_lesson_filename_accepts_slugged_markdown(self):
        self.assertEqual(_safe_lesson_filename("01-intro_build.MD"), "01-intro_build.md")

    def test_safe_lesson_filename_rejects_unsafe_tokens(self):
        for candidate in (
            "",
            ".md",
            "../lesson.md",
            "lesson.txt",
            "lesson name.md",
            "lesson.md/",
            "lesson\x00.md",
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(SyllabusIngestError):
                    _safe_lesson_filename(candidate)
