"""Teacher certificate issuance endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store, safe_attachment_filename
from ...models import CertificateIssuance, StudentIdentity
from ...services.certificates import certificate_download_text, sign_certificate_payload
from ...services.filenames import safe_filename
from ...services.teacher_roster_class import build_certificate_eligibility_rows
from .shared_auth import (
    staff_can_access_classroom,
    staff_can_manage_classroom,
    staff_classroom_or_none,
    staff_member_required,
)
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def _certificate_page_path(classroom_id: int) -> str:
    return f"{_teach_class_path(classroom_id)}/certificate-eligibility"


def _parse_positive_id(raw) -> int:
    try:
        value = int((raw or "").strip())
    except Exception:
        value = 0
    return value if value > 0 else 0


def _eligible_student_row(*, classroom, student):
    summary = build_certificate_eligibility_rows(classroom=classroom, students=[student])
    rows = summary.get("rows") or []
    row = rows[0] if rows else None
    return summary, row


def _issue_or_reissue_certificate(*, request, classroom, student, summary: dict, row: dict):
    issuance, created = CertificateIssuance.objects.update_or_create(
        classroom=classroom,
        student=student,
        defaults={
            "issued_by": request.user if request.user.is_authenticated else None,
            "session_count": int(row.get("session_count") or 0),
            "artifact_count": int(row.get("artifact_count") or 0),
            "milestone_count": int(row.get("milestone_count") or 0),
            "min_sessions_required": int(summary.get("certificate_min_sessions") or 1),
            "min_artifacts_required": int(summary.get("certificate_min_artifacts") or 1),
        },
    )
    issuance = (
        CertificateIssuance.objects.select_related("classroom", "student", "issued_by")
        .filter(id=issuance.id)
        .first()
    )
    issuance.signed_token = sign_certificate_payload(issuance=issuance)
    issuance.save(update_fields=["signed_token", "updated_at"])
    return issuance, created


@staff_member_required
@require_POST
def teach_issue_certificate(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    student_id = _parse_positive_id(request.POST.get("student_id"))
    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if not student:
        return _safe_internal_redirect(
            request,
            _with_notice(_certificate_page_path(classroom.id), error="Select a valid student."),
            fallback=_teach_class_path(classroom.id),
        )

    summary, row = _eligible_student_row(classroom=classroom, student=student)
    if not row or not bool(row.get("certificate_eligible")):
        return _safe_internal_redirect(
            request,
            _with_notice(_certificate_page_path(classroom.id), error=f"{student.display_name} is not certificate-eligible yet."),
            fallback=_teach_class_path(classroom.id),
        )

    issuance, created = _issue_or_reissue_certificate(
        request=request,
        classroom=classroom,
        student=student,
        summary=summary,
        row=row,
    )

    _audit(
        request,
        action="class.issue_certificate",
        classroom=classroom,
        target_type="CertificateIssuance",
        target_id=str(issuance.id),
        summary=f"Issued certificate for {student.display_name}",
        metadata={"student_id": student.id, "certificate_code": issuance.code, "created": created},
    )
    notice = (
        f"Certificate issued for {student.display_name}."
        if created
        else f"Certificate re-issued for {student.display_name}."
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_certificate_page_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
def teach_download_certificate(request, class_id: int, student_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_access_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    issuance = (
        CertificateIssuance.objects.select_related("classroom", "student", "issued_by")
        .filter(classroom=classroom, student_id=student_id)
        .first()
    )
    if issuance is None:
        return HttpResponse("Not found", status=404)

    body = certificate_download_text(issuance=issuance)
    filename = safe_attachment_filename(
        f"{safe_filename(classroom.name)}_{safe_filename(issuance.student.display_name)}_certificate_{issuance.code}.txt"
    )
    response = HttpResponse(body, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = ["teach_download_certificate", "teach_issue_certificate"]
