"""Teacher facilitator-signal resolution endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import StudentEvent, StudentIdentity
from ...services.telemetry_events import write_student_event
from .shared_auth import staff_can_manage_roster, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def _parse_student_id(raw: str | None) -> int:
    try:
        return int((raw or "0").strip() or 0)
    except Exception:
        return 0


@staff_member_required
@require_POST
def teach_resolve_stuck_flag(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_student_id(request.POST.get("student_id"))
    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Could not resolve that support request."),
            fallback=_teach_class_path(classroom.id),
        )

    module_id = _parse_student_id(request.POST.get("module_id"))
    if module_id > 0 and not classroom.modules.filter(id=module_id).exists():
        module_id = 0

    details = {
        "signal": "stuck_resolved",
        "resolved_by_user_id": request.user.id,
    }
    if module_id > 0:
        details["module_id"] = module_id
    write_student_event(
        event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
        source="classhub.teach_class_dashboard",
        details=details,
        classroom=classroom,
        student=student,
        write_source="teach_resolve_stuck_flag",
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
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_student_id(request.POST.get("student_id"))
    student = StudentIdentity.objects.filter(classroom=classroom, id=student_id).only("id", "display_name").first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Could not resolve that deletion request."),
            fallback=_teach_class_path(classroom.id),
        )

    write_student_event(
        event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
        source="classhub.teach_class_dashboard",
        details={
            "signal": "delete_request_resolved",
            "resolved_by_user_id": request.user.id,
        },
        classroom=classroom,
        student=student,
        write_source="teach_resolve_delete_request",
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


__all__ = [
    "teach_resolve_delete_request",
    "teach_resolve_stuck_flag",
]
