"""Teacher portal endpoint callables under /teach/*."""

import base64
import hashlib
import logging
import re
import tempfile
import zipfile
from datetime import datetime, time as dt_time, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode, urlparse

import qrcode
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required as django_staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core import signing
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, models, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils._os import safe_join
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_otp.plugins.otp_totp.models import TOTPDevice
from qrcode.image.svg import SvgPathImage

from ..models import (
    Class,
    LessonAsset,
    LessonAssetFolder,
    LessonRelease,
    LessonVideo,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
    gen_class_code,
)
from ..http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ..services.content_links import build_asset_url, parse_course_lesson_url
from ..services.filenames import safe_filename
from ..services.markdown_content import load_lesson_markdown, load_teacher_material_html
from ..services.authoring_templates import generate_authoring_templates
from ..services.audit import log_audit_event
from ..services.release_state import (
    lesson_release_override_map,
    lesson_release_state,
    parse_release_date,
)
from ..content import _build_allowed_topics, _build_lesson_topics, iter_course_lesson_options


def staff_member_required(view_func=None):
    """
    Wrap the Django admin staff_member_required decorator to redirect unauthenticated
    teachers to /teach/login instead of the Django admin login page.
    """
    if view_func is None:
        return lambda f: django_staff_member_required(f, login_url="/teach/login")
    return django_staff_member_required(view_func, login_url="/teach/login")


_TEMPLATE_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")
_AUTHORING_TEMPLATE_SUFFIXES = {
    "teacher_plan_md": "teacher-plan-template.md",
    "teacher_plan_docx": "teacher-plan-template.docx",
    "public_overview_md": "public-overview-template.md",
    "public_overview_docx": "public-overview-template.docx",
}
_TEACHER_2FA_TOKEN_SALT = "classhub.teacher-2fa-setup"
_TEACHER_2FA_TOKEN_USED_CACHE_PREFIX = "classhub:teacher-2fa:used:"
logger = logging.getLogger(__name__)


def _teacher_2fa_device_name() -> str:
    configured = (getattr(settings, "TEACHER_2FA_DEVICE_NAME", "teacher-primary") or "").strip()
    return configured or "teacher-primary"


def _product_name() -> str:
    configured = (getattr(settings, "CLASSHUB_PRODUCT_NAME", "Class Hub") or "").strip()
    return configured or "Class Hub"


def _teacher_invite_max_age_seconds() -> int:
    raw = int(getattr(settings, "TEACHER_2FA_INVITE_MAX_AGE_SECONDS", 24 * 3600) or 0)
    return raw if raw > 0 else 24 * 3600


def _teacher_setup_token_cache_key(token: str) -> str:
    digest = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    return f"{_TEACHER_2FA_TOKEN_USED_CACHE_PREFIX}{digest}"


def _build_teacher_setup_token(user) -> str:
    payload = {
        "uid": int(user.id),
        "email": (user.email or "").strip().lower(),
        "username": (user.get_username() or "").strip(),
    }
    return signing.dumps(payload, salt=_TEACHER_2FA_TOKEN_SALT)


def _resolve_teacher_setup_user(token: str, *, consume: bool = False):
    if not token:
        return None, "Missing setup token."
    cache_key = _teacher_setup_token_cache_key(token)
    if not consume:
        try:
            if cache.get(cache_key):
                return None, "This setup link was already used. Ask an admin for a new invite."
        except Exception:
            logger.warning("teacher_setup_token_cache_check_failed")
    try:
        payload = signing.loads(
            token,
            salt=_TEACHER_2FA_TOKEN_SALT,
            max_age=_teacher_invite_max_age_seconds(),
        )
    except signing.SignatureExpired:
        return None, "This setup link expired. Ask an admin to send a new invite."
    except signing.BadSignature:
        return None, "Invalid setup link."

    try:
        user_id = int(payload.get("uid") or 0)
    except Exception:
        user_id = 0
    email = (payload.get("email") or "").strip().lower()
    username = (payload.get("username") or "").strip()
    if not user_id or not email or not username:
        return None, "Invalid setup link payload."

    User = get_user_model()
    user = User.objects.filter(
        id=user_id,
        username=username,
        email__iexact=email,
        is_staff=True,
        is_active=True,
    ).first()
    if not user:
        return None, "Invite is no longer valid for an active teacher account."
    if consume:
        try:
            cache_claimed = bool(cache.add(cache_key, "1", timeout=_teacher_invite_max_age_seconds()))
        except Exception:
            logger.warning("teacher_setup_token_cache_mark_failed")
            cache_claimed = True
        if not cache_claimed:
            return None, "This setup link was already used. Ask an admin for a new invite."
    return user, ""


