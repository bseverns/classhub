"""Remote helper compute accounting counters."""

from __future__ import annotations

from datetime import datetime, timezone

from .remote_compute_store import load_metrics, persist_metrics


def load_metric_payload(class_id: int) -> dict:
    return load_metrics(class_id)


def record_activation(*, class_id: int, requested_at: str) -> None:
    metrics = load_metric_payload(class_id)
    metrics["activation_count"] = _safe_int(metrics.get("activation_count")) + 1
    metrics["last_activation_at"] = str(requested_at or "").strip()[:64]
    _persist_metrics(class_id, metrics)


def record_ready_transition(*, class_id: int, requested_at: str) -> None:
    metrics = load_metric_payload(class_id)
    metrics["ready_transition_count"] = _safe_int(metrics.get("ready_transition_count")) + 1
    metrics["last_ready_at"] = _utc_now().isoformat()
    requested_at_dt = _parse_iso_datetime(str(requested_at or "").strip())
    if requested_at_dt is not None:
        elapsed_seconds = max(int((_utc_now() - requested_at_dt).total_seconds()), 0)
        metrics["cumulative_ready_seconds"] = _safe_int(metrics.get("cumulative_ready_seconds")) + elapsed_seconds
    _persist_metrics(class_id, metrics)


def record_remote_route(*, class_id: int) -> None:
    metrics = load_metric_payload(class_id)
    metrics["remote_route_count"] = _safe_int(metrics.get("remote_route_count")) + 1
    _persist_metrics(class_id, metrics)


def record_fallback_local(*, class_id: int) -> None:
    metrics = load_metric_payload(class_id)
    metrics["fallback_local_count"] = _safe_int(metrics.get("fallback_local_count")) + 1
    metrics["last_fallback_at"] = _utc_now().isoformat()
    _persist_metrics(class_id, metrics)


def record_degraded_transition(*, class_id: int, error_code: str) -> None:
    metrics = load_metric_payload(class_id)
    metrics["degraded_transition_count"] = _safe_int(metrics.get("degraded_transition_count")) + 1
    _persist_metrics(class_id, metrics)


def record_provider_unreachable_if_needed(*, class_id: int, error_code: str) -> None:
    if not _looks_unreachable_error(error_code):
        return
    metrics = load_metric_payload(class_id)
    metrics["provider_unreachable_count"] = _safe_int(metrics.get("provider_unreachable_count")) + 1
    _persist_metrics(class_id, metrics)


def finalize_unused_activation_from_payload(payload: dict) -> None:
    class_id = _safe_int(payload.get("class_id"))
    if class_id <= 0:
        return
    requested_at = str(payload.get("requested_at") or "").strip()
    if not requested_at:
        return
    if str(payload.get("last_routed_at") or "").strip():
        return
    metrics = load_metric_payload(class_id)
    metrics["unused_activation_count"] = _safe_int(metrics.get("unused_activation_count")) + 1
    _persist_metrics(class_id, metrics)


def _persist_metrics(class_id: int, payload: dict) -> None:
    persist_metrics(class_id, payload)


def _parse_iso_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _looks_unreachable_error(error_code: str) -> bool:
    return "unreachable" in str(error_code or "").strip().lower()


__all__ = [
    "finalize_unused_activation_from_payload",
    "load_metric_payload",
    "record_activation",
    "record_degraded_transition",
    "record_fallback_local",
    "record_provider_unreachable_if_needed",
    "record_ready_transition",
    "record_remote_route",
]
