"""Teacher class-local lesson override editor endpoints."""

from django.shortcuts import redirect

from hub.models import ClassLessonOverride
from hub.services.markdown_content import _safe_course_file_path, load_course_manifest, load_lesson_markdown

from .shared import _audit, render, staff_can_manage_classroom, staff_classroom_or_none, staff_member_required


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


@staff_member_required
def teach_edit_override_lesson(request, course_slug: str, lesson_slug: str):
    """Postgres-backed override editor for Teacher Freedom compliance."""
    try:
        class_id = int((request.GET.get("class_id") or "0").strip())
    except ValueError:
        class_id = 0

    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom or not staff_can_manage_classroom(request.user, classroom):
        return redirect("/teach/lessons")

    manifest = load_course_manifest(course_slug)
    lessons = manifest.get("lessons") or []
    match = next((l for l in lessons if isinstance(l, dict) and l.get("slug") == lesson_slug), None)
    if not match:
        return redirect("/teach/lessons")

    rel = str(match.get("file") or "").strip()
    lesson_path = _safe_course_file_path(course_slug, rel)
    if not lesson_path or not lesson_path.exists():
        return redirect("/teach/lessons")

    master_raw = lesson_path.read_text(encoding="utf-8")
    fm, _, _ = load_lesson_markdown(course_slug, lesson_slug)

    override = ClassLessonOverride.objects.filter(
        classroom_id=classroom.id,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
    ).first()
    current_raw = override.raw_markdown if override else master_raw

    if request.method == "POST":
        if not staff_can_manage_classroom(request.user, classroom):
            return redirect(f"/course/{course_slug}/{lesson_slug}?class_id={class_id}")

        action = request.POST.get("action")
        if action == "reset":
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
            return redirect(f"/course/{course_slug}/{lesson_slug}?class_id={class_id}")

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
        else:
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
        return redirect(f"/course/{course_slug}/{lesson_slug}?class_id={class_id}")

    return render(
        request,
        "teacher/teach_lesson_edit.html",
        {
            "class_id": class_id,
            "classroom": classroom,
            "course_slug": course_slug,
            "lesson_slug": lesson_slug,
            "lesson_title": fm.get("title") or lesson_slug,
            "current_raw": current_raw,
            "has_override": bool(override),
        },
    )


__all__ = [
    "teach_edit_override_lesson",
]
