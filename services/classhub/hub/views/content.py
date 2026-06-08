"""Course lesson rendering endpoint callables."""

import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from common.helper_scope import issue_scope_token
from config.localization import localization_from_request

from ..models import LessonVideo, Material, Module, Submission
from ..services.content_links import (
    build_asset_url,
    extract_youtube_id,
    is_probably_video_url,
    normalize_lesson_videos,
    youtube_embed_url,
    video_mime_type,
)
from ..services.markdown_content import (
    load_course_manifest,
    load_lesson_markdown,
    render_markdown_to_safe_html,
    split_lesson_markdown_for_audiences,
)
from ..services.helper_topics import (
    build_allowed_topics,
    build_lesson_topics,
    split_helper_topics_text,
)
from ..services.helper_widget import build_helper_prompt_sets_json
from ..services.lesson_handouts import (
    build_handout_context,
    resolve_community_glossary,
    resolve_example_variants,
    resolve_local_anchors,
    resolve_reading_level,
)
from ..services.org_access import staff_can_manage_classroom, staff_classroom_or_none
from ..services.release_state import lesson_release_override_map, lesson_release_state
from ..services.upload_policy import front_matter_submission
from ..services.ui_density import resolve_ui_density_mode

logger = logging.getLogger(__name__)


def _helper_scope_signing_key() -> str:
    return str(getattr(settings, "HELPER_SCOPE_SIGNING_KEY", "") or "")


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


