"""Teacher class remote-helper-compute control endpoint."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse

from ...services.helper_control import set_remote_compute_state
from .shared_auth import staff_can_manage_policy, staff_classroom_or_none
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def teach_set_remote_helper_compute_impl(*, request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
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
        return "Remote helper compute is stopping or off. Local/default helper mode remains the baseline."
    if result.state == "ready":
        return f"Remote helper compute is ready for about {result.remaining_minutes} minute(s)."
    return f"Remote helper compute requested. Current state: {result.state or 'requested'}."


__all__ = ["teach_set_remote_helper_compute_impl"]
