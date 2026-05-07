"""Teacher class helper snapshot export endpoints."""

from __future__ import annotations

import csv
import json
from io import StringIO

from django.conf import settings
from django.http import JsonResponse

from ...services.filenames import safe_filename
from ...services.helper_control import fetch_remote_compute_evidence
from ...services.helper_control import fetch_remote_compute_status
from ...services.remote_compute_signals import build_remote_compute_signal_summary
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


def _remote_helper_fetch_context(*, classroom):
    timeout_seconds = float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0)
    internal_token = str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip()
    evidence_result = fetch_remote_compute_evidence(
        class_id=classroom.id,
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_EVIDENCE_URL", "") or "").strip(),
        internal_token=internal_token,
        timeout_seconds=timeout_seconds,
    )
    status_result = fetch_remote_compute_status(
        class_id=classroom.id,
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL", "") or "").strip(),
        internal_token=internal_token,
        timeout_seconds=timeout_seconds,
    )
    return evidence_result, build_remote_compute_signal_summary(status_result=status_result, evidence_result=evidence_result)


def _remote_helper_snapshot_base_payload(*, classroom, active_lease: dict, summary: dict) -> dict:
    return {
        "ok": False,
        "class_id": int(classroom.id),
        "class_name": str(classroom.name or ""),
        "state": str(active_lease.get("state") or "off"),
        "active": bool(active_lease.get("active")),
        "active_for_class": bool(active_lease.get("active_for_class")),
        "use_remote_backend": bool(active_lease.get("use_remote_backend")),
        "requested_by": str(active_lease.get("requested_by") or ""),
        "requested_at": str(active_lease.get("requested_at") or ""),
        "expires_at": str(active_lease.get("expires_at") or ""),
        "requested_duration_minutes": int(active_lease.get("requested_duration_minutes") or 0),
        "remaining_minutes": int(active_lease.get("remaining_minutes") or 0),
        "provider_label": str(active_lease.get("provider_label") or ""),
        "provider_request_id": str(active_lease.get("provider_request_id") or ""),
        "provider_adapter": str(active_lease.get("provider_adapter") or ""),
        "status_detail": str(active_lease.get("status_detail") or ""),
        "last_error_code": str(active_lease.get("last_error_code") or ""),
        "last_readiness_reason_code": str(active_lease.get("last_readiness_reason_code") or ""),
        "last_transition_at": str(active_lease.get("last_transition_at") or ""),
        "last_healthcheck_at": str(active_lease.get("last_healthcheck_at") or ""),
        "last_ready_probe_at": str(active_lease.get("last_ready_probe_at") or ""),
        "last_ready_probe_ok_at": str(active_lease.get("last_ready_probe_ok_at") or ""),
        "last_routed_at": str(active_lease.get("last_routed_at") or ""),
        "activation_count": int(summary.get("activation_count") or 0),
        "requested_duration_minutes_total": int(summary.get("requested_duration_minutes_total") or 0),
        "starting_seconds_total": int(summary.get("starting_seconds_total") or 0),
        "ready_seconds_total": int(summary.get("ready_seconds_total") or 0),
        "degraded_seconds_total": int(summary.get("degraded_seconds_total") or 0),
        "manual_stop_count_total": int(summary.get("manual_stop_count_total") or 0),
        "auto_stop_count_total": int(summary.get("auto_stop_count_total") or 0),
        "remote_route_count": int(summary.get("remote_route_count") or 0),
        "fallback_local_count": int(summary.get("fallback_local_count") or 0),
        "leased_minutes_total": int(summary.get("leased_minutes_total") or 0),
        "approximate_cost_usd_total": str(summary.get("approximate_cost_usd_total") or ""),
    }


def _remote_helper_snapshot_signal_payload(signal_summary: dict) -> dict:
    return {
        "signal_level": str(signal_summary.get("level") or ""),
        "signal_summary": str(signal_summary.get("summary") or ""),
        "signal_detail": str(signal_summary.get("detail") or ""),
        "remote_attempt_count": int(signal_summary.get("remote_attempt_count") or 0),
        "fallback_rate_pct": int(signal_summary.get("fallback_rate_pct") or 0),
        "unused_activation_rate_pct": int(signal_summary.get("unused_activation_rate_pct") or 0),
        "signal_alerts": list(signal_summary.get("alerts") or []),
    }


def _remote_helper_snapshot_payload(*, classroom) -> dict:
    result, signal_summary = _remote_helper_fetch_context(classroom=classroom)
    payload = _remote_helper_snapshot_base_payload(
        classroom=classroom,
        active_lease=result.active_lease or {},
        summary=result.summary or {},
    )
    payload.update(_remote_helper_snapshot_signal_payload(signal_summary))
    payload.update(
        {
            "ok": bool(result.ok),
            "recent_sessions": list(result.recent_sessions or []),
            "recent_events": list(result.recent_events or []),
            "request_id": str(result.request_id or ""),
            "error_code": str(result.error_code or ""),
            "status_code": int(result.status_code or 0),
            "exported_at": timezone.now().isoformat(),
        }
    )
    return payload


def _remote_helper_snapshot_csv(payload: dict) -> str:
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["field", "value"])
    for key, value in payload.items():
        if key in {"recent_sessions", "recent_events", "signal_alerts"}:
            writer.writerow([key, json.dumps(value, separators=(",", ":"), sort_keys=True)])
            continue
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
