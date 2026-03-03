"""Teacher facilitator-support actions for class dashboards."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import StudentEvent, StudentIdentity
from .shared_auth import staff_can_manage_classroom, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


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


__all__ = [
    "teach_resolve_stuck_flag",
]