def _totp_secret_base32(device: TOTPDevice) -> str:
    return base64.b32encode(device.bin_key).decode("ascii").rstrip("=")


def _format_base32_for_display(secret: str) -> str:
    groups = [secret[idx : idx + 4] for idx in range(0, len(secret), 4)]
    return " ".join(groups)


def _totp_qr_svg(config_url: str) -> str:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(config_url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    stream = BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def _send_teacher_onboarding_email(request, *, user, setup_url: str, starting_password: str = ""):
    app_host = request.get_host()
    login_url = request.build_absolute_uri("/teach/login")
    product_name = _product_name()
    from_email = (getattr(settings, "TEACHER_INVITE_FROM_EMAIL", "") or "").strip() or getattr(
        settings, "DEFAULT_FROM_EMAIL", "classhub@localhost"
    )
    include_password = bool(starting_password)
    lines = [
        f"Hi {user.first_name or user.username},",
        "",
        f"Your {product_name} teacher account is ready.",
        "",
        f"Username: {user.username}",
    ]
    if include_password:
        lines.extend(
            [
                f"Temporary password: {starting_password}",
                "",
                "Change your password after first sign-in.",
            ]
        )
    lines.extend(
        [
            "",
            "Finalize two-factor setup here:",
            setup_url,
            "",
            "What to do:",
            "1) Open the setup link.",
            "2) Scan the QR code in your authenticator app.",
            "3) Enter the 6-digit code to confirm.",
            "",
            f"Teacher login: {login_url}",
            f"Host: {app_host}",
        ]
    )
    send_mail(
        subject=f"Complete your {product_name} teacher 2FA setup",
        message="\n".join(lines),
        from_email=from_email,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _title_from_video_filename(filename: str) -> str:
    stem = Path(filename or "").stem
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:200] or "Untitled video"


def _next_lesson_video_order(course_slug: str, lesson_slug: str) -> int:
    try:
        max_idx = (
            LessonVideo.objects.filter(course_slug=course_slug, lesson_slug=lesson_slug)
            .aggregate(models.Max("order_index"))
            .get("order_index__max")
        )
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonvideo" in str(exc).lower():
            return 0
        raise
    return int(max_idx) + 1 if max_idx is not None else 0


def _normalize_order(qs, field: str = "order_index"):
    """Normalize order_index values to 0..N-1 in current QS order."""
    for i, obj in enumerate(qs):
        if getattr(obj, field) != i:
            setattr(obj, field, i)
            obj.save(update_fields=[field])


def _material_submission_counts(material_ids: list[int]) -> dict[int, int]:
    counts = {}
    if not material_ids:
        return counts
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id", "student_id")
        .distinct()
    )
    for row in rows:
        material_id = int(row["material_id"])
        counts[material_id] = counts.get(material_id, 0) + 1
    return counts


def _material_latest_upload_map(material_ids: list[int]) -> dict[int, timezone.datetime]:
    latest = {}
    if not material_ids:
        return latest
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id")
        .annotate(last_uploaded_at=models.Max("uploaded_at"))
    )
    for row in rows:
        latest[int(row["material_id"])] = row["last_uploaded_at"]
    return latest


