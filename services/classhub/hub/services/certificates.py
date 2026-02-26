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


def _pdf_escape(value: str) -> str:
    ascii_value = (value or "").encode("latin-1", "replace").decode("latin-1")
    return ascii_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(value: str, *, width: int = 92) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return [""]
    return [raw[idx : idx + width] for idx in range(0, len(raw), width)]


def _pdf_text_stream(lines: list[str]) -> bytes:
    stream_lines = ["BT", "/F1 12 Tf", "16 TL", "72 760 Td"]
    for line in lines:
        stream_lines.append(f"({_pdf_escape(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    return ("\n".join(stream_lines) + "\n").encode("latin-1", "replace")


def _pdf_document_from_stream(stream: bytes) -> bytes:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
    pdf.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def certificate_download_pdf_bytes(*, issuance) -> bytes:
    payload = build_certificate_payload(issuance=issuance)
    token = (issuance.signed_token or "").strip() or sign_certificate_payload(issuance=issuance)
    lines: list[str] = [
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
    ]
    lines.extend(_wrap_text(token))
    lines.extend(["", "This is a signed Class Hub certificate record."])
    return _pdf_document_from_stream(_pdf_text_stream(lines))


__all__ = [
    "build_certificate_payload",
    "certificate_download_pdf_bytes",
    "certificate_download_text",
    "sign_certificate_payload",
]
