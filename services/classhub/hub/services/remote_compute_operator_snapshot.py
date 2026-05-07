"""Helper-backed operator snapshot shaping for remote compute evidence."""

from __future__ import annotations

from ..models import Class
from .helper_control import (
    HelperRemoteComputeEvidenceResult,
    HelperRemoteComputeStatusResult,
    fetch_remote_compute_operator_snapshot,
)
from .remote_compute_signals import build_remote_compute_signal_summary


def build_remote_compute_operator_snapshot(
    *,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
) -> dict:
    result = fetch_remote_compute_operator_snapshot(
        endpoint_url=endpoint_url,
        internal_token=internal_token,
        timeout_seconds=timeout_seconds,
    )
    if result.ok:
        return _snapshot_payload(result=result)
    if result.error_code in {"helper_endpoint_not_configured", "helper_token_not_configured"}:
        return {"status": "not_configured", "error_code": str(result.error_code)}
    return {"status": "error", "error_code": str(result.error_code or "helper_status_failed")}


def _snapshot_payload(*, result) -> dict:
    active_lease = dict(result.active_lease or {})
    recent_classes = list(result.recent_classes or [])
    class_name_map = _class_name_map(recent_classes=recent_classes, active_lease=active_lease)
    active_class_id = int(active_lease.get("class_id") or 0)
    summary = dict(result.summary or {})
    return {
        "status": "ok",
        "active_lease": {
            **active_lease,
            "class_id": active_class_id,
            "class_name": str(class_name_map.get(active_class_id, "")),
        },
        "summary": summary,
        "aggregate_signal": _signal_summary(
            row=summary,
            active_lease=active_lease,
        ),
        "recent_classes": _recent_class_rows(
            recent_classes=recent_classes,
            class_name_map=class_name_map,
        ),
    }


def _recent_class_rows(*, recent_classes: list[dict], class_name_map: dict[int, str]) -> list[dict]:
    rows: list[dict] = []
    for row in recent_classes:
        class_id = int(row.get("class_id") or 0)
        rows.append(
            {
                **row,
                "class_id": class_id,
                "class_name": str(class_name_map.get(class_id, "")),
                "signal": _signal_summary(row=row),
            }
        )
    return rows


def _class_name_map(*, recent_classes: list[dict], active_lease: dict) -> dict[int, str]:
    class_ids = {
        int(row.get("class_id") or 0)
        for row in recent_classes
        if int(row.get("class_id") or 0) > 0
    }
    active_class_id = int(active_lease.get("class_id") or 0)
    if active_class_id > 0:
        class_ids.add(active_class_id)
    return dict(Class.objects.filter(id__in=class_ids).values_list("id", "name"))


def _signal_summary(*, row: dict, active_lease: dict | None = None) -> dict:
    return build_remote_compute_signal_summary(
        status_result=_status_from_row(row=row, active_lease=active_lease),
        evidence_result=HelperRemoteComputeEvidenceResult(ok=True),
    )


def _status_from_row(*, row: dict, active_lease: dict | None = None) -> HelperRemoteComputeStatusResult:
    lease = active_lease or {}
    return HelperRemoteComputeStatusResult(
        ok=True,
        active=bool(lease.get("active")),
        active_for_class=bool(lease.get("active_for_class")),
        use_remote_backend=bool(lease.get("use_remote_backend")),
        state=str(lease.get("state") or "off").strip()[:32],
        class_id=int(row.get("class_id") or lease.get("class_id") or 0),
        requested_by=str(lease.get("requested_by") or "").strip()[:150],
        expires_at=str(lease.get("expires_at") or "").strip()[:64],
        remaining_minutes=int(lease.get("remaining_minutes") or 0),
        status_detail=str(lease.get("status_detail") or "").strip()[:160],
        last_error_code=str(lease.get("last_error_code") or "").strip()[:80],
        activation_count=int(row.get("activation_count") or 0),
        ready_transition_count=int(row.get("ready_transition_count") or 0),
        avg_ready_seconds=int(row.get("avg_ready_seconds") or 0),
        remote_route_count=int(row.get("remote_route_count") or 0),
        fallback_local_count=int(row.get("fallback_local_count") or 0),
        degraded_transition_count=int(row.get("degraded_transition_count") or 0),
        provider_unreachable_count=int(row.get("provider_unreachable_count") or 0),
        unused_activation_count=int(row.get("unused_activation_count") or 0),
        last_activation_at=str(row.get("last_activation_at") or "").strip()[:64],
        last_ready_at=str(row.get("last_ready_at") or "").strip()[:64],
        last_fallback_at=str(row.get("last_fallback_at") or "").strip()[:64],
        leased_minutes_total=int(row.get("leased_minutes_total") or 0),
        approximate_cost_usd_total=str(row.get("approximate_cost_usd_total") or "").strip()[:32],
    )


__all__ = ["build_remote_compute_operator_snapshot"]
