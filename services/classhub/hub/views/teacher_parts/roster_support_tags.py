"""Teacher facilitator support-tag endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import StudentIdentity, StudentSupportTag
from .shared_auth import staff_can_manage_roster, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def _parse_support_tag(raw: str) -> str:
    value = (raw or "").strip().lower()
    allowed = {choice for choice, _label in StudentSupportTag.TAG_CHOICES}
    return value if value in allowed else ""


def _parse_student_id(raw: str | None) -> int:
    try:
        return int((raw or "0").strip() or 0)
    except Exception:
        return 0


@staff_member_required
@require_POST
def teach_add_support_tag(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_student_id(request.POST.get("student_id"))
    tag_value = _parse_support_tag(request.POST.get("tag") or "")
    if student_id <= 0 or not tag_value:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Choose a student and support tag."),
            fallback=_teach_class_path(classroom.id),
        )

    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student not found in this class."),
            fallback=_teach_class_path(classroom.id),
        )

    tag_row, created = StudentSupportTag.objects.get_or_create(
        classroom=classroom,
        student=student,
        tag=tag_value,
        defaults={"created_by": request.user},
    )
    label = StudentSupportTag.label_for(tag_row.tag)
    _audit(
        request,
        action="student.support_tag_add",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Added support tag {label} for {student.display_name}",
        metadata={
            "student_id": student.id,
            "tag": tag_row.tag,
            "created": bool(created),
        },
    )
    notice = f"Added support tag: {label}."
    if not created:
        notice = f"Support tag already set: {label}."
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_remove_support_tag(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_student_id(request.POST.get("student_id"))
    tag_value = _parse_support_tag(request.POST.get("tag") or "")
    if student_id <= 0 or not tag_value:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Choose a student and support tag."),
            fallback=_teach_class_path(classroom.id),
        )

    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student not found in this class."),
            fallback=_teach_class_path(classroom.id),
        )

    deleted, _details = StudentSupportTag.objects.filter(
        classroom=classroom,
        student=student,
        tag=tag_value,
    ).delete()
    label = StudentSupportTag.label_for(tag_value)
    _audit(
        request,
        action="student.support_tag_remove",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Removed support tag {label} for {student.display_name}",
        metadata={
            "student_id": student.id,
            "tag": tag_value,
            "removed": int(deleted > 0),
        },
    )
    notice = f"Removed support tag: {label}."
    if deleted == 0:
        notice = f"Support tag was not set: {label}."
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = [
    "teach_add_support_tag",
    "teach_remove_support_tag",
]
