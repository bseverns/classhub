"""Teacher outcomes/certificate endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import CertificateIssuance, Module, StudentIdentity, StudentOutcomeEvent
from ...services.teacher_roster_class import build_certificate_eligibility_rows
from .shared_auth import staff_can_manage_classroom, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice
from .shared import render


def _parse_positive_id(raw) -> int:
    try:
        value = int((raw or "").strip())
    except Exception:
        value = 0
    return value if value > 0 else 0


@staff_member_required
def teach_certificate_eligibility(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    can_manage = staff_can_manage_classroom(request.user, classroom)

    students = list(classroom.students.only("id", "display_name").order_by("display_name", "id"))
    modules = list(classroom.modules.only("id", "title", "order_index").order_by("order_index", "id"))
    summary = build_certificate_eligibility_rows(classroom=classroom, students=students)
    issuance_rows = list(
        CertificateIssuance.objects.filter(classroom=classroom)
        .only("id", "student_id", "issued_at", "code")
        .order_by("-issued_at", "-id")
    )
    issuance_by_student: dict[int, CertificateIssuance] = {}
    for issuance in issuance_rows:
        if issuance.student_id not in issuance_by_student:
            issuance_by_student[int(issuance.student_id)] = issuance
    for row in summary.get("rows", []):
        issuance = issuance_by_student.get(int(row.get("student_id") or 0))
        row["certificate_issued"] = bool(issuance)
        row["certificate_code"] = issuance.code if issuance else ""
        row["certificate_issued_at"] = issuance.issued_at if issuance else None

    response = render(
        request,
        "teach_certificate_eligibility.html",
        {
            "classroom": classroom,
            "modules": modules,
            "eligibility_rows": summary["rows"],
            "eligible_students": summary["eligible_students"],
            "total_students": summary["total_students"],
            "certificate_min_sessions": summary["certificate_min_sessions"],
            "certificate_min_artifacts": summary["certificate_min_artifacts"],
            "can_manage": can_manage,
            "notice": (request.GET.get("notice") or "").strip(),
            "error": (request.GET.get("error") or "").strip(),
        },
    )
    return response


@staff_member_required
@require_POST
def teach_mark_session_completed(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_positive_id(request.POST.get("student_id"))
    module_id = _parse_positive_id(request.POST.get("module_id"))
    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    module = Module.objects.filter(id=module_id, classroom=classroom).first()
    if not student or not module:
        return _safe_internal_redirect(
            request,
            _with_notice(f"{_teach_class_path(classroom.id)}/certificate-eligibility", error="Select a student and module."),
            fallback=_teach_class_path(classroom.id),
        )

    event_exists = StudentOutcomeEvent.objects.filter(
        classroom=classroom,
        student=student,
        module=module,
        event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
    ).exists()
    if event_exists:
        notice = "Session completion already recorded for that student and module."
    else:
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            module=module,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            source="classhub.teacher_mark_session_completed",
            details={"trigger": "teacher_marked", "module_id": module.id},
        )
        _audit(
            request,
            action="class.mark_session_completed",
            classroom=classroom,
            target_type="StudentOutcomeEvent",
            target_id=f"{student.id}:{module.id}",
            summary=f"Marked session completed for {student.display_name}",
            metadata={"student_id": student.id, "module_id": module.id},
        )
        notice = f"Marked session completed for {student.display_name}."

    path = f"{_teach_class_path(classroom.id)}/certificate-eligibility"
    return _safe_internal_redirect(
        request,
        _with_notice(path, notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = ["teach_certificate_eligibility", "teach_mark_session_completed"]
