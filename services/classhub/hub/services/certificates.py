"""Certificate issuance helpers."""

from __future__ import annotations

from django.core import signing
from django.utils import timezone

_CERTIFICATE_SIGNING_SALT = "classhub.certificate.v1"


def build_certificate_payload(*, issuance) -> dict:
    issued_at = issuance.issued_at or timezone.now()
    return {
        "certificate_id": int(issuance.id or 0),
        "code": issuance.code,
        "class_id": int(issuance.classroom_id or 0),
        "class_name": issuance.classroom.name,
        "student_id": int(issuance.student_id or 0),
        "display_name": issuance.student.display_name,
        "issued_by": (issuance.issued_by.username if issuance.issued_by else ""),
        "issued_at": issued_at.isoformat(),
        "session_count": int(issuance.session_count or 0),
        "artifact_count": int(issuance.artifact_count or 0),
        "milestone_count": int(issuance.milestone_count or 0),
        "min_sessions_required": int(issuance.min_sessions_required or 1),
        "min_artifacts_required": int(issuance.min_artifacts_required or 1),
    }


def sign_certificate_payload(*, issuance) -> str:
    payload = build_certificate_payload(issuance=issuance)
    return signing.dumps(payload, salt=_CERTIFICATE_SIGNING_SALT)


def certificate_download_text(*, issuance) -> str:
    payload = build_certificate_payload(issuance=issuance)
    token = (issuance.signed_token or "").strip() or sign_certificate_payload(issuance=issuance)
    lines = [
        "Class Hub Certificate Record",
        "",
        f"Certificate code: {payload['code']}",
        f"Student: {payload['display_name']}",
        f"Class: {payload['class_name']}",
        f"Issued at: {payload['issued_at']}",
        f"Issued by: {payload['issued_by'] or '(system)'}",
        "",
        "Eligibility snapshot:",
        f"- Sessions completed: {payload['session_count']} (required {payload['min_sessions_required']})",
        f"- Artifact submissions: {payload['artifact_count']} (required {payload['min_artifacts_required']})",
        f"- Milestones: {payload['milestone_count']}",
        "",
        "Signed token:",
        token,
        "",
        "This file is a signed Class Hub certificate record.",
    ]
    return "\n".join(lines) + "\n"


__all__ = ["build_certificate_payload", "certificate_download_text", "sign_certificate_payload"]
