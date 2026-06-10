"""Course lesson rendering endpoint callables."""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import translation
from common.helper_scope import issue_scope_token
from config.localization import (
    localization_from_request,
    request_language_override,
    resolve_request_language,
)

from ..services.content_links import (
    normalize_lesson_videos,
)
from ..services.lesson_page import (
    apply_helper_release_overrides,
    build_lesson_helper_widget,
    build_lesson_upload_context,
    helper_scope_signing_key,
    intro_only_markdown,
    normalize_stored_lesson_videos,
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


def _staff_preview_classroom(request):
    if not (request.user.is_authenticated and request.user.is_staff):
        return None
    try:
        class_id = int((request.GET.get("class_id") or "0").strip())
    except Exception:
        return None
    return staff_classroom_or_none(request.user, class_id)


def course_lesson(request, course_slug: str, lesson_slug: str):
    """Render a markdown lesson page from disk."""
    requested_language = resolve_request_language(request, request.GET.get("lang"))
    with request_language_override(request, requested_language) as localization:
        return _render_course_lesson(
            request=request,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            localization=localization,
        )


def _load_course_lesson_source(*, request, course_slug: str, lesson_slug: str):
    manifest = load_course_manifest(course_slug)
    if not manifest:
        return None, HttpResponse("Course not found", status=404)

    effective_classroom = getattr(request, "classroom", None) or _staff_preview_classroom(request)
    classroom_id = getattr(effective_classroom, "id", 0) or 0
    raw_markdown_override = None
    if classroom_id:
        from ..models import ClassLessonOverride

        override = ClassLessonOverride.objects.filter(
            classroom_id=classroom_id,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
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
        return None, HttpResponse("Lesson metadata invalid.", status=500)
    if not body_md:
        return None, HttpResponse("Lesson not found", status=404)

    return {
        "manifest": manifest,
        "effective_classroom": effective_classroom,
        "classroom_id": classroom_id,
        "front_matter": fm,
        "body_md": body_md,
        "lesson_meta": lesson_meta,
    }, None


def _build_lesson_release_content(*, request, course_slug: str, lesson_slug: str, front_matter: dict, body_md: str, lesson_meta: dict, classroom_id: int):
    learner_body_md, _teacher_body_md = split_lesson_markdown_for_audiences(body_md)
    release_override_map = lesson_release_override_map(classroom_id) if classroom_id else {}
    release_override = release_override_map.get((course_slug, lesson_slug))
    release_state = lesson_release_state(
        request,
        front_matter,
        lesson_meta,
        classroom_id=classroom_id,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        override_map=release_override_map,
    )
    lesson_locked = bool(release_state.get("is_locked"))
    if lesson_locked:
        learner_body_md = intro_only_markdown(learner_body_md)
    if not learner_body_md.strip():
        learner_body_md = "### Learner activity\nAsk your teacher for today's activity steps.\n"

    lesson_videos = normalize_lesson_videos(front_matter)
    lesson_videos.extend(normalize_stored_lesson_videos(course_slug, lesson_slug))
    if lesson_locked:
        lesson_videos = []

    return {
        "html": render_markdown_to_safe_html(learner_body_md),
        "lesson_videos": lesson_videos,
        "release_override": release_override,
        "lesson_locked": lesson_locked,
        "lesson_available_on": release_state.get("available_on"),
    }


def _lesson_prev_next(manifest: dict, lesson_slug: str):
    lessons = manifest.get("lessons") or []
    idx = next((i for i, lesson in enumerate(lessons) if lesson.get("slug") == lesson_slug), None)
    prev_lesson = lessons[idx - 1] if isinstance(idx, int) and idx > 0 else None
    next_lesson = lessons[idx + 1] if isinstance(idx, int) and idx + 1 < len(lessons) else None
    return prev_lesson, next_lesson


def _build_lesson_handout_upload(*, request, course_slug: str, lesson_slug: str, manifest: dict, front_matter: dict, lesson_locked: bool, localization):
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    lesson_path = f"/course/{course_slug}/{lesson_slug}"
    handout = build_handout_context(
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        course_manifest=manifest,
        front_matter=front_matter,
        request=request,
        reading_level=selected_reading_level,
        online_path=lesson_path,
        language_code=localization.code,
    )
    lesson_submission = front_matter_submission(front_matter)
    lesson_upload_material, lesson_upload_status = build_lesson_upload_context(
        request=request,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        lesson_locked=lesson_locked,
        lesson_submission=lesson_submission,
    )
    return {
        "selected_reading_level": selected_reading_level,
        "lesson_handout": handout,
        "lesson_submission": lesson_submission,
        "lesson_upload_material": lesson_upload_material,
        "lesson_upload_status": lesson_upload_status,
    }


def _build_lesson_helper(*, request, lesson_slug: str, manifest: dict, front_matter: dict, lesson_meta: dict, release_override, lesson_locked: bool, localization, ui_density_mode: str):
    helper_context = front_matter.get("title") or lesson_slug
    helper_topics = build_lesson_topics(front_matter)
    helper_allowed_topics = build_allowed_topics(front_matter)
    helper_reference = lesson_meta.get("helper_reference") or manifest.get("helper_reference") or ""
    helper_context, helper_topics, helper_allowed_topics, helper_reference = apply_helper_release_overrides(
        release_override=release_override,
        helper_context=helper_context,
        helper_topics=helper_topics,
        helper_allowed_topics=helper_allowed_topics,
        helper_reference=helper_reference,
        split_topics=split_helper_topics_text,
    )
    helper_scope_token = issue_scope_token(
        context=helper_context,
        topics=helper_topics,
        allowed_topics=helper_allowed_topics,
        reference=helper_reference,
        signing_key=helper_scope_signing_key(),
    )
    return build_lesson_helper_widget(
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


def _lesson_template_context(*, request, course_slug: str, lesson_slug: str, manifest: dict, effective_classroom, front_matter: dict, ui_density_mode: str, lesson_render: dict, prev_lesson, next_lesson, helper_widget, handout_upload: dict):
    return {
        "course_slug": course_slug,
        "course": manifest,
        "lesson_slug": lesson_slug,
        "front_matter": front_matter,
        "lesson_html": lesson_render["html"],
        "lesson_videos": lesson_render["lesson_videos"],
        "prev": prev_lesson,
        "next": next_lesson,
        "helper_widget": helper_widget,
        "student": getattr(request, "student", None),
        "classroom": effective_classroom,
        "lesson_submission": handout_upload["lesson_submission"],
        "lesson_upload_material": handout_upload["lesson_upload_material"],
        "lesson_upload_status": handout_upload["lesson_upload_status"],
        "lesson_locked": lesson_render["lesson_locked"],
        "lesson_available_on": lesson_render["lesson_available_on"],
        "ui_density_mode": ui_density_mode,
        "can_edit_lesson_override": staff_can_manage_classroom(request.user, effective_classroom),
        "selected_reading_level": handout_upload["selected_reading_level"],
        "local_anchors": resolve_local_anchors(front_matter=front_matter),
        "example_variants": resolve_example_variants(course_manifest=manifest, front_matter=front_matter),
        "community_glossary": resolve_community_glossary(course_manifest=manifest, front_matter=front_matter),
        "lesson_handout": handout_upload["lesson_handout"],
    }


def _render_course_lesson(*, request, course_slug: str, lesson_slug: str, localization):
    lesson_source, error_response = _load_course_lesson_source(request=request, course_slug=course_slug, lesson_slug=lesson_slug)
    if error_response is not None:
        return error_response
    manifest = lesson_source["manifest"]
    effective_classroom = lesson_source["effective_classroom"]
    classroom_id, front_matter, lesson_meta = (
        lesson_source["classroom_id"],
        lesson_source["front_matter"],
        lesson_source["lesson_meta"],
    )
    ui_density_mode = resolve_ui_density_mode(program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary"), course_manifest=manifest, lesson_front_matter=front_matter)
    lesson_render = _build_lesson_release_content(
        request=request,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        front_matter=front_matter,
        body_md=lesson_source["body_md"],
        lesson_meta=lesson_meta,
        classroom_id=classroom_id,
    )
    prev_lesson, next_lesson = _lesson_prev_next(manifest, lesson_slug)
    handout_upload = _build_lesson_handout_upload(
        request=request,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        manifest=manifest,
        front_matter=front_matter,
        lesson_locked=lesson_render["lesson_locked"],
        localization=localization,
    )
    helper_widget = _build_lesson_helper(
        request=request,
        lesson_slug=lesson_slug,
        manifest=manifest,
        front_matter=front_matter,
        lesson_meta=lesson_meta,
        release_override=lesson_render["release_override"],
        lesson_locked=lesson_render["lesson_locked"],
        localization=localization,
        ui_density_mode=ui_density_mode,
    )
    context = _lesson_template_context(request=request, course_slug=course_slug, lesson_slug=lesson_slug, manifest=manifest, effective_classroom=effective_classroom, front_matter=front_matter, ui_density_mode=ui_density_mode, lesson_render=lesson_render, prev_lesson=prev_lesson, next_lesson=next_lesson, helper_widget=helper_widget, handout_upload=handout_upload)
    with translation.override(localization.code):
        return render(request, "lesson_page.html", context)
__all__ = [
    "course_lesson",
]