def _build_class_digest_rows(classes: list[Class], *, since: timezone.datetime) -> list[dict]:
    class_ids = [int(c.id) for c in classes if c and c.id]
    if not class_ids:
        return []

    student_totals: dict[int, int] = {}
    for row in (
        StudentIdentity.objects.filter(classroom_id__in=class_ids)
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        student_totals[int(row["classroom_id"])] = int(row["total"] or 0)

    students_with_submissions: dict[int, int] = {}
    for row in (
        Submission.objects.filter(student__classroom_id__in=class_ids)
        .values("student__classroom_id")
        .annotate(total=models.Count("student_id", distinct=True))
    ):
        students_with_submissions[int(row["student__classroom_id"])] = int(row["total"] or 0)

    submission_totals_since: dict[int, int] = {}
    for row in (
        Submission.objects.filter(
            material__module__classroom_id__in=class_ids,
            uploaded_at__gte=since,
        )
        .values("material__module__classroom_id")
        .annotate(total=models.Count("id"))
    ):
        submission_totals_since[int(row["material__module__classroom_id"])] = int(row["total"] or 0)

    helper_events_since: dict[int, int] = {}
    for row in (
        StudentEvent.objects.filter(
            classroom_id__in=class_ids,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            created_at__gte=since,
        )
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        helper_events_since[int(row["classroom_id"])] = int(row["total"] or 0)

    new_students_since: dict[int, int] = {}
    for row in (
        StudentIdentity.objects.filter(
            classroom_id__in=class_ids,
            created_at__gte=since,
        )
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        new_students_since[int(row["classroom_id"])] = int(row["total"] or 0)

    last_submission_at: dict[int, timezone.datetime] = {}
    for row in (
        Submission.objects.filter(material__module__classroom_id__in=class_ids)
        .values("material__module__classroom_id")
        .annotate(last_uploaded_at=models.Max("uploaded_at"))
    ):
        class_id = int(row["material__module__classroom_id"])
        last_submission_at[class_id] = row["last_uploaded_at"]

    rows: list[dict] = []
    for classroom in classes:
        classroom_id = int(classroom.id)
        student_total = int(student_totals.get(classroom_id, 0))
        with_submissions = int(students_with_submissions.get(classroom_id, 0))
        students_without_submissions = max(student_total - with_submissions, 0)
        rows.append(
            {
                "classroom": classroom,
                "student_total": student_total,
                "new_students_since": int(new_students_since.get(classroom_id, 0)),
                "submission_total_since": int(submission_totals_since.get(classroom_id, 0)),
                "helper_access_total_since": int(helper_events_since.get(classroom_id, 0)),
                "students_without_submissions": students_without_submissions,
                "last_submission_at": last_submission_at.get(classroom_id),
            }
        )
    return rows


def _local_day_window() -> tuple[timezone.datetime, timezone.datetime]:
    today = timezone.localdate()
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, dt_time.min), zone)
    end = start + timedelta(days=1)
    return start, end


def _build_lesson_tracker_rows(request, classroom_id: int, modules: list[Module], student_count: int) -> list[dict]:
    rows: list[dict] = []
    upload_material_ids = []
    module_materials_map: dict[int, list[Material]] = {}
    teacher_material_html_by_lesson: dict[tuple[str, str], str] = {}
    lesson_title_by_lesson: dict[tuple[str, str], str] = {}
    lesson_release_by_lesson: dict[tuple[str, str], dict] = {}
    helper_defaults_by_lesson: dict[tuple[str, str], dict] = {}
    release_override_map = lesson_release_override_map(classroom_id)

    for module in modules:
        mats = list(module.materials.all())
        mats.sort(key=lambda m: (m.order_index, m.id))
        module_materials_map[module.id] = mats
        for mat in mats:
            if mat.type == Material.TYPE_UPLOAD:
                upload_material_ids.append(mat.id)

    submission_counts = _material_submission_counts(upload_material_ids)
    latest_upload_map = _material_latest_upload_map(upload_material_ids)

    for module in modules:
        mats = module_materials_map.get(module.id, [])
        dropboxes = []
        for mat in mats:
            if mat.type != Material.TYPE_UPLOAD:
                continue
            submitted = submission_counts.get(mat.id, 0)
            dropboxes.append(
                {
                    "id": mat.id,
                    "title": mat.title,
                    "submitted": submitted,
                    "missing": max(student_count - submitted, 0),
                    "last_uploaded_at": latest_upload_map.get(mat.id),
                }
            )

        review_dropbox = None
        if dropboxes:
            review_dropbox = max(dropboxes, key=lambda d: (d["missing"], d["submitted"], -int(d["id"])))

        if review_dropbox and review_dropbox["missing"] > 0:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions?show=missing"
            review_label = f"Review missing now ({review_dropbox['missing']})"
        elif review_dropbox:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions"
            review_label = "Review submissions"
        else:
            review_url = ""
            review_label = ""

        seen_lessons = set()
        for mat in mats:
            if mat.type != Material.TYPE_LINK:
                continue
            parsed = parse_course_lesson_url(mat.url)
            if not parsed:
                continue
            lesson_key = parsed
            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)
            course_slug, lesson_slug = parsed

            if lesson_key not in teacher_material_html_by_lesson:
                teacher_material_html_by_lesson[lesson_key] = load_teacher_material_html(course_slug, lesson_slug)
                try:
                    front_matter, _body_markdown, lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
                except ValueError:
                    front_matter = {}
                    lesson_meta = {}
                lesson_title_by_lesson[lesson_key] = (
                    str(front_matter.get("title") or "").strip() or mat.title
                )
                helper_defaults_by_lesson[lesson_key] = {
                    "context": str(front_matter.get("title") or lesson_slug).strip() or lesson_slug,
                    "topics": _build_lesson_topics(front_matter),
                    "allowed_topics": _build_allowed_topics(front_matter),
                    "reference": str(lesson_meta.get("helper_reference") or "").strip(),
                }
                lesson_release_by_lesson[lesson_key] = lesson_release_state(
                    request,
                    front_matter,
                    lesson_meta,
                    classroom_id=classroom_id,
                    course_slug=course_slug,
                    lesson_slug=lesson_slug,
                    override_map=release_override_map,
                    respect_staff_bypass=False,
                )

            release_override = release_override_map.get(lesson_key)
            helper_context_override = (getattr(release_override, "helper_context_override", "") or "").strip()
            helper_topics_override = (getattr(release_override, "helper_topics_override", "") or "").strip()
            helper_allowed_topics_override = (getattr(release_override, "helper_allowed_topics_override", "") or "").strip()
            helper_reference_override = (getattr(release_override, "helper_reference_override", "") or "").strip()
            has_helper_override = bool(
                helper_context_override
                or helper_topics_override
                or helper_allowed_topics_override
                or helper_reference_override
            )

            helper_defaults = helper_defaults_by_lesson.get(
                lesson_key,
                {"context": lesson_slug, "topics": [], "allowed_topics": [], "reference": ""},
            )
            rows.append(
                {
                    "module": module,
                    "lesson_title": lesson_title_by_lesson.get(lesson_key, mat.title),
                    "lesson_url": mat.url,
                    "course_slug": course_slug,
                    "lesson_slug": lesson_slug,
                    "dropboxes": dropboxes,
                    "review_url": review_url,
                    "review_label": review_label,
                    "teacher_material_html": teacher_material_html_by_lesson.get(lesson_key, ""),
                    "release_state": lesson_release_by_lesson.get(lesson_key, {}),
                    "helper_tuning": {
                        "has_override": has_helper_override,
                        "context_value": helper_context_override,
                        "topics_value": helper_topics_override,
                        "allowed_topics_value": helper_allowed_topics_override,
                        "reference_value": helper_reference_override,
                        "default_context": helper_defaults.get("context", ""),
                        "default_topics": helper_defaults.get("topics", []),
                        "default_allowed_topics": helper_defaults.get("allowed_topics", []),
                        "default_reference": helper_defaults.get("reference", ""),
                    },
                }
            )

    return rows


