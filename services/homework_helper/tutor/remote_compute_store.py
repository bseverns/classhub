"""Durable store for remote helper lease state and accounting metrics."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError

from .models import RemoteComputeClassMetric, RemoteComputeLeaseRecord

logger = logging.getLogger(__name__)

_LEASE_CACHE_KEY = "helper:remote_compute:lease"
_METRICS_CACHE_KEY_PREFIX = "helper:remote_compute:metrics:"
_LEASE_SLOT = "active"
_METRICS_TIMEOUT_SECONDS = 45 * 24 * 60 * 60


def load_state() -> dict:
    cached = cache.get(_LEASE_CACHE_KEY) or {}
    if isinstance(cached, dict) and cached:
        return dict(cached)
    try:
        record = RemoteComputeLeaseRecord.objects.filter(slot=_LEASE_SLOT).first()
    except (OperationalError, ProgrammingError) as exc:
        _log_storage_warning(op="load_state", exc=exc)
        return {}
    payload = _state_payload_from_record(record)
    if payload:
        cache.set(_LEASE_CACHE_KEY, payload, timeout=_payload_timeout_seconds(payload))
    return payload


def persist_state(payload: dict, *, timeout_seconds: int) -> None:
    if not payload:
        delete_state()
        return
    normalized = _normalized_state_payload(payload)
    cache.set(_LEASE_CACHE_KEY, normalized, timeout=max(int(timeout_seconds), 60))
    try:
        RemoteComputeLeaseRecord.objects.update_or_create(
            slot=_LEASE_SLOT,
            defaults={
                "state": str(normalized.get("state") or "off")[:32],
                "class_id": _safe_int(normalized.get("class_id")),
                "requested_by": str(normalized.get("requested_by") or "").strip()[:150],
                "requested_at": _parse_iso_datetime(str(normalized.get("requested_at") or "").strip()),
                "expires_at": _parse_iso_datetime(str(normalized.get("expires_at") or "").strip()),
                "requested_duration_minutes": _safe_int(normalized.get("requested_duration_minutes")),
                "provider_request_id": str(normalized.get("provider_request_id") or "").strip()[:120],
                "lease_session_id": _safe_int(normalized.get("lease_session_id")),
                "status_detail": str(normalized.get("status_detail") or "").strip()[:160],
                "last_error_code": str(normalized.get("last_error_code") or "").strip()[:80],
                "last_readiness_reason_code": str(normalized.get("last_readiness_reason_code") or "").strip()[:80],
                "last_transition_at": _parse_iso_datetime(str(normalized.get("last_transition_at") or "").strip()),
                "last_healthcheck_at": _parse_iso_datetime(str(normalized.get("last_healthcheck_at") or "").strip()),
                "last_ready_probe_at": _parse_iso_datetime(str(normalized.get("last_ready_probe_at") or "").strip()),
                "last_ready_probe_ok_at": _parse_iso_datetime(str(normalized.get("last_ready_probe_ok_at") or "").strip()),
                "last_routed_at": _parse_iso_datetime(str(normalized.get("last_routed_at") or "").strip()),
            },
        )
    except (OperationalError, ProgrammingError) as exc:
        _log_storage_warning(op="persist_state", exc=exc)


def delete_state() -> None:
    cache.delete(_LEASE_CACHE_KEY)
    try:
        RemoteComputeLeaseRecord.objects.filter(slot=_LEASE_SLOT).delete()
    except (OperationalError, ProgrammingError) as exc:
        _log_storage_warning(op="delete_state", exc=exc)


def load_metrics(class_id: int) -> dict:
    class_id = _safe_int(class_id)
    if class_id <= 0:
        return {}
    cached = cache.get(_metrics_cache_key(class_id)) or {}
    if isinstance(cached, dict) and cached:
        return dict(cached)
    try:
        record = RemoteComputeClassMetric.objects.filter(class_id=class_id).first()
    except (OperationalError, ProgrammingError) as exc:
        _log_storage_warning(op="load_metrics", exc=exc)
        return {}
    payload = _metrics_payload_from_record(record)
    if payload:
        cache.set(_metrics_cache_key(class_id), payload, timeout=_METRICS_TIMEOUT_SECONDS)
    return payload


def persist_metrics(class_id: int, payload: dict) -> None:
    class_id = _safe_int(class_id)
    if class_id <= 0:
        return
    normalized = _normalized_metrics_payload(payload)
    cache.set(_metrics_cache_key(class_id), normalized, timeout=_METRICS_TIMEOUT_SECONDS)
    try:
        RemoteComputeClassMetric.objects.update_or_create(
            class_id=class_id,
            defaults={
                "activation_count": _safe_int(normalized.get("activation_count")),
                "ready_transition_count": _safe_int(normalized.get("ready_transition_count")),
                "cumulative_ready_seconds": _safe_int(normalized.get("cumulative_ready_seconds")),
                "remote_route_count": _safe_int(normalized.get("remote_route_count")),
                "fallback_local_count": _safe_int(normalized.get("fallback_local_count")),
                "degraded_transition_count": _safe_int(normalized.get("degraded_transition_count")),
                "provider_unreachable_count": _safe_int(normalized.get("provider_unreachable_count")),
                "unused_activation_count": _safe_int(normalized.get("unused_activation_count")),
                "last_activation_at": _parse_iso_datetime(str(normalized.get("last_activation_at") or "").strip()),
                "last_ready_at": _parse_iso_datetime(str(normalized.get("last_ready_at") or "").strip()),
                "last_fallback_at": _parse_iso_datetime(str(normalized.get("last_fallback_at") or "").strip()),
            },
        )
    except (OperationalError, ProgrammingError) as exc:
        _log_storage_warning(op="persist_metrics", exc=exc)


def _metrics_cache_key(class_id: int) -> str:
    return f"{_METRICS_CACHE_KEY_PREFIX}{int(class_id)}"


def _payload_timeout_seconds(payload: dict) -> int:
    expires_at = _parse_iso_datetime(str(payload.get("expires_at") or "").strip())
    if expires_at is None:
        return 300
    return max(int((expires_at - _utc_now()).total_seconds()), 60)


def _state_payload_from_record(record: RemoteComputeLeaseRecord | None) -> dict:
    if record is None:
        return {}
    return {
        "state": str(record.state or "off").strip()[:32],
        "class_id": int(record.class_id or 0),
        "requested_by": str(record.requested_by or "").strip()[:150],
        "requested_at": _iso_or_empty(record.requested_at),
        "expires_at": _iso_or_empty(record.expires_at),
        "requested_duration_minutes": int(record.requested_duration_minutes or 0),
        "provider_request_id": str(record.provider_request_id or "").strip()[:120],
        "lease_session_id": int(record.lease_session_id or 0),
        "status_detail": str(record.status_detail or "").strip()[:160],
        "last_error_code": str(record.last_error_code or "").strip()[:80],
        "last_readiness_reason_code": str(record.last_readiness_reason_code or "").strip()[:80],
        "last_transition_at": _iso_or_empty(record.last_transition_at),
        "last_healthcheck_at": _iso_or_empty(record.last_healthcheck_at),
        "last_ready_probe_at": _iso_or_empty(record.last_ready_probe_at),
        "last_ready_probe_ok_at": _iso_or_empty(record.last_ready_probe_ok_at),
        "last_routed_at": _iso_or_empty(record.last_routed_at),
    }


def _metrics_payload_from_record(record: RemoteComputeClassMetric | None) -> dict:
    if record is None:
        return {}
    return {
        "activation_count": int(record.activation_count or 0),
        "ready_transition_count": int(record.ready_transition_count or 0),
        "cumulative_ready_seconds": int(record.cumulative_ready_seconds or 0),
        "remote_route_count": int(record.remote_route_count or 0),
        "fallback_local_count": int(record.fallback_local_count or 0),
        "degraded_transition_count": int(record.degraded_transition_count or 0),
        "provider_unreachable_count": int(record.provider_unreachable_count or 0),
        "unused_activation_count": int(record.unused_activation_count or 0),
        "last_activation_at": _iso_or_empty(record.last_activation_at),
        "last_ready_at": _iso_or_empty(record.last_ready_at),
        "last_fallback_at": _iso_or_empty(record.last_fallback_at),
    }


def _normalized_state_payload(payload: dict) -> dict:
    return {
        "state": str(payload.get("state") or "off").strip()[:32],
        "class_id": _safe_int(payload.get("class_id")),
        "requested_by": str(payload.get("requested_by") or "").strip()[:150],
        "requested_at": str(payload.get("requested_at") or "").strip()[:64],
        "expires_at": str(payload.get("expires_at") or "").strip()[:64],
        "requested_duration_minutes": _safe_int(payload.get("requested_duration_minutes")),
        "provider_request_id": str(payload.get("provider_request_id") or "").strip()[:120],
        "lease_session_id": _safe_int(payload.get("lease_session_id")),
        "status_detail": str(payload.get("status_detail") or "").strip()[:160],
        "last_error_code": str(payload.get("last_error_code") or "").strip()[:80],
        "last_readiness_reason_code": str(payload.get("last_readiness_reason_code") or "").strip()[:80],
        "last_transition_at": str(payload.get("last_transition_at") or "").strip()[:64],
        "last_healthcheck_at": str(payload.get("last_healthcheck_at") or "").strip()[:64],
        "last_ready_probe_at": str(payload.get("last_ready_probe_at") or "").strip()[:64],
        "last_ready_probe_ok_at": str(payload.get("last_ready_probe_ok_at") or "").strip()[:64],
        "last_routed_at": str(payload.get("last_routed_at") or "").strip()[:64],
    }


def _normalized_metrics_payload(payload: dict) -> dict:
    return {
        "activation_count": _safe_int(payload.get("activation_count")),
        "ready_transition_count": _safe_int(payload.get("ready_transition_count")),
        "cumulative_ready_seconds": _safe_int(payload.get("cumulative_ready_seconds")),
        "remote_route_count": _safe_int(payload.get("remote_route_count")),
        "fallback_local_count": _safe_int(payload.get("fallback_local_count")),
        "degraded_transition_count": _safe_int(payload.get("degraded_transition_count")),
        "provider_unreachable_count": _safe_int(payload.get("provider_unreachable_count")),
        "unused_activation_count": _safe_int(payload.get("unused_activation_count")),
        "last_activation_at": str(payload.get("last_activation_at") or "").strip()[:64],
        "last_ready_at": str(payload.get("last_ready_at") or "").strip()[:64],
        "last_fallback_at": str(payload.get("last_fallback_at") or "").strip()[:64],
    }


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


def _iso_or_empty(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _log_storage_warning(*, op: str, exc: Exception) -> None:
    logger.warning(
        "remote_compute_store_db_warning op=%s error=%s",
        op,
        exc.__class__.__name__,
    )