def _staff_preview_classroom(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return None
    try:
        class_id = int((request.GET.get("class_id") or "0").strip())
    except Exception:
        return None
    return staff_classroom_or_none(request.user, class_id)


def _intro_only_markdown(learner_markdown: str) -> str:
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


def _find_lesson_upload_material(classroom_id: int, course_slug: str, lesson_slug: str):
    """Find the upload material linked to a lesson for a specific class."""
    lesson_url = f"/course/{course_slug}/{lesson_slug}"
    module_ids = (
        Module.objects.filter(
            classroom_id=classroom_id,
            materials__type=Material.TYPE_LINK,
            materials__url=lesson_url,
        )
        .order_by("order_index", "id")
        .values_list("id", flat=True)
    )
    if not module_ids:
        return None

    return (
        Material.objects.filter(module_id__in=module_ids, type=Material.TYPE_UPLOAD)
        .order_by("module__order_index", "order_index", "id")
        .first()
    )


def _normalize_stored_lesson_videos(course_slug: str, lesson_slug: str) -> list[dict]:
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


def _lesson_upload_context(
    *,
    request,
    course_slug: str,
    lesson_slug: str,
    lesson_locked: bool,
    lesson_submission: dict,
) -> tuple[Material | None, dict]:
    lesson_upload_material = None
    lesson_upload_status: dict = {}
    if (
        lesson_locked
        or lesson_submission.get("type") != "file"
        or getattr(request, "student", None) is None
        or getattr(request, "classroom", None) is None
    ):
        return lesson_upload_material, lesson_upload_status

    lesson_upload_material = _find_lesson_upload_material(request.classroom.id, course_slug, lesson_slug)
    if lesson_upload_material is None:
        return lesson_upload_material, lesson_upload_status

    student_submissions = Submission.objects.filter(
        material=lesson_upload_material,
        student=request.student,
    )
    latest = student_submissions.only("id", "uploaded_at").first()
    if latest is not None:
        lesson_upload_status = {
            "count": student_submissions.count(),
            "last_uploaded_at": latest.uploaded_at,
            "last_id": latest.id,
        }
    return lesson_upload_material, lesson_upload_status


def _apply_helper_release_overrides(
    *,
    release_override,
    helper_context: str,
    helper_topics: list[str],
    helper_allowed_topics: list[str],
    helper_reference: str,
) -> tuple[str, list[str], list[str], str]:
    if not release_override:
        return helper_context, helper_topics, helper_allowed_topics, helper_reference

    helper_context_override = (release_override.helper_context_override or "").strip()
    helper_topics_override = split_helper_topics_text(release_override.helper_topics_override)
    helper_allowed_topics_override = split_helper_topics_text(release_override.helper_allowed_topics_override)
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


def _build_lesson_helper_widget(
    *,
    request,
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


def course_lesson(request, course_slug: str, lesson_slug: str):
    """Render a markdown lesson page from disk."""
    localization = localization_from_request(request)
    manifest = load_course_manifest(course_slug)
    if not manifest:
        return HttpResponse("Course not found", status=404)

    effective_classroom = getattr(request, "classroom", None) or _staff_preview_classroom(request)
    classroom_id = getattr(effective_classroom, "id", 0) or 0
    raw_markdown_override = None
    if classroom_id:
        from ..models import ClassLessonOverride
        override = ClassLessonOverride.objects.filter(
            classroom_id=classroom_id, course_slug=course_slug, lesson_slug=lesson_slug
        ).first()
        if override and override.raw_markdown.strip():
            raw_markdown_override = override.raw_markdown

    try:
        if raw_markdown_override:
            fm, body_md, lesson_meta = load_lesson_markdown(
                course_slug,
                lesson_slug,
                raw_markdown_override=raw_markdown_override,
            )
        else:
            fm, body_md, lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
    except ValueError:
        logger.warning(
            "lesson_metadata_invalid course_slug=%s lesson_slug=%s",
            course_slug,
            lesson_slug,
            exc_info=True,
        )
        return HttpResponse("Lesson metadata invalid.", status=500)
    if not body_md:
        return HttpResponse("Lesson not found", status=404)

    ui_density_mode = resolve_ui_density_mode(
        program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary"),
        course_manifest=manifest,
        lesson_front_matter=fm,
    )

    learner_body_md, _teacher_body_md = split_lesson_markdown_for_audiences(body_md)
    release_override_map = lesson_release_override_map(classroom_id) if classroom_id else {}
    release_override = release_override_map.get((course_slug, lesson_slug))
    release_state = lesson_release_state(
        request,
        fm,
        lesson_meta,
        classroom_id=classroom_id,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        override_map=release_override_map,
    )
    lesson_locked = bool(release_state.get("is_locked"))
    lesson_available_on = release_state.get("available_on")

    if lesson_locked:
        learner_body_md = _intro_only_markdown(learner_body_md)

    if not learner_body_md.strip():
        learner_body_md = "### Learner activity\nAsk your teacher for today's activity steps.\n"
    html = render_markdown_to_safe_html(learner_body_md)
    lesson_videos = normalize_lesson_videos(fm)
    lesson_videos.extend(_normalize_stored_lesson_videos(course_slug, lesson_slug))
    if lesson_locked:
        lesson_videos = []

    lessons = manifest.get("lessons") or []
    idx = next((i for i, l in enumerate(lessons) if l.get("slug") == lesson_slug), None)
    prev_l = lessons[idx - 1] if isinstance(idx, int) and idx > 0 else None
    next_l = lessons[idx + 1] if isinstance(idx, int) and idx + 1 < len(lessons) else None

    helper_context = fm.get("title") or lesson_slug
    helper_topics = build_lesson_topics(fm)
    helper_allowed_topics = build_allowed_topics(fm)
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    lesson_path = f"/course/{course_slug}/{lesson_slug}"
    handout = build_handout_context(
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        course_manifest=manifest,
        front_matter=fm,
        request=request,
        reading_level=selected_reading_level,
        online_path=lesson_path,
        language_code=localization.code,
    )
    lesson_submission = front_matter_submission(fm)
    lesson_upload_material, lesson_upload_status = _lesson_upload_context(
        request=request,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        lesson_locked=lesson_locked,
        lesson_submission=lesson_submission,
    )

    helper_reference = lesson_meta.get("helper_reference") or manifest.get("helper_reference") or ""
    helper_context, helper_topics, helper_allowed_topics, helper_reference = _apply_helper_release_overrides(
        release_override=release_override,
        helper_context=helper_context,
        helper_topics=helper_topics,
        helper_allowed_topics=helper_allowed_topics,
        helper_reference=helper_reference,
    )

    helper_scope_token = issue_scope_token(
        context=helper_context,
        topics=helper_topics,
        allowed_topics=helper_allowed_topics,
        reference=helper_reference,
        signing_key=_helper_scope_signing_key(),
    )
    helper_widget = _build_lesson_helper_widget(
        request=request,
        lesson_locked=lesson_locked,
        helper_context=helper_context,
        helper_topics=helper_topics,
        helper_allowed_topics=helper_allowed_topics,
        helper_reference=helper_reference,
        localization=localization,
        ui_density_mode=ui_density_mode,
        helper_scope_token=helper_scope_token,
    )

    return render(
        request,
        "lesson_page.html",
        {
            "course_slug": course_slug,
            "course": manifest,
            "lesson_slug": lesson_slug,
            "front_matter": fm,
            "lesson_html": html,
            "lesson_videos": lesson_videos,
            "prev": prev_l,
            "next": next_l,
            "helper_widget": helper_widget,
            "student": getattr(request, "student", None),
            "classroom": effective_classroom,
            "lesson_submission": lesson_submission,
            "lesson_upload_material": lesson_upload_material,
            "lesson_upload_status": lesson_upload_status,
            "lesson_locked": lesson_locked,
            "lesson_available_on": lesson_available_on,
            "ui_density_mode": ui_density_mode,
            "can_edit_lesson_override": staff_can_manage_classroom(request.user, effective_classroom),
            "selected_reading_level": selected_reading_level,
            "local_anchors": resolve_local_anchors(front_matter=fm),
            "example_variants": resolve_example_variants(course_manifest=manifest, front_matter=fm),
            "community_glossary": resolve_community_glossary(course_manifest=manifest, front_matter=fm),
            "lesson_handout": handout,
        },
    )
__all__ = [
    "course_lesson",
]
