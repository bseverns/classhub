"""Teacher class-local lesson override editor endpoints."""

from urllib.parse import urlencode

from django.shortcuts import redirect

from hub.models import ClassLessonOverride
from hub.services.markdown_content import _safe_course_file_path, load_course_manifest, load_lesson_markdown

from .shared import (
    _audit,
    _safe_internal_redirect,
    render,
    staff_can_manage_classroom,
    staff_classroom_or_none,
    staff_member_required,
)


def _parse_class_id(request) -> int:
    try:
        return int((request.GET.get("class_id") or "0").strip())
    except ValueError:
        return 0


def _lesson_override_target_id(*, classroom_id: int, course_slug: str, lesson_slug: str) -> str:
    return f"{classroom_id}:{course_slug}/{lesson_slug}"[:64]


def _audit_lesson_override_mutation(
    request,
    *,
    classroom,
    course_slug: str,
    lesson_slug: str,
    action: str,
    summary: str,
    has_override: bool,
):
    _audit(
        request,
        action=action,
        classroom=classroom,
        target_type="ClassLessonOverride",
        target_id=_lesson_override_target_id(
            classroom_id=classroom.id,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
        ),
        summary=summary,
        metadata={
            "classroom_id": classroom.id,
            "course_slug": course_slug,
            "lesson_slug": lesson_slug,
            "has_override": has_override,
        },
    )


def _editable_classroom_or_redirect(request, *, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom or not staff_can_manage_classroom(request.user, classroom):
        return None, redirect("/teach/lessons")
    return classroom, None


def _load_editable_lesson(course_slug: str, lesson_slug: str):
    manifest = load_course_manifest(course_slug)
    lessons = manifest.get("lessons") or []
    match = next((l for l in lessons if isinstance(l, dict) and l.get("slug") == lesson_slug), None)
    if not match:
        return None

    rel = str(match.get("file") or "").strip()
    lesson_path = _safe_course_file_path(course_slug, rel)
    if not lesson_path or not lesson_path.exists():
        return None

    master_raw = lesson_path.read_text(encoding="utf-8")
    fm, _, _ = load_lesson_markdown(course_slug, lesson_slug)
    return {
        "front_matter": fm,
        "master_raw": master_raw,
    }


def _lesson_override_redirect(*, class_id: int, course_slug: str, lesson_slug: str):
    path = f"/course/{course_slug}/{lesson_slug}"
    return f"{path}?{urlencode({'class_id': str(class_id)})}"


def _upsert_lesson_override(
    request,
    *,
    classroom,
    course_slug: str,
    lesson_slug: str,
    override,
):
    new_markdown = request.POST.get("raw_markdown", "")
    if override:
        override.raw_markdown = new_markdown
        override.updated_by = request.user
        override.save()
        _audit_lesson_override_mutation(
            request,
            classroom=classroom,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            action="lesson_override.update",
            summary="Updated class-local lesson override",
            has_override=True,
        )
        return

    ClassLessonOverride.objects.create(
        classroom=classroom,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        raw_markdown=new_markdown,
        updated_by=request.user,
    )
    _audit_lesson_override_mutation(
        request,
        classroom=classroom,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        action="lesson_override.create",
        summary="Created class-local lesson override",
        has_override=True,
    )


def _handle_override_post(
    request,
    *,
    classroom,
    class_id: int,
    course_slug: str,
    lesson_slug: str,
    override,
):
    if not staff_can_manage_classroom(request.user, classroom):
        return _safe_internal_redirect(
            request,
            _lesson_override_redirect(class_id=class_id, course_slug=course_slug, lesson_slug=lesson_slug),
            fallback="/teach/lessons",
        )

    if request.POST.get("action") == "reset":
        if override:
            override.delete()
            _audit_lesson_override_mutation(
                request,
                classroom=classroom,
                course_slug=course_slug,
                lesson_slug=lesson_slug,
                action="lesson_override.reset",
                summary="Reset lesson override to repository default",
                has_override=False,
            )
        return _safe_internal_redirect(
            request,
            _lesson_override_redirect(class_id=class_id, course_slug=course_slug, lesson_slug=lesson_slug),
            fallback="/teach/lessons",
        )

    _upsert_lesson_override(
        request,
        classroom=classroom,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        override=override,
    )
    return _safe_internal_redirect(
        request,
        _lesson_override_redirect(class_id=class_id, course_slug=course_slug, lesson_slug=lesson_slug),
        fallback="/teach/lessons",
    )


@staff_member_required
def teach_edit_override_lesson(request, course_slug: str, lesson_slug: str):
    """Postgres-backed override editor for Teacher Freedom compliance."""
    class_id = _parse_class_id(request)
    classroom, redirect_response = _editable_classroom_or_redirect(request, class_id=class_id)
    if redirect_response:
        return redirect_response
    if not staff_can_manage_classroom(request.user, classroom):
        return redirect("/teach/lessons")

    lesson_data = _load_editable_lesson(course_slug, lesson_slug)
    if lesson_data is None:
        return redirect("/teach/lessons")

    override = ClassLessonOverride.objects.filter(
        classroom_id=classroom.id,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
    ).first()
    current_raw = override.raw_markdown if override else lesson_data["master_raw"]

    if request.method == "POST":
        return _handle_override_post(
            request,
            classroom=classroom,
            class_id=class_id,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            override=override,
        )

    return render(
        request,
        "teacher/teach_lesson_edit.html",
        {
            "class_id": class_id,
            "classroom": classroom,
            "course_slug": course_slug,
            "lesson_slug": lesson_slug,
            "lesson_title": lesson_data["front_matter"].get("title") or lesson_slug,
            "current_raw": current_raw,
            "has_override": bool(override),
        },
    )


__all__ = [
    "teach_edit_override_lesson",
]
