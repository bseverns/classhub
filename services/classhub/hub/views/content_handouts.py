"""Offline lesson handout endpoints."""

import logging

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import translation
from config.localization import localization_from_request, request_language_override, resolve_request_language

from ..services.lesson_handouts import (
    build_handout_context,
    build_handout_pdf_bytes,
    build_handout_qr_svg,
    resolve_reading_level,
)
from ..services.markdown_content import load_course_manifest, load_lesson_markdown

logger = logging.getLogger(__name__)


def _load_handout_source(course_slug: str, lesson_slug: str):
    manifest = load_course_manifest(course_slug)
    if not manifest:
        return None, None, HttpResponse("Course not found", status=404)

    try:
        fm, body_md, _lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
    except ValueError:
        logger.warning(
            "lesson_handout_metadata_invalid course_slug=%s lesson_slug=%s",
            course_slug,
            lesson_slug,
            exc_info=True,
        )
        return None, None, HttpResponse("Lesson metadata invalid.", status=500)
    if not body_md:
        return None, None, HttpResponse("Lesson not found", status=404)
    return manifest, fm, None


def _build_handout(request, *, course_slug: str, lesson_slug: str, manifest: dict, front_matter: dict) -> tuple[str, dict]:
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    localization = localization_from_request(request)
    handout = build_handout_context(
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        course_manifest=manifest,
        front_matter=front_matter,
        request=request,
        reading_level=selected_reading_level,
        online_path=f"/course/{course_slug}/{lesson_slug}",
        language_code=localization.code,
    )
    return selected_reading_level, handout


def course_lesson_handout(request, course_slug: str, lesson_slug: str):
    manifest, front_matter, error_response = _load_handout_source(course_slug, lesson_slug)
    if error_response is not None:
        return error_response

    requested_language = resolve_request_language(request, request.GET.get("lang"))
    with request_language_override(request, requested_language):
        selected_reading_level, handout = _build_handout(
            request,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            manifest=manifest,
            front_matter=front_matter,
        )
        with translation.override(localization_from_request(request).code):
            return render(
                request,
                "lesson_handout.html",
                {
                    "course_slug": course_slug,
                    "lesson_slug": lesson_slug,
                    "course": manifest,
                    "front_matter": front_matter,
                    "selected_reading_level": selected_reading_level,
                    "lesson_handout": handout,
                    "handout_qr_svg": build_handout_qr_svg(handout["online_url"]),
                },
            )


def course_lesson_handout_pdf(request, course_slug: str, lesson_slug: str):
    manifest, front_matter, error_response = _load_handout_source(course_slug, lesson_slug)
    if error_response is not None:
        return error_response

    requested_language = resolve_request_language(request, request.GET.get("lang"))
    with request_language_override(request, requested_language):
        _selected_reading_level, handout = _build_handout(
            request,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            manifest=manifest,
            front_matter=front_matter,
        )
        with translation.override(localization_from_request(request).code):
            response = HttpResponse(build_handout_pdf_bytes(handout), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{course_slug}-{lesson_slug}-handout.pdf"'
    return response


__all__ = [
    "course_lesson_handout",
    "course_lesson_handout_pdf",
]
