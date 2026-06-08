"""Course catalog endpoints kept separate from lesson rendering."""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from ..services.lesson_handouts import resolve_reading_level
from ..services.content_links import courses_dir
from ..services.markdown_content import load_course_manifest
from ..services.ui_density import resolve_ui_density_mode


def course_overview(request, course_slug: str):
    """Tiny course landing page."""
    manifest = load_course_manifest(course_slug)
    if not manifest:
        return HttpResponse("Course not found", status=404)

    ui_density_mode = resolve_ui_density_mode(
        program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary"),
        course_manifest=manifest,
    )
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))

    return render(
        request,
        "course_overview.html",
        {
            "course_slug": course_slug,
            "course": manifest,
            "lessons": manifest.get("lessons") or [],
            "ui_density_mode": ui_density_mode,
            "selected_reading_level": selected_reading_level,
        },
    )


def iter_course_lesson_options() -> list[dict]:
    """Enumerate lesson options from course manifests for teacher tooling."""
    options: list[dict] = []
    root = courses_dir()
    if not root.exists():
        return options

    for manifest_path in sorted(root.glob("*/course.yaml")):
        course_slug = manifest_path.parent.name
        manifest = load_course_manifest(course_slug)
        course_title = str(manifest.get("title") or course_slug).strip()
        lessons = manifest.get("lessons") or []
        for lesson in lessons:
            lesson_slug = str(lesson.get("slug") or "").strip()
            if not lesson_slug:
                continue
            lesson_title = str(lesson.get("title") or lesson_slug).strip()
            options.append(
                {
                    "course_slug": course_slug,
                    "course_title": course_title,
                    "lesson_slug": lesson_slug,
                    "lesson_title": lesson_title,
                    "session": lesson.get("session"),
                }
            )
    return options


__all__ = [
    "course_overview",
    "iter_course_lesson_options",
]
