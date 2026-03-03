"""Teacher facilitator-support actions for class dashboards."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import StudentEvent, StudentIdentity, StudentSupportTag
from .shared_auth import staff_can_manage_classroom, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def _parse_support_tag(raw: str) -> str:
    value = (raw or "").strip().lower()
    allowed = {choice for choice, _label in StudentSupportTag.TAG_CHOICES}
    return value if value in allowed else ""


@staff_member_required
@require_POST
def teach_resolve_stuck_flag(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip() or 0)
    except Exception:
        student_id = 0
    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Could not resolve that support request."),
            fallback=_teach_class_path(classroom.id),
        )

    try:
        module_id = int((request.POST.get("module_id") or "0").strip() or 0)
    except Exception:
        module_id = 0
    if module_id > 0 and not classroom.modules.filter(id=module_id).exists():
        module_id = 0

    details = {
        "signal": "stuck_resolved",
        "resolved_by_user_id": request.user.id,
    }
    if module_id > 0:
        details["module_id"] = module_id
    StudentEvent.objects.create(
        classroom=classroom,
        student=student,
        event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
        source="classhub.teach_class_dashboard",
        details=details,
    )
    _audit(
        request,
        action="class.resolve_stuck_flag",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Marked stuck request resolved for {student.display_name}",
        metadata={
            "student_id": student.id,
            "module_id": module_id,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=f"Marked {student.display_name} as supported."),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_resolve_delete_request(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip() or 0)
    except Exception:
        student_id = 0
    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Could not resolve that deletion request."),
            fallback=_teach_class_path(classroom.id),
        )

    StudentEvent.objects.create(
        classroom=classroom,
        student=student,
        event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
        source="classhub.teach_class_dashboard",
        details={
            "signal": "delete_request_resolved",
            "resolved_by_user_id": request.user.id,
        },
    )
    _audit(
        request,
        action="class.resolve_delete_request",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Marked deletion request resolved for {student.display_name}",
        metadata={"student_id": student.id},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=f"Marked {student.display_name} deletion request resolved."),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_add_support_tag(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip() or 0)
    except Exception:
        student_id = 0
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
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip() or 0)
    except Exception:
        student_id = 0
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
    "teach_resolve_delete_request",
    "teach_resolve_stuck_flag",
]
