"""Shared helpers for lesson page rendering."""

from urllib.parse import urlsplit

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from ..models import LessonVideo, Material, Module, Submission
from .content_links import (
    build_asset_url,
    extract_youtube_id,
    is_probably_video_url,
    video_mime_type,
    youtube_embed_url,
)
from .helper_widget import build_helper_prompt_sets_json


def helper_scope_signing_key() -> str:
    return str(getattr(settings, "HELPER_SCOPE_SIGNING_KEY", "") or "")


def intro_only_markdown(learner_markdown: str) -> str:
    lines = learner_markdown.splitlines()
    collected: list[str] = []
    for line in lines:
        if line.startswith("## "):
            break
        collected.append(line)
    intro = "\n".join(collected).strip()
    if intro:
        return intro + "\n"
    return "### Intro\nYour teacher will open the full lesson on the scheduled date.\n"


def normalize_stored_lesson_videos(course_slug: str, lesson_slug: str) -> list[dict]:
    try:
        rows = list(
            LessonVideo.objects.filter(course_slug=course_slug, lesson_slug=lesson_slug, is_active=True)
            .order_by("order_index", "id")
        )
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonvideo" in str(exc).lower():
            return []
        raise
    normalized = []
    for row in rows:
        url = (row.source_url or "").strip()
        if row.video_file:
            media_url = build_asset_url(f"/lesson-video/{row.id}/stream")
            media_type = video_mime_type(row.video_file.name)
            source_type = "native"
            embed_url = ""
        else:
            youtube_id = extract_youtube_id(url)
            if youtube_id:
                source_type = "youtube"
                embed_url = youtube_embed_url(youtube_id)
                media_url = ""
                media_type = ""
            elif is_probably_video_url(url):
                source_type = "native"
                embed_url = ""
                media_url = url
                media_type = video_mime_type(url)
            else:
                source_type = "link"
                embed_url = ""
                media_url = ""
                media_type = ""

        normalized.append(
            {
                "id": f"asset-{row.id}",
                "title": row.title,
                "minutes": row.minutes,
                "outcome": row.outcome,
                "url": url or media_url,
                "embed_url": embed_url,
                "source_type": source_type,
                "media_url": media_url,
                "media_type": media_type,
            }
        )
    return normalized


def build_lesson_upload_context(
    *,
    request: HttpRequest,
    course_slug: str,
    lesson_slug: str,
    lesson_locked: bool,
    lesson_submission: dict,
) -> tuple[Material | None, dict]:
    if (
        lesson_locked
        or lesson_submission.get("type") != "file"
        or getattr(request, "student", None) is None
        or getattr(request, "classroom", None) is None
    ):
        return None, {}

    lesson_url = f"/course/{course_slug}/{lesson_slug}"
    module_ids = (
        Module.objects.filter(
            classroom_id=request.classroom.id,
            materials__type=Material.TYPE_LINK,
            materials__url=lesson_url,
        )
        .order_by("order_index", "id")
        .values_list("id", flat=True)
    )
    if not module_ids:
        return None, {}

    lesson_upload_material = (
        Material.objects.filter(module_id__in=module_ids, type=Material.TYPE_UPLOAD)
        .order_by("module__order_index", "order_index", "id")
        .first()
    )
    if lesson_upload_material is None:
        return None, {}

    student_submissions = Submission.objects.filter(
        material=lesson_upload_material,
        student=request.student,
    )
    latest = student_submissions.only("id", "uploaded_at").first()
    if latest is None:
        return lesson_upload_material, {}
    return lesson_upload_material, {
        "count": student_submissions.count(),
        "last_uploaded_at": latest.uploaded_at,
        "last_id": latest.id,
    }


def apply_helper_release_overrides(
    *,
    release_override,
    helper_context: str,
    helper_topics: list[str],
    helper_allowed_topics: list[str],
    helper_reference: str,
    split_topics,
) -> tuple[str, list[str], list[str], str]:
    if not release_override:
        return helper_context, helper_topics, helper_allowed_topics, helper_reference

    helper_context_override = (release_override.helper_context_override or "").strip()
    helper_topics_override = split_topics(release_override.helper_topics_override)
    helper_allowed_topics_override = split_topics(release_override.helper_allowed_topics_override)
    helper_reference_override = (release_override.helper_reference_override or "").strip()
    if helper_context_override:
        helper_context = helper_context_override
    if helper_topics_override:
        helper_topics = helper_topics_override
    if helper_allowed_topics_override:
        helper_allowed_topics = helper_allowed_topics_override
    if helper_reference_override:
        helper_reference = helper_reference_override
    return helper_context, helper_topics, helper_allowed_topics, helper_reference


def build_lesson_helper_widget(
    *,
    request: HttpRequest,
    lesson_locked: bool,
    helper_context: str,
    helper_topics: list[str],
    helper_allowed_topics: list[str],
    helper_reference: str,
    localization,
    ui_density_mode: str,
    helper_scope_token: str,
) -> str:
    can_use_helper = bool(
        getattr(request, "student", None) is not None
        or (request.user.is_authenticated and request.user.is_staff)
    )
    if lesson_locked or not can_use_helper:
        return ""

    get_token(request)
    helper_delete_url = "/student/my-data" if getattr(request, "student", None) is not None else "/teach"
    helper_description = _("Need a hint for this lesson? Ask the helper to guide you without handing out answers.")
    if ui_density_mode == "compact":
        helper_description = _("Need help? Ask for one small next step at a time.")
    elif ui_density_mode == "expanded":
        helper_description = _("Ask for strategy, debugging, or extension ideas without asking for direct answers.")
    return render_to_string(
        "includes/helper_widget.html",
        {
            "helper_title": _("Lesson helper"),
            "helper_description": helper_description,
            "helper_context": helper_context,
            "helper_topics": " | ".join(helper_topics),
            "helper_reference": helper_reference,
            "helper_allowed_topics": " | ".join(helper_allowed_topics),
            "helper_backend_label": _helper_backend_label(),
            "helper_delete_url": helper_delete_url,
            "helper_language_code": localization.helper_code,
            "helper_prompt_sets_json": build_helper_prompt_sets_json(),
            "student_event_retention_days": _retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180),
            "helper_scope_token": helper_scope_token,
        },
        request=request,
    )


def _helper_backend_label() -> str:
    backend = (getattr(settings, "HELPER_LLM_BACKEND", "ollama") or "ollama").strip().lower()
    base_url = str(getattr(settings, "LLM_BASE_URL", "") or "").strip()
    host = (urlsplit(base_url).hostname or "").strip().lower()
    is_remote_ollama = backend == "ollama" and host not in {"", "localhost", "127.0.0.1", "ollama", "classhub_ollama"}
    if backend in {"openai", "openai_responses", "openai_compatible"}:
        return _("Private remote model")
    if is_remote_ollama:
        return _("Private remote model")
    if backend == "ollama":
        return _("Local model (Ollama)")
    if backend == "mock":
        return _("Mock model (Test mode)")
    return _("Model backend (Unknown)")


def _retention_days(setting_name: str, default: int) -> int:
    raw = getattr(settings, setting_name, default)
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    return value if value > 0 else 0
