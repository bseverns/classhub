"""Teacher student identity endpoints."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .shared import (
    HttpResponse,
    StudentIdentity,
    _audit,
    _safe_internal_redirect,
    _teach_class_path,
    _with_notice,
    apply_no_store,
    require_POST,
    staff_can_manage_roster,
    staff_classroom_or_none,
    staff_member_required,
)


def _parse_student_id(raw: str | None) -> int:
    try:
        return int((raw or "0").strip())
    except Exception:
        return 0


@staff_member_required
@require_GET
def teach_student_return_code(request, class_id: int, student_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if not student:
        return HttpResponse("Not found", status=404)

    response = JsonResponse({"return_code": student.return_code})
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_rename_student(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_student_id(request.POST.get("student_id"))
    new_name = (request.POST.get("display_name") or "").strip()[:80]
    if not student_id:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invalid student selection."),
            fallback=_teach_class_path(classroom.id),
        )
    if not new_name:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student name cannot be empty."),
            fallback=_teach_class_path(classroom.id),
        )

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student not found in this class."),
            fallback=_teach_class_path(classroom.id),
        )

    old_name = student.display_name
    if old_name == new_name:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), notice="No change applied to student name."),
            fallback=_teach_class_path(classroom.id),
        )

    student.display_name = new_name
    student.save(update_fields=["display_name"])
    _audit(
        request,
        action="student.rename",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Renamed student {old_name} -> {new_name}",
        metadata={"old_name": old_name, "new_name": new_name},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=f"Renamed student to {new_name}."),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = [
    "teach_student_return_code",
    "teach_rename_student",
]
