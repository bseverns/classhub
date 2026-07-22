"""Teacher class remote-helper-compute control endpoint."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse

from ...services.helper_control import (
    HelperRemoteComputeEvidenceResult,
    HelperRemoteComputeStatusResult,
    fetch_remote_compute_evidence,
    fetch_remote_compute_status,
    set_remote_compute_state,
)
from ...services.remote_compute_signals import build_remote_compute_signal_summary
from .shared_auth import staff_classroom_or_none
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def remote_compute_status_context(*, can_manage_remote_compute: bool, classroom) -> dict:
    if can_manage_remote_compute:
        status_result = fetch_remote_compute_status(
            class_id=classroom.id,
            endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL", "") or "").strip(),
            internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
            timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        )
        evidence_result = fetch_remote_compute_evidence(
            class_id=classroom.id,
            endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_EVIDENCE_URL", "") or "").strip(),
            internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
            timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        )
    else:
        status_result = HelperRemoteComputeStatusResult(ok=False, error_code="not_visible")
        evidence_result = HelperRemoteComputeEvidenceResult(ok=False, error_code="not_visible")
    return {
        "helper_remote_compute": status_result,
        "helper_remote_compute_evidence": evidence_result,
        "helper_remote_compute_cost_risk": _remote_compute_cost_risk(
            status_result=status_result,
            evidence_result=evidence_result,
        ),
        "helper_remote_compute_signal_summary": build_remote_compute_signal_summary(
            status_result=status_result,
            evidence_result=evidence_result,
        ),
        "helper_remote_compute_duration_choices": [30, 60, 90, 120],
    }


def teach_set_remote_helper_compute_impl(*, request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403)

    action = (request.POST.get("action") or "").strip().lower()
    result = set_remote_compute_state(
        class_id=classroom.id,
        action=action,
        requested_by=str(getattr(request.user, "username", "") or "").strip(),
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_CONTROL_URL", "") or "").strip(),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        duration_minutes=_duration_minutes_from_request(request),
        stop_reason=_stop_reason_from_request(request=request, action=action),
    )
    if not result.ok:
        return _remote_compute_failed_redirect(
            request=request,
            classroom=classroom,
            action=action,
            result=result,
        )

    _audit(
        request,
        action=f"class.remote_helper_compute_{result.action}",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Remote helper compute {result.action} for {classroom.name}",
        metadata={
            "active": result.active,
            "active_for_class": result.active_for_class,
            "use_remote_backend": result.use_remote_backend,
            "state": result.state,
            "expires_at": result.expires_at,
            "remaining_minutes": result.remaining_minutes,
            "provider_request_id": result.provider_request_id,
            "helper_request_id": result.request_id,
            "stop_reason": _stop_reason_from_request(request=request, action=action),
            "status_detail": result.status_detail,
            "detail": result.detail,
            "status_code": result.status_code,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=_remote_compute_success_notice(result=result)),
        fallback=_teach_class_path(classroom.id),
    )


def _duration_minutes_from_request(request) -> int:
    try:
        return int(request.POST.get("duration_minutes") or 0)
    except Exception:
        return 0


def _stop_reason_from_request(*, request, action: str) -> str:
    if action != "deactivate":
        return ""
    return str(request.POST.get("stop_reason") or "manual_stop").strip()[:80]


def _remote_compute_failed_redirect(*, request, classroom, action: str, result):
    _audit(
        request,
        action="class.remote_helper_compute_failed",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Failed remote helper compute {action or 'update'} for {classroom.name}",
        metadata={
            "action_requested": action,
            "error_code": result.error_code,
            "helper_request_id": result.request_id,
            "stop_reason": _stop_reason_from_request(request=request, action=action),
            "status_code": result.status_code,
            "remaining_minutes": result.remaining_minutes,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            _teach_class_path(classroom.id),
            error=f"Could not update remote helper compute ({result.error_code}).",
        ),
        fallback=_teach_class_path(classroom.id),
    )


def _remote_compute_success_notice(*, result) -> str:
    if result.action != "activate":
        if result.state == "off":
            return "Remote helper compute is off. Local/default helper mode remains the baseline."
        return "Remote helper compute is stopping. Local/default helper mode remains the baseline."
    if result.state == "ready":
        return f"Remote helper compute is ready for about {result.remaining_minutes} minute(s)."
    return f"Remote helper compute requested. Current state: {result.state or 'requested'}."


def _remote_compute_cost_risk(*, status_result, evidence_result) -> dict:
    if not bool(getattr(status_result, "ok", False)):
        return {
            "level": "unavailable",
            "summary": "Staff evidence unavailable",
            "detail": "The helper evidence path did not return a usable remote-compute status snapshot.",
        }
    if not bool(getattr(status_result, "active", False)):
        return {
            "level": "low",
            "summary": "No active lease",
            "detail": "Remote helper compute is off, so there is no current leased-cost exposure.",
        }
    if str(getattr(status_result, "state", "") or "").strip() == "degraded":
        return {
            "level": "degraded_active",
            "summary": "Lease active while degraded",
            "detail": "The lease is still active but helper traffic is falling back locally; stop it if the class no longer needs remote capacity.",
        }
    if int(getattr(status_result, "remaining_minutes", 0) or 0) <= 10:
        return {
            "level": "expiring",
            "summary": "Lease nearing expiry",
            "detail": "The remote window is close to ending; extend it only if the class is actively using the remote path right now.",
        }
    remote_routes = int(getattr(status_result, "remote_route_count", 0) or 0)
    if bool(getattr(evidence_result, "ok", False)):
        recent_sessions = list(getattr(evidence_result, "recent_sessions", []) or [])
        if recent_sessions:
            remote_routes = int(recent_sessions[0].get("remote_route_count") or remote_routes)
    if remote_routes <= 0:
        return {
            "level": "unused_active",
            "summary": "Lease active but unused",
            "detail": "The current lease is running but the helper has not recorded remote-routed chats yet.",
        }
    return {
        "level": "bounded",
        "summary": "Bounded active lease",
        "detail": "Remote helper compute is active within a class-scoped window and has recorded live remote usage.",
    }


__all__ = ["remote_compute_status_context", "teach_set_remote_helper_compute_impl"]
