"""Teacher class helper snapshot export endpoints."""

from __future__ import annotations

import csv
from io import StringIO

from django.conf import settings
from django.http import JsonResponse

from ...services.filenames import safe_filename
from ...services.helper_control import fetch_remote_compute_status
from .shared import (
    HttpResponse,
    _audit,
    apply_download_safety,
    apply_no_store,
    safe_attachment_filename,
    staff_can_manage_policy,
    staff_classroom_or_none,
    staff_member_required,
    timezone,
)


def _remote_helper_snapshot_filename(*, classroom, extension: str) -> str:
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    return safe_attachment_filename(
        f"{safe_filename(classroom.name)}_remote_helper_snapshot_{stamp}.{extension}"
    )


def _remote_helper_snapshot_payload(*, classroom) -> dict:
    result = fetch_remote_compute_status(
        class_id=classroom.id,
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL", "") or "").strip(),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
    )
    return {
        "ok": bool(result.ok),
        "class_id": int(classroom.id),
        "class_name": str(classroom.name or ""),
        "state": str(result.state or "off"),
        "feature_enabled": bool(result.feature_enabled),
        "paid_usage_acknowledged": bool(result.paid_usage_acknowledged),
        "backend_configured": bool(result.backend_configured),
        "active": bool(result.active),
        "active_for_class": bool(result.active_for_class),
        "use_remote_backend": bool(result.use_remote_backend),
        "requested_by": str(result.requested_by or ""),
        "requested_at": str(result.requested_at or ""),
        "expires_at": str(result.expires_at or ""),
        "remaining_minutes": int(result.remaining_minutes or 0),
        "provider_label": str(result.provider_label or ""),
        "provider_request_id": str(result.provider_request_id or ""),
        "provider_adapter": str(result.provider_adapter or ""),
        "control_url_configured": bool(result.control_url_configured),
        "healthcheck_url_configured": bool(result.healthcheck_url_configured),
        "auto_stop_on_idle": bool(result.auto_stop_on_idle),
        "idle_timeout_seconds": int(result.idle_timeout_seconds or 0),
        "status_detail": str(result.status_detail or ""),
        "last_error_code": str(result.last_error_code or ""),
        "last_transition_at": str(result.last_transition_at or ""),
        "last_healthcheck_at": str(result.last_healthcheck_at or ""),
        "last_routed_at": str(result.last_routed_at or ""),
        "activation_count": int(result.activation_count or 0),
        "ready_transition_count": int(result.ready_transition_count or 0),
        "avg_ready_seconds": int(result.avg_ready_seconds or 0),
        "remote_route_count": int(result.remote_route_count or 0),
        "fallback_local_count": int(result.fallback_local_count or 0),
        "degraded_transition_count": int(result.degraded_transition_count or 0),
        "provider_unreachable_count": int(result.provider_unreachable_count or 0),
        "unused_activation_count": int(result.unused_activation_count or 0),
        "last_activation_at": str(result.last_activation_at or ""),
        "last_ready_at": str(result.last_ready_at or ""),
        "last_fallback_at": str(result.last_fallback_at or ""),
        "request_id": str(result.request_id or ""),
        "error_code": str(result.error_code or ""),
        "status_code": int(result.status_code or 0),
        "exported_at": timezone.now().isoformat(),
    }


def _remote_helper_snapshot_csv(payload: dict) -> str:
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["field", "value"])
    for key, value in payload.items():
        writer.writerow([key, value])
    return out.getvalue()


@staff_member_required
def teach_export_class_remote_helper_snapshot(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    export_format = (request.GET.get("format") or "json").strip().lower()
    if export_format not in {"json", "csv"}:
        return HttpResponse("Invalid export format.", status=400)

    payload = _remote_helper_snapshot_payload(classroom=classroom)
    filename = _remote_helper_snapshot_filename(classroom=classroom, extension=export_format)

    if export_format == "json":
        response = JsonResponse(payload)
    else:
        response = HttpResponse(
            _remote_helper_snapshot_csv(payload),
            content_type="text/csv; charset=utf-8",
        )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    _audit(
        request,
        action="class.remote_helper_snapshot_export",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Exported remote helper snapshot for {classroom.name}",
        metadata={
            "format": export_format,
            "filename": filename,
            "helper_request_id": payload.get("request_id"),
            "state": payload.get("state"),
            "ok": payload.get("ok"),
        },
    )
    return response


__all__ = ["teach_export_class_remote_helper_snapshot"]
