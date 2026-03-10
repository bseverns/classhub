"""Student upload API endpoints for queue/flush workflows."""

import logging
from functools import wraps

from django.conf import settings
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from common.request_safety import client_ip_from_request, fixed_window_allow
from ..forms import SubmissionUploadForm
from ..http.headers import apply_no_store
from ..models import Class, Material, StudentIdentity
from ..services.ip_privacy import minimize_student_event_ip
from ..services.telemetry_events import write_student_event
from ..services.submission_service import (
    parse_extensions,
    process_material_upload_form,
    resolve_upload_release_state,
    scan_uploaded_file,
    validate_upload_content,
)

logger = logging.getLogger(__name__)


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _api_rate_limit(limit: int = 120, window_seconds: int = 60):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if getattr(request, "student", None) is None:
                return view_func(request, *args, **kwargs)
            client_ip = client_ip_from_request(
                request,
                trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
                xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
            )
            key = f"api_rate:student:{request.student.id}:ip:{client_ip}"
            if not fixed_window_allow(key, limit=limit, window_seconds=window_seconds):
                return _json_no_store_response({"error": "rate_limited"}, status=429, private=True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def _emit_student_event(
    *,
    event_type: str,
    classroom: Class | None,
    student: StudentIdentity | None,
    source: str,
    details: dict,
    ip_address: str = "",
) -> None:
    try:
        write_student_event(
            event_type=event_type,
            source=source,
            details=details or {},
            classroom=classroom,
            student=student,
            ip_address=(minimize_student_event_ip(ip_address) or None),
            write_source="api_student_upload",
        )
    except Exception:
        logger.exception("student_event_write_failed type=%s", event_type)


def _first_form_error(form) -> str:
    first_error = ""
    for values in form.errors.values():
        if values:
            first_error = str(values[0]).strip()
            break
    return first_error or "Please check your upload form and try again."


def _student_session_missing(request) -> bool:
    return getattr(request, "student", None) is None or getattr(request, "classroom", None) is None


def _student_upload_material(request, material_id: int) -> Material | None:
    material = (
        Material.objects.select_related("module__classroom")
        .filter(id=material_id)
        .first()
    )
    if not material or material.module.classroom_id != request.classroom.id:
        return None
    return material


def _upload_locked_response(request, *, material: Material):
    release_state = resolve_upload_release_state(request, material=material)
    if not release_state.get("is_locked"):
        return None
    available_on = release_state.get("available_on")
    message = (
        f"Submissions for this lesson open on {available_on.isoformat()}."
        if available_on
        else "Submissions for this lesson are not open yet."
    )
    return _json_no_store_response(
        {"error": "upload_locked", "message": message},
        status=403,
        private=True,
    )


def _share_with_class_requested(request, *, material: Material) -> bool:
    if material.type != Material.TYPE_GALLERY:
        return False
    return str(request.POST.get("share_with_class", "")).strip().lower() in {"1", "true", "yes", "on"}


def _upload_result_response(*, material: Material, upload_result):
    if upload_result.redirect_url:
        return _json_no_store_response(
            {
                "ok": True,
                "material_id": material.id,
                "redirect_url": upload_result.redirect_url,
            },
            private=True,
        )
    return _json_no_store_response(
        {"error": "upload_failed", "message": upload_result.error or "Upload failed."},
        status=upload_result.response_status or 400,
        private=True,
    )


def _upload_internal_error_response() -> JsonResponse:
    return _json_no_store_response(
        {
            "error": "upload_internal_error",
            "message": "Upload temporarily unavailable. Please ask your teacher to retry.",
            "retry": False,
        },
        status=500,
        private=True,
    )


@require_GET
@_api_rate_limit(limit=120, window_seconds=60)
def api_student_csrf(request):
    """GET /api/v1/student/csrf."""
    if _student_session_missing(request):
        return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)
    return _json_no_store_response({"csrf_token": get_token(request)}, private=True)


@require_POST
@_api_rate_limit(limit=60, window_seconds=60)
def api_student_material_upload(request, material_id: int):
    """POST /api/v1/student/material/<id>/upload."""
    if _student_session_missing(request):
        return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)

    try:
        material = _student_upload_material(request, material_id)
        if material is None:
            return _json_no_store_response({"error": "not_found"}, status=404, private=True)
        if material.type not in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
            return _json_no_store_response({"error": "not_upload_material"}, status=404, private=True)

        locked_response = _upload_locked_response(request, material=material)
        if locked_response is not None:
            return locked_response

        form = SubmissionUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return _json_no_store_response(
                {"error": "invalid_form", "message": _first_form_error(form)},
                status=400,
                private=True,
            )

        allowed_exts = parse_extensions(material.accepted_extensions) or [".sb3"]
        max_bytes = int(material.max_upload_mb) * 1024 * 1024
        share_with_class = _share_with_class_requested(request, material=material)
        upload_result = process_material_upload_form(
            request=request,
            material=material,
            form=form,
            allowed_exts=allowed_exts,
            max_bytes=max_bytes,
            validate_upload_content_fn=validate_upload_content,
            scan_uploaded_file_fn=scan_uploaded_file,
            emit_student_event_fn=_emit_student_event,
            logger=logger,
            share_with_class=share_with_class,
        )
        return _upload_result_response(material=material, upload_result=upload_result)
    except Exception:
        logger.exception(
            "api_student_upload_internal_error material_id=%s student_id=%s",
            material_id,
            getattr(getattr(request, "student", None), "id", "unknown"),
        )
        return _upload_internal_error_response()


__all__ = ["api_student_csrf", "api_student_material_upload"]