def _safe_teacher_return_path(raw: str, fallback: str) -> str:
    parsed = urlparse((raw or "").strip())
    if parsed.scheme or parsed.netloc:
        return fallback
    if not parsed.path.startswith("/teach"):
        return fallback
    return (raw or "").strip() or fallback


def _teach_class_path(class_id: int | str) -> str:
    try:
        parsed_id = int(class_id)
    except Exception:
        return "/teach"
    if parsed_id <= 0:
        return "/teach"
    return f"/teach/class/{parsed_id}"


def _teach_module_path(module_id: int | str) -> str:
    try:
        parsed_id = int(module_id)
    except Exception:
        return "/teach"
    if parsed_id <= 0:
        return "/teach"
    return f"/teach/module/{parsed_id}"


def _safe_internal_redirect(request, to: str, fallback: str = "/teach"):
    candidate = (to or "").strip() or fallback
    if candidate.startswith("//"):
        candidate = fallback
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        candidate = fallback
    if not candidate.startswith("/"):
        candidate = fallback
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        candidate = fallback
    # Keep redirects local-only and avoid framework URL sink ambiguity for static analysis.
    response = HttpResponse(status=302)
    response["Location"] = candidate
    return response


def _with_notice(path: str, notice: str = "", error: str = "", extra: dict | None = None) -> str:
    params = {}
    if notice:
        params["notice"] = notice
    if error:
        params["error"] = error
    for key, value in (extra or {}).items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            params[key] = text
    if not params:
        return path
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}{urlencode(params)}"


