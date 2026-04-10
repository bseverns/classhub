"""Internal helper endpoint for bounded remote compute control/status."""

from __future__ import annotations

import hmac
import json

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .engine import runtime as engine_runtime
from .internal_audit import log_internal_audit_event
from .remote_compute_control import (
    activate_remote_compute,
    current_remote_compute_lease,
    deactivate_remote_compute,
    remote_compute_duration_minutes,
)


def _request_id(request) -> str:
    return engine_runtime.request_id(request)


def _json_response(payload: dict, *, request_id: str, status: int = 200):
    return engine_runtime.json_response(payload, request_id_value=request_id, status=status)


def _extract_bearer_token(request) -> str:
    header = (request.META.get("HTTP_AUTHORIZATION", "") or "").strip()
    if not header.lower().startswith("bearer "):
        return ""
    return header[7:].strip()


def _internal_api_token() -> str:
    return str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip()


def _authorized(request, *, request_id: str, event_prefix: str):
    configured_token = _internal_api_token()
    if not configured_token:
        log_internal_audit_event(
            "error",
            f"{event_prefix}_token_not_configured",
            request=request,
            request_id=request_id,
        )
        return False, _json_response({"error": "internal_token_not_configured"}, request_id=request_id, status=503)
    provided_token = _extract_bearer_token(request)
    if not provided_token or not hmac.compare_digest(configured_token, provided_token):
        log_internal_audit_event(
            "warning",
            f"{event_prefix}_unauthorized",
            request=request,
            request_id=request_id,
        )
        return False, _json_response({"error": "unauthorized"}, request_id=request_id, status=401)
    return True, None


@csrf_exempt
@require_GET
def internal_remote_compute_status(request):
    request_id = _request_id(request)
    ok, response = _authorized(request, request_id=request_id, event_prefix="internal_remote_compute_status")
    if not ok:
        return response
    try:
        class_id = int(request.GET.get("class_id") or 0)
    except Exception:
        class_id = 0
    lease = current_remote_compute_lease(class_id=class_id, refresh=True)
    log_internal_audit_event(
        "info",
        "internal_remote_compute_status_read",
        request=request,
        request_id=request_id,
        class_id=lease.class_id,
        state=lease.state,
        active=lease.active,
        active_for_class=lease.active_for_class,
        use_remote_backend=lease.use_remote_backend,
    )
    return _json_response(
        {
            "ok": True,
            "feature_enabled": lease.feature_enabled,
            "paid_usage_acknowledged": lease.paid_usage_acknowledged,
            "backend_configured": lease.backend_configured,
            "active": lease.active,
            "active_for_class": lease.active_for_class,
            "use_remote_backend": lease.use_remote_backend,
            "state": lease.state,
            "class_id": lease.class_id,
            "requested_by": lease.requested_by,
            "requested_at": lease.requested_at,
            "expires_at": lease.expires_at,
            "remaining_minutes": lease.remaining_minutes,
            "provider_label": lease.provider_label,
            "provider_request_id": lease.provider_request_id,
            "provider_adapter": lease.provider_adapter,
            "control_url_configured": lease.control_url_configured,
            "healthcheck_url_configured": lease.healthcheck_url_configured,
            "auto_stop_on_idle": lease.auto_stop_on_idle,
            "idle_timeout_seconds": lease.idle_timeout_seconds,
            "last_error_code": lease.last_error_code,
            "status_detail": lease.status_detail,
            "last_transition_at": lease.last_transition_at,
            "last_healthcheck_at": lease.last_healthcheck_at,
            "last_routed_at": lease.last_routed_at,
        },
        request_id=request_id,
    )


@csrf_exempt
@require_POST
def internal_remote_compute_control(request):
    request_id = _request_id(request)
    ok, response = _authorized(request, request_id=request_id, event_prefix="internal_remote_compute_control")
    if not ok:
        return response
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_bad_json",
            request=request,
            request_id=request_id,
        )
        return _json_response({"error": "bad_json"}, request_id=request_id, status=400)
    if not isinstance(payload, dict):
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_bad_json",
            request=request,
            request_id=request_id,
        )
        return _json_response({"error": "bad_json"}, request_id=request_id, status=400)

    action = str(payload.get("action") or "").strip().lower()
    try:
        class_id = int(payload.get("class_id") or 0)
    except Exception:
        class_id = 0
    requested_by = str(payload.get("requested_by") or "").strip()
    if class_id <= 0:
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_invalid_class_id",
            request=request,
            request_id=request_id,
            action=action,
        )
        return _json_response({"error": "invalid_class_id"}, request_id=request_id, status=400)
    if not requested_by:
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_missing_requested_by",
            request=request,
            request_id=request_id,
            action=action,
            class_id=class_id,
        )
        return _json_response({"error": "missing_requested_by"}, request_id=request_id, status=400)

    if action == "activate":
        result = activate_remote_compute(
            class_id=class_id,
            requested_by=requested_by,
            duration_minutes=remote_compute_duration_minutes(payload.get("duration_minutes")),
        )
    elif action == "deactivate":
        result = deactivate_remote_compute(class_id=class_id, requested_by=requested_by)
    else:
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_invalid_action",
            request=request,
            request_id=request_id,
            action=action,
            class_id=class_id,
            requested_by=requested_by,
        )
        return _json_response({"error": "invalid_action"}, request_id=request_id, status=400)

    if not result.ok:
        log_internal_audit_event(
            "warning",
            "internal_remote_compute_control_failed",
            request=request,
            request_id=request_id,
            action=action,
            class_id=class_id,
            requested_by=requested_by,
            error_code=result.error_code,
            state=result.lease.state,
            provider_request_id=result.provider_request_id,
        )
        return _json_response(
            {
                "error": result.error_code or "remote_compute_control_failed",
                "lease": {
                    "active": result.lease.active,
                    "active_for_class": result.lease.active_for_class,
                    "use_remote_backend": result.lease.use_remote_backend,
                    "state": result.lease.state,
                    "class_id": result.lease.class_id,
                    "expires_at": result.lease.expires_at,
                    "remaining_minutes": result.lease.remaining_minutes,
                },
            },
            request_id=request_id,
            status=503,
        )
    log_internal_audit_event(
        "info",
        "internal_remote_compute_control_completed",
        request=request,
        request_id=request_id,
        action=result.action,
        class_id=result.lease.class_id,
        requested_by=requested_by,
        state=result.lease.state,
        active=result.lease.active,
        use_remote_backend=result.lease.use_remote_backend,
        provider_request_id=result.provider_request_id,
    )
    return _json_response(
        {
            "ok": True,
            "action": result.action,
            "provider_request_id": result.provider_request_id,
            "detail": result.detail,
            "lease": {
                "active": result.lease.active,
                "active_for_class": result.lease.active_for_class,
                "use_remote_backend": result.lease.use_remote_backend,
                "state": result.lease.state,
                "class_id": result.lease.class_id,
                "requested_by": result.lease.requested_by,
                "requested_at": result.lease.requested_at,
                "expires_at": result.lease.expires_at,
                "remaining_minutes": result.lease.remaining_minutes,
            },
        },
        request_id=request_id,
    )


__all__ = ["internal_remote_compute_control", "internal_remote_compute_status"]
