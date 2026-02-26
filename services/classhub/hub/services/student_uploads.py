"""Student upload service helpers."""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from common.request_safety import client_ip_from_request

from ..models import Material, StudentEvent, StudentOutcomeEvent, Submission
from .content_links import parse_course_lesson_url
from .markdown_content import load_lesson_markdown
from .release_state import lesson_release_state


@dataclass(frozen=True)
class UploadAttemptResult:
    error: str = ""
    response_status: int = 200
    redirect_url: str = ""


def resolve_upload_release_state(request, *, material: Material) -> dict:
    release_state = {"is_locked": False, "available_on": None}
    module_mats = list(material.module.materials.all())
    module_mats.sort(key=lambda m: (m.order_index, m.id))
    for candidate in module_mats:
        if candidate.type != Material.TYPE_LINK:
            continue
        parsed = parse_course_lesson_url(candidate.url)
        if not parsed:
            continue
        try:
            front_matter, _body, lesson_meta = load_lesson_markdown(parsed[0], parsed[1])
        except ValueError:
            front_matter = {}
            lesson_meta = {}
        release_state = lesson_release_state(
            request,
            front_matter,
            lesson_meta,
            classroom_id=material.module.classroom_id,
            course_slug=parsed[0],
            lesson_slug=parsed[1],
        )
        break
    return release_state


def process_material_upload_form(
    *,
    request,
    material: Material,
    form,
    allowed_exts: list[str],
    max_bytes: int,
    validate_upload_content_fn,
    scan_uploaded_file_fn,
    emit_student_event_fn,
    logger,
) -> UploadAttemptResult:
    uploaded_file = form.cleaned_data["file"]
    note = (form.cleaned_data.get("note") or "").strip()
    name = (getattr(uploaded_file, "name", "") or "upload").strip()
    lower = name.lower()
    ext = "." + lower.rsplit(".", 1)[-1] if "." in lower else ""

    if ext not in allowed_exts:
        return UploadAttemptResult(error=f"File type not allowed. Allowed: {', '.join(allowed_exts)}")
    if getattr(uploaded_file, "size", 0) and uploaded_file.size > max_bytes:
        return UploadAttemptResult(error=f"File too large. Max size: {material.max_upload_mb}MB")

    content_error = validate_upload_content_fn(uploaded_file, ext)
    if content_error:
        logger.info(
            "upload_rejected_content_mismatch material_id=%s student_id=%s ext=%s",
            material.id,
            request.student.id,
            ext,
        )
        return UploadAttemptResult(error=content_error, response_status=400)

    scan_result = scan_uploaded_file_fn(uploaded_file)
    fail_closed = bool(getattr(settings, "CLASSHUB_UPLOAD_SCAN_FAIL_CLOSED", False))
    if scan_result.status == "infected":
        logger.warning(
            "upload_blocked_malware material_id=%s student_id=%s message=%s",
            material.id,
            request.student.id,
            scan_result.message,
        )
        return UploadAttemptResult(
            error="Upload blocked by malware scan. Ask your teacher for help.",
            response_status=400,
        )
    if scan_result.status == "error" and fail_closed:
        logger.warning(
            "upload_blocked_scan_error material_id=%s student_id=%s message=%s",
            material.id,
            request.student.id,
            scan_result.message,
        )
        return UploadAttemptResult(
            error="Upload scanner unavailable right now. Please try again shortly.",
            response_status=503,
        )

    submission = Submission.objects.create(
        material=material,
        student=request.student,
        original_filename=name,
        file=uploaded_file,
        note=note,
    )
    emit_student_event_fn(
        event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
        classroom=request.classroom,
        student=request.student,
        source="classhub.material_upload",
        details={
            "material_id": material.id,
            "submission_id": submission.id,
            "file_ext": (Path(name).suffix or "").lower()[:16],
            "size_bytes": int(getattr(uploaded_file, "size", 0) or 0),
            "scan_status": scan_result.status,
        },
        ip_address=client_ip_from_request(
            request,
            trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
            xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
        ),
    )
    try:
        StudentOutcomeEvent.objects.create(
            classroom=request.classroom,
            student=request.student,
            module=material.module,
            material=material,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="classhub.material_upload",
            details={
                "material_id": material.id,
                "module_id": material.module_id,
                "submission_id": submission.id,
            },
        )
        if not StudentOutcomeEvent.objects.filter(
            classroom=request.classroom,
            student=request.student,
            module=material.module,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
        ).exists():
            StudentOutcomeEvent.objects.create(
                classroom=request.classroom,
                student=request.student,
                module=material.module,
                material=material,
                event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
                source="classhub.material_upload",
                details={
                    "module_id": material.module_id,
                    "trigger": "artifact_submitted",
                },
            )
    except Exception:
        logger.exception("student_outcome_event_write_failed material_id=%s student_id=%s", material.id, request.student.id)
    return UploadAttemptResult(redirect_url=f"/material/{material.id}/upload")