def _audit(request, *, action: str, summary: str = "", classroom=None, target_type: str = "", target_id: str = "", metadata=None):
    log_audit_event(
        request,
        action=action,
        summary=summary,
        classroom=classroom,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )


def _lesson_video_redirect_params(course_slug: str, lesson_slug: str, class_id: int = 0, notice: str = "") -> str:
    query = {"course_slug": course_slug, "lesson_slug": lesson_slug}
    if class_id:
        query["class_id"] = str(class_id)
    if notice:
        query["notice"] = notice
    return urlencode(query)


def _normalize_optional_slug_tag(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", (raw or "").strip().lower())
    return value.strip("-_")


def _parse_positive_int(raw: str, *, min_value: int, max_value: int) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < min_value or parsed > max_value:
        return None
    return parsed


def _split_helper_topics_text(raw: str) -> list[str]:
    parts: list[str] = []
    normalized = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.split("\n"):
        for segment in line.split("|"):
            token = segment.strip()
            if token:
                parts.append(token)
    return parts


def _normalize_helper_topics_text(raw: str) -> str:
    return "\n".join(_split_helper_topics_text(raw))


def _authoring_template_output_dir() -> Path:
    return Path(getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_DIR", "/uploads/authoring_templates"))


def _resolve_authoring_template_download_path(slug: str, suffix: str) -> Path | None:
    output_dir = _authoring_template_output_dir().resolve()
    try:
        joined = safe_join(str(output_dir), f"{slug}-{suffix}")
    except Exception:
        return None
    candidate = Path(joined).resolve()
    if not candidate.is_relative_to(output_dir):
        return None
    return candidate


def _lesson_asset_redirect_params(folder_id: int = 0, course_slug: str = "", lesson_slug: str = "", status: str = "all", notice: str = "") -> str:
    query = {"status": status or "all"}
    if folder_id:
        query["folder_id"] = str(folder_id)
    if course_slug:
        query["course_slug"] = course_slug
    if lesson_slug:
        query["lesson_slug"] = lesson_slug
    if notice:
        query["notice"] = notice
    return urlencode(query)
