"""Bounded remote helper compute lifecycle and status helpers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .engine.config_source import helper_config_overrides, helper_explicit_env, helper_getenv
from .llm import (
    LLMAuthError,
    LLMConfigError,
    LLMMalformedResponseError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
    healthcheck_provider,
    resolve_backend_name,
)
from .remote_compute_evidence import (
    build_class_evidence,
    create_or_update_active_session,
    record_local_fallback as record_evidence_local_fallback,
    record_ready_probe,
    record_remote_route as record_evidence_remote_route,
    sync_session_from_payload,
)
from .remote_compute_provider import build_remote_compute_provider
from .remote_compute_store import delete_state, load_metrics, load_state, persist_metrics, persist_state

_DEFAULT_DURATION_MINUTES = 90
_MAX_DURATION_MINUTES = 240
_STATUS_REFRESH_MIN_SECONDS = 10
_ALLOWED_STATES = {"off", "requested", "starting", "ready", "degraded", "stopping", "error"}


@dataclass(frozen=True)
class RemoteComputeLease:
    feature_enabled: bool
    paid_usage_acknowledged: bool
    backend_configured: bool
    active: bool
    active_for_class: bool
    use_remote_backend: bool
    state: str = "off"
    class_id: int = 0
    requested_by: str = ""
    requested_at: str = ""
    expires_at: str = ""
    requested_duration_minutes: int = 0
    remaining_minutes: int = 0
    provider_label: str = ""
    provider_request_id: str = ""
    provider_adapter: str = ""
    control_url_configured: bool = False
    healthcheck_url_configured: bool = False
    auto_stop_on_idle: bool = False
    idle_timeout_seconds: int = 0
    last_error_code: str = ""
    last_readiness_reason_code: str = ""
    status_detail: str = ""
    last_transition_at: str = ""
    last_healthcheck_at: str = ""
    last_ready_probe_at: str = ""
    last_ready_probe_ok_at: str = ""
    last_routed_at: str = ""
    activation_count: int = 0
    ready_transition_count: int = 0
    avg_ready_seconds: int = 0
    remote_route_count: int = 0
    fallback_local_count: int = 0
    degraded_transition_count: int = 0
    provider_unreachable_count: int = 0
    unused_activation_count: int = 0
    last_activation_at: str = ""
    last_ready_at: str = ""
    last_fallback_at: str = ""


@dataclass(frozen=True)
class RemoteComputeActionResult:
    ok: bool
    action: str
    lease: RemoteComputeLease
    provider_request_id: str = ""
    detail: str = ""
    error_code: str = ""
    status_code: int = 0


def remote_compute_feature_enabled() -> bool:
    value = helper_explicit_env("HELPER_REMOTE_COMPUTE_ENABLED") or helper_getenv("HELPER_REMOTE_COMPUTE_ENABLED", "0")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def remote_compute_paid_usage_acknowledged() -> bool:
    value = helper_explicit_env("HELPER_REMOTE_MODE_ACKNOWLEDGED") or helper_getenv("HELPER_REMOTE_MODE_ACKNOWLEDGED", "0")
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def remote_compute_backend_configured() -> bool:
    required = ("REMOTE_LLM_BASE_URL", "REMOTE_LLM_API_KEY", "REMOTE_LLM_MODEL")
    return all(bool((helper_explicit_env(name) or "").strip()) for name in required)


def remote_compute_control_url_configured(action: str) -> bool:
    return bool((helper_explicit_env(f"HELPER_REMOTE_COMPUTE_{action.upper()}_URL") or "").strip())


def remote_compute_healthcheck_url_configured() -> bool:
    return bool((helper_explicit_env("HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL") or "").strip())


def remote_compute_provider_label() -> str:
    configured = (helper_explicit_env("HELPER_REMOTE_COMPUTE_PROVIDER_LABEL") or "").strip()
    if configured:
        return configured
    adapter = (helper_explicit_env("HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER") or "").strip()
    return adapter or "operator_webhook"


def remote_compute_provider_adapter() -> str:
    adapter = (helper_explicit_env("HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER") or "").strip()
    return adapter or "generic_webhook"


def remote_compute_duration_minutes(raw_value) -> int:
    try:
        minutes = int(raw_value or 0)
    except Exception:
        minutes = 0
    if minutes <= 0:
        minutes = _DEFAULT_DURATION_MINUTES
    return max(15, min(minutes, _MAX_DURATION_MINUTES))


def remote_compute_idle_timeout_seconds() -> int:
    return max(_safe_int(helper_explicit_env("HELPER_REMOTE_COMPUTE_IDLE_TIMEOUT_SECONDS") or "0"), 0)


def remote_compute_ready_probe_max_seconds() -> int:
    return max(_safe_int(helper_explicit_env("HELPER_REMOTE_COMPUTE_READY_MAX_SECONDS") or "12"), 1)


def remote_compute_llm_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}
    mapping = {
        "LLM_BASE_URL": "REMOTE_LLM_BASE_URL",
        "LLM_API_KEY": "REMOTE_LLM_API_KEY",
        "LLM_MODEL": "REMOTE_LLM_MODEL",
        "LLM_TIMEOUT_SECONDS": "REMOTE_LLM_TIMEOUT_SECONDS",
        "LLM_MAX_TOKENS": "REMOTE_LLM_MAX_TOKENS",
        "LLM_NUM_CTX": "REMOTE_LLM_NUM_CTX",
        "LLM_TEMPERATURE": "REMOTE_LLM_TEMPERATURE",
        "LLM_TOP_P": "REMOTE_LLM_TOP_P",
        "OLLAMA_BASE_URL": "REMOTE_LLM_BASE_URL",
        "OLLAMA_API_KEY": "REMOTE_LLM_API_KEY",
        "OLLAMA_MODEL": "REMOTE_LLM_MODEL",
        "OLLAMA_TIMEOUT_SECONDS": "REMOTE_LLM_TIMEOUT_SECONDS",
        "OLLAMA_NUM_PREDICT": "REMOTE_LLM_MAX_TOKENS",
        "OLLAMA_NUM_CTX": "REMOTE_LLM_NUM_CTX",
        "OLLAMA_TEMPERATURE": "REMOTE_LLM_TEMPERATURE",
        "OLLAMA_TOP_P": "REMOTE_LLM_TOP_P",
    }
    for target, source in mapping.items():
        value = (helper_explicit_env(source) or "").strip()
        if value:
            overrides[target] = value
    return overrides


def current_remote_compute_lease(*, class_id: int = 0, refresh: bool = False) -> RemoteComputeLease:
    payload = _load_cached_state()
    payload = _expire_elapsed_lease(payload)
    payload = _auto_stop_if_idle(payload)
    if refresh:
        payload = _refresh_state_from_provider(payload)
    return _lease_from_payload(payload, class_id=class_id)


def reconcile_remote_compute_state(*, refresh: bool = True) -> RemoteComputeLease:
    payload = _load_cached_state()
    active_class_id = _safe_int(payload.get("class_id"))
    return current_remote_compute_lease(class_id=active_class_id, refresh=refresh)


def active_remote_compute_overrides_for_class(*, class_id: int) -> dict[str, str]:
    lease = current_remote_compute_lease(class_id=class_id, refresh=True)
    if not (
        lease.feature_enabled
        and lease.paid_usage_acknowledged
        and lease.backend_configured
        and lease.active_for_class
        and lease.use_remote_backend
    ):
        return {}
    return remote_compute_llm_overrides()


def activate_remote_compute(
    *,
    class_id: int,
    requested_by: str,
    duration_minutes: int,
    control_request_id: str = "",
) -> RemoteComputeActionResult:
    duration = remote_compute_duration_minutes(duration_minutes)
    lease = current_remote_compute_lease(class_id=class_id)
    if not lease.feature_enabled:
        return RemoteComputeActionResult(ok=False, action="activate", lease=lease, error_code="remote_compute_disabled")
    if not lease.paid_usage_acknowledged:
        return RemoteComputeActionResult(
            ok=False,
            action="activate",
            lease=lease,
            error_code="remote_compute_usage_not_acknowledged",
        )
    if not lease.backend_configured:
        return RemoteComputeActionResult(ok=False, action="activate", lease=lease, error_code="remote_backend_not_configured")
    if not remote_compute_control_url_configured("activate"):
        return RemoteComputeActionResult(
            ok=False,
            action="activate",
            lease=lease,
            error_code="remote_compute_control_not_configured",
        )
    if lease.active and lease.class_id and lease.class_id != int(class_id):
        return RemoteComputeActionResult(
            ok=False,
            action="activate",
            lease=lease,
            error_code="remote_compute_busy_for_another_class",
        )
    if lease.active and lease.class_id == int(class_id):
        payload = _load_cached_state()
        if payload and _safe_int(payload.get("class_id")) == int(class_id):
            sync_session_from_payload(
                payload=payload,
                reason_code="already_active_same_class",
                event_type="activation_duplicate_ignored",
                detail=f"Duplicate activate request reused the existing {lease.state} lease.",
            )
        return RemoteComputeActionResult(
            ok=True,
            action="activate",
            lease=lease,
            provider_request_id=str(lease.provider_request_id or "")[:120],
            detail=f"Remote helper compute already has an active {lease.state} lease for this class.",
            status_code=200,
        )

    provider = build_remote_compute_provider()
    provider_result = provider.activate(
        class_id=class_id,
        requested_by=requested_by,
        duration_minutes=duration,
        control_request_id=_control_request_id(control_request_id),
    )
    if not provider_result.ok:
        _record_provider_unreachable_if_needed(class_id=class_id, error_code=provider_result.error_code)
        error_payload = {
            "state": "error",
            "class_id": int(class_id),
            "requested_by": str(requested_by or "").strip()[:150],
            "provider_request_id": provider_result.provider_request_id,
            "last_error_code": provider_result.error_code,
            "status_detail": provider_result.detail,
            "last_transition_at": _utc_now().isoformat(),
        }
        _persist_state(error_payload, timeout_seconds=max(duration * 60, 60))
        return RemoteComputeActionResult(
            ok=False,
            action="activate",
            lease=current_remote_compute_lease(class_id=class_id),
            error_code=str(provider_result.error_code),
            status_code=int(provider_result.status_code),
        )

    _finalize_unused_activation_from_payload(_load_cached_state())
    now = _utc_now()
    expires_at = now + timedelta(minutes=duration)
    state = _normalize_state(provider_result.state, default="ready")
    last_error_code = ""
    status_detail = str(provider_result.detail or "").strip()[:160]
    last_readiness_reason_code = ""
    last_ready_probe_at = ""
    last_ready_probe_ok_at = ""
    if state == "ready":
        probe_ok, probe_error_code, probe_detail = _remote_backend_ready_probe()
        last_ready_probe_at = _utc_now().isoformat()
        if probe_ok:
            last_ready_probe_ok_at = last_ready_probe_at
            status_detail = probe_detail
        else:
            state = "starting"
            last_error_code = probe_error_code
            last_readiness_reason_code = probe_error_code
            status_detail = probe_detail
    payload = {
        "state": state,
        "class_id": int(class_id),
        "requested_by": str(requested_by or "").strip()[:150],
        "requested_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "requested_duration_minutes": duration,
        "provider_request_id": provider_result.provider_request_id,
        "status_detail": status_detail,
        "last_error_code": last_error_code,
        "last_readiness_reason_code": last_readiness_reason_code,
        "last_transition_at": now.isoformat(),
        "last_healthcheck_at": "",
        "last_ready_probe_at": last_ready_probe_at,
        "last_ready_probe_ok_at": last_ready_probe_ok_at,
        "last_routed_at": "",
    }
    payload["lease_session_id"] = create_or_update_active_session(
        payload=payload,
        provider_label=remote_compute_provider_label(),
        provider_adapter=remote_compute_provider_adapter(),
    )
    _persist_state(payload, timeout_seconds=max(duration * 60, 60))
    if last_ready_probe_at:
        record_ready_probe(
            payload=payload,
            ok=bool(last_ready_probe_ok_at),
            reason_code=last_readiness_reason_code,
            detail=status_detail,
        )
    _record_activation(class_id=class_id, requested_at=payload["requested_at"])
    if state == "ready":
        _record_ready_transition(class_id=class_id, requested_at=payload["requested_at"])
    return RemoteComputeActionResult(
        ok=True,
        action="activate",
        lease=current_remote_compute_lease(class_id=class_id),
        provider_request_id=str(provider_result.provider_request_id or "")[:120],
        detail=str(provider_result.detail or "").strip()[:160],
        status_code=int(provider_result.status_code),
    )


def deactivate_remote_compute(
    *,
    class_id: int,
    requested_by: str,
    control_request_id: str = "",
    stop_reason: str = "",
) -> RemoteComputeActionResult:
    lease = current_remote_compute_lease(class_id=class_id)
    stop_reason = _normalize_stop_reason(stop_reason)
    if not lease.feature_enabled:
        return RemoteComputeActionResult(ok=False, action="deactivate", lease=lease, error_code="remote_compute_disabled")
    if not remote_compute_control_url_configured("deactivate"):
        return RemoteComputeActionResult(
            ok=False,
            action="deactivate",
            lease=lease,
            error_code="remote_compute_control_not_configured",
        )
    if lease.active and lease.class_id and lease.class_id != int(class_id):
        return RemoteComputeActionResult(
            ok=False,
            action="deactivate",
            lease=lease,
            error_code="remote_compute_busy_for_another_class",
        )
    if not lease.active or lease.state == "off":
        return RemoteComputeActionResult(
            ok=True,
            action="deactivate",
            lease=lease,
            detail="Remote helper compute is already off for this class.",
            status_code=200,
        )

    provider = build_remote_compute_provider()
    provider_result = provider.deactivate(
        class_id=class_id,
        requested_by=requested_by,
        control_request_id=_control_request_id(control_request_id),
        stop_reason=stop_reason,
    )
    if not provider_result.ok:
        _record_provider_unreachable_if_needed(class_id=class_id, error_code=provider_result.error_code)
        payload = _load_cached_state()
        if payload:
            payload["state"] = "error"
            payload["last_error_code"] = provider_result.error_code
            payload["status_detail"] = provider_result.detail or payload.get("status_detail") or ""
            payload["last_transition_at"] = _utc_now().isoformat()
            _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
        return RemoteComputeActionResult(
            ok=False,
            action="deactivate",
            lease=current_remote_compute_lease(class_id=class_id),
            error_code=str(provider_result.error_code),
            status_code=int(provider_result.status_code),
        )

    state = _normalize_state(provider_result.state, default="off")
    if state == "off":
        payload = _load_cached_state()
        if payload:
            payload["state"] = "off"
            payload["status_detail"] = str(provider_result.detail or "").strip()[:160]
            payload["last_transition_at"] = _utc_now().isoformat()
            sync_session_from_payload(
                payload=payload,
                reason_code=stop_reason,
                event_type=_stop_event_type(stop_reason),
                detail=payload["status_detail"],
                stop_mode=_stop_mode_for_reason(stop_reason),
            )
        _finalize_unused_activation_from_payload(payload)
        _delete_state()
    else:
        payload = _load_cached_state()
        payload.update(
            {
                "state": state,
                "status_detail": provider_result.detail,
                "last_transition_at": _utc_now().isoformat(),
                "last_error_code": "",
            }
        )
        _persist_state(payload, timeout_seconds=max(_state_timeout_seconds(payload), 300))
        sync_session_from_payload(
            payload=payload,
            reason_code=stop_reason,
            event_type="lease_stopping",
            detail=str(provider_result.detail or "").strip()[:160],
        )
    return RemoteComputeActionResult(
        ok=True,
        action="deactivate",
        lease=current_remote_compute_lease(class_id=class_id, refresh=True),
        provider_request_id=str(provider_result.provider_request_id or "")[:120],
        detail=str(provider_result.detail or "").strip()[:160],
        status_code=int(provider_result.status_code),
    )


def mark_remote_compute_degraded(*, class_id: int, error_code: str) -> None:
    payload = _load_cached_state()
    if not payload or _safe_int(payload.get("class_id")) != int(class_id):
        return
    prior_state = _normalize_state(payload.get("state"))
    payload["state"] = "degraded"
    payload["last_error_code"] = str(error_code or "").strip()[:80]
    payload["status_detail"] = "Remote helper compute fell back to local/default mode."
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
    sync_session_from_payload(
        payload=payload,
        reason_code=str(error_code or "").strip()[:80],
        event_type="lease_degraded",
        detail=payload["status_detail"],
    )
    if prior_state != "degraded":
        _record_degraded_transition(class_id=class_id, error_code=error_code)


def mark_remote_compute_fallback_local(*, class_id: int, error_code: str) -> None:
    payload = _load_cached_state()
    if payload and _safe_int(payload.get("class_id")) == int(class_id):
        record_evidence_local_fallback(
            payload=payload,
            reason_code=str(error_code or "").strip()[:80],
            detail="Remote helper compute fell back to local/default mode.",
        )
    _record_fallback_local(class_id=class_id)
    mark_remote_compute_degraded(class_id=class_id, error_code=error_code)


def mark_remote_compute_routed(*, class_id: int) -> None:
    payload = _load_cached_state()
    if not payload or _safe_int(payload.get("class_id")) != int(class_id):
        return
    if _normalize_state(payload.get("state")) != "ready":
        return
    payload["last_routed_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
    record_evidence_remote_route(payload=payload)
    _record_remote_route(class_id=class_id)


def _load_cached_state() -> dict:
    return load_state()


def _persist_state(payload: dict, *, timeout_seconds: int) -> None:
    persist_state(payload, timeout_seconds=timeout_seconds)


def _delete_state() -> None:
    delete_state()


def _expire_elapsed_lease(payload: dict) -> dict:
    if not payload:
        return {}
    expires_at = _parse_iso_datetime(str(payload.get("expires_at") or "").strip())
    if expires_at is None:
        return payload
    if expires_at > _utc_now():
        return payload
    provider = build_remote_compute_provider()
    result = provider.deactivate(
        class_id=_safe_int(payload.get("class_id")),
        requested_by="auto_expire_stop",
        control_request_id=_automatic_control_request_id(payload=payload, reason="lease_expired"),
        stop_reason="lease_expired",
    )
    if result.ok:
        payload["state"] = "off"
        payload["status_detail"] = "Lease expired; remote helper compute returned to off."
        payload["last_transition_at"] = _utc_now().isoformat()
        sync_session_from_payload(
            payload=payload,
            reason_code="lease_expired",
            event_type="lease_expired_auto_stop",
            detail=payload["status_detail"],
            stop_mode="auto",
        )
        _finalize_unused_activation_from_payload(payload)
        _delete_state()
        return {}
    _record_provider_unreachable_if_needed(class_id=_safe_int(payload.get("class_id")), error_code=result.error_code)
    payload["state"] = "error"
    payload["last_error_code"] = result.error_code or "remote_compute_expiry_stop_failed"
    payload["status_detail"] = "Lease expired, but remote helper compute did not confirm shutdown."
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=300)
    sync_session_from_payload(
        payload=payload,
        reason_code=str(payload["last_error_code"]),
        event_type="lease_expiry_stop_failed",
        detail=payload["status_detail"],
    )
    return payload


def _auto_stop_if_idle(payload: dict) -> dict:
    idle_timeout = remote_compute_idle_timeout_seconds()
    if not payload or idle_timeout <= 0:
        return payload
    state = _normalize_state(payload.get("state"))
    if state not in {"requested", "starting", "ready", "degraded"}:
        return payload
    last_routed_at = _parse_iso_datetime(str(payload.get("last_routed_at") or "").strip())
    if last_routed_at is None:
        return payload
    if (_utc_now() - last_routed_at).total_seconds() < idle_timeout:
        return payload
    provider = build_remote_compute_provider()
    result = provider.deactivate(
        class_id=_safe_int(payload.get("class_id")),
        requested_by="auto_idle_stop",
        control_request_id=_automatic_control_request_id(payload=payload, reason="idle_timeout"),
        stop_reason="idle_timeout",
    )
    if result.ok:
        payload["state"] = "off"
        payload["status_detail"] = "Idle auto-stop returned remote helper compute to off."
        payload["last_transition_at"] = _utc_now().isoformat()
        sync_session_from_payload(
            payload=payload,
            reason_code="idle_timeout",
            event_type="lease_idle_auto_stop",
            detail=payload["status_detail"],
            stop_mode="auto",
        )
        _finalize_unused_activation_from_payload(payload)
        _delete_state()
        return {}
    _record_provider_unreachable_if_needed(class_id=_safe_int(payload.get("class_id")), error_code=result.error_code)
    payload["state"] = "error"
    payload["last_error_code"] = result.error_code or "remote_compute_idle_stop_failed"
    payload["status_detail"] = "Idle auto-stop could not return remote helper compute to off."
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
    sync_session_from_payload(
        payload=payload,
        reason_code=str(payload["last_error_code"]),
        event_type="lease_idle_stop_failed",
        detail=payload["status_detail"],
    )
    return payload


def _refresh_state_from_provider(payload: dict) -> dict:
    if not payload:
        return {}
    state = _normalize_state(payload.get("state"))
    if state not in {"requested", "starting", "ready", "degraded", "stopping"}:
        return payload
    provider = build_remote_compute_provider()
    if not provider.supports_healthcheck():
        return payload
    last_healthcheck_at = _parse_iso_datetime(str(payload.get("last_healthcheck_at") or "").strip())
    if last_healthcheck_at is not None:
        min_interval = max(
            _safe_int(helper_explicit_env("HELPER_REMOTE_COMPUTE_HEALTHCHECK_MIN_INTERVAL_SECONDS") or _STATUS_REFRESH_MIN_SECONDS),
            1,
        )
        if (_utc_now() - last_healthcheck_at).total_seconds() < min_interval:
            return payload
    result = provider.healthcheck(
        class_id=_safe_int(payload.get("class_id")),
        provider_request_id=str(payload.get("provider_request_id") or "").strip()[:120],
        control_request_id=_automatic_control_request_id(payload=payload, reason="healthcheck"),
    )
    payload["last_healthcheck_at"] = _utc_now().isoformat()
    probe_detail = ""
    if not result.ok:
        _record_provider_unreachable_if_needed(class_id=_safe_int(payload.get("class_id")), error_code=result.error_code)
        if state in {"requested", "starting"}:
            payload["status_detail"] = payload.get("status_detail") or "Remote helper compute is still starting."
        else:
            payload["state"] = "degraded"
            payload["last_error_code"] = result.error_code or "remote_compute_healthcheck_failed"
            payload["status_detail"] = "Remote helper compute healthcheck failed; helper stays on local/default mode."
            payload["last_transition_at"] = _utc_now().isoformat()
            if state != "degraded":
                _record_degraded_transition(
                    class_id=_safe_int(payload.get("class_id")),
                    error_code=result.error_code or "remote_compute_healthcheck_failed",
                )
        _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
        sync_session_from_payload(
            payload=payload,
            reason_code=str(result.error_code or "remote_compute_healthcheck_failed"),
            event_type="provider_healthcheck_failed",
            detail=str(payload.get("status_detail") or "").strip()[:160],
        )
        return payload
    next_state = _normalize_state(result.state, default="ready")
    if next_state == "off":
        payload["state"] = "off"
        payload["status_detail"] = "Provider reported remote helper compute as off."
        payload["last_transition_at"] = _utc_now().isoformat()
        sync_session_from_payload(
            payload=payload,
            reason_code="provider_off_reconciled",
            event_type="provider_reconciled_off",
            detail=payload["status_detail"],
        )
        _finalize_unused_activation_from_payload(payload)
        _delete_state()
        return {}
    if next_state == "ready":
        probe_ok, probe_error_code, probe_detail = _remote_backend_ready_probe()
        payload["last_ready_probe_at"] = _utc_now().isoformat()
        payload["last_readiness_reason_code"] = str(probe_error_code or "").strip()[:80]
        if not probe_ok:
            record_ready_probe(
                payload=payload,
                ok=False,
                reason_code=probe_error_code,
                detail=probe_detail,
            )
            if state in {"requested", "starting"}:
                payload["state"] = "starting"
            else:
                payload["state"] = "degraded"
                if state != "degraded":
                    _record_degraded_transition(
                        class_id=_safe_int(payload.get("class_id")),
                        error_code=probe_error_code,
                    )
            payload["last_error_code"] = probe_error_code
            payload["status_detail"] = probe_detail
            payload["last_transition_at"] = _utc_now().isoformat()
            _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
            sync_session_from_payload(
                payload=payload,
                reason_code=probe_error_code,
                event_type="ready_probe_blocked",
                detail=probe_detail,
            )
            return payload
        payload["last_ready_probe_ok_at"] = payload["last_ready_probe_at"]
        payload["last_readiness_reason_code"] = ""
        record_ready_probe(
            payload=payload,
            ok=True,
            reason_code="",
            detail=probe_detail,
        )
    if state in {"requested", "starting"} and next_state == "ready":
        _record_ready_transition(
            class_id=_safe_int(payload.get("class_id")),
            requested_at=str(payload.get("requested_at") or "").strip(),
        )
    payload["state"] = next_state
    payload["provider_request_id"] = result.provider_request_id or str(payload.get("provider_request_id") or "")
    if next_state == "ready":
        payload["status_detail"] = probe_detail
    else:
        payload["status_detail"] = result.detail or str(payload.get("status_detail") or "")
    payload["last_error_code"] = ""
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
    sync_session_from_payload(
        payload=payload,
        reason_code="",
        event_type="provider_state_refresh",
        detail=str(payload.get("status_detail") or "").strip()[:160],
    )
    return payload


def _lease_from_payload(payload: dict, *, class_id: int) -> RemoteComputeLease:
    feature_enabled = remote_compute_feature_enabled()
    paid_usage_acknowledged = remote_compute_paid_usage_acknowledged()
    backend_configured = remote_compute_backend_configured()
    state = _normalize_state(payload.get("state"), default="off")
    active = bool(payload) and state != "off"
    active_class_id = _safe_int(payload.get("class_id"))
    active_for_class = bool(active and class_id > 0 and active_class_id == class_id)
    expires_at_raw = str(payload.get("expires_at") or "").strip()[:64]
    expires_at = _parse_iso_datetime(expires_at_raw)
    remaining_minutes = 0
    if expires_at is not None:
        remaining_minutes = max(int((expires_at - _utc_now()).total_seconds() // 60), 0)
    metrics_class_id = int(class_id) if int(class_id or 0) > 0 else active_class_id
    metrics = _load_metrics(metrics_class_id)
    ready_transition_count = _safe_int(metrics.get("ready_transition_count"))
    cumulative_ready_seconds = _safe_int(metrics.get("cumulative_ready_seconds"))
    avg_ready_seconds = 0
    if ready_transition_count > 0:
        avg_ready_seconds = max(int(round(cumulative_ready_seconds / ready_transition_count)), 0)
    return RemoteComputeLease(
        feature_enabled=feature_enabled,
        paid_usage_acknowledged=paid_usage_acknowledged,
        backend_configured=backend_configured,
        active=active,
        active_for_class=active_for_class,
        use_remote_backend=bool(active_for_class and state == "ready"),
        state=state,
        class_id=active_class_id,
        requested_by=str(payload.get("requested_by") or "").strip()[:150],
        requested_at=str(payload.get("requested_at") or "").strip()[:64],
        expires_at=expires_at_raw,
        requested_duration_minutes=_safe_int(payload.get("requested_duration_minutes")),
        remaining_minutes=remaining_minutes,
        provider_label=remote_compute_provider_label(),
        provider_request_id=str(payload.get("provider_request_id") or "").strip()[:120],
        provider_adapter=remote_compute_provider_adapter(),
        control_url_configured=bool(
            remote_compute_control_url_configured("activate") and remote_compute_control_url_configured("deactivate")
        ),
        healthcheck_url_configured=remote_compute_healthcheck_url_configured(),
        auto_stop_on_idle=remote_compute_idle_timeout_seconds() > 0,
        idle_timeout_seconds=remote_compute_idle_timeout_seconds(),
        last_error_code=str(payload.get("last_error_code") or "").strip()[:80],
        last_readiness_reason_code=str(payload.get("last_readiness_reason_code") or "").strip()[:80],
        status_detail=str(payload.get("status_detail") or "").strip()[:160],
        last_transition_at=str(payload.get("last_transition_at") or "").strip()[:64],
        last_healthcheck_at=str(payload.get("last_healthcheck_at") or "").strip()[:64],
        last_ready_probe_at=str(payload.get("last_ready_probe_at") or "").strip()[:64],
        last_ready_probe_ok_at=str(payload.get("last_ready_probe_ok_at") or "").strip()[:64],
        last_routed_at=str(payload.get("last_routed_at") or "").strip()[:64],
        activation_count=_safe_int(metrics.get("activation_count")),
        ready_transition_count=ready_transition_count,
        avg_ready_seconds=avg_ready_seconds,
        remote_route_count=_safe_int(metrics.get("remote_route_count")),
        fallback_local_count=_safe_int(metrics.get("fallback_local_count")),
        degraded_transition_count=_safe_int(metrics.get("degraded_transition_count")),
        provider_unreachable_count=_safe_int(metrics.get("provider_unreachable_count")),
        unused_activation_count=_safe_int(metrics.get("unused_activation_count")),
        last_activation_at=str(metrics.get("last_activation_at") or "").strip()[:64],
        last_ready_at=str(metrics.get("last_ready_at") or "").strip()[:64],
        last_fallback_at=str(metrics.get("last_fallback_at") or "").strip()[:64],
    )


def _state_timeout_seconds(payload: dict) -> int:
    expires_at = _parse_iso_datetime(str(payload.get("expires_at") or "").strip())
    if expires_at is None:
        return 300
    remaining = int((expires_at - _utc_now()).total_seconds())
    return max(remaining, 60)


def _normalize_state(value, *, default: str = "off") -> str:
    token = str(value or "").strip().lower()
    if token in _ALLOWED_STATES:
        return token
    if token in {"warming", "booting"}:
        return "starting"
    if token in {"running", "healthy"}:
        return "ready"
    if token in {"stopped", "inactive"}:
        return "off"
    return default if default in _ALLOWED_STATES else "off"


def _safe_json_dict(raw: str) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except Exception:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


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


def _control_request_id(value: str) -> str:
    return str(value or "").strip()[:80]


def _automatic_control_request_id(*, payload: dict, reason: str) -> str:
    session_id = _safe_int(payload.get("lease_session_id"))
    class_id = _safe_int(payload.get("class_id"))
    token = f"auto-{str(reason or '').strip()[:24]}-{class_id}-{session_id}"
    return token[:80]


def _normalize_stop_reason(value: str) -> str:
    token = str(value or "").strip().lower()
    if token in {"manual_stop", "class_end", "lease_expired", "idle_timeout"}:
        return token
    return "manual_stop"


def _stop_event_type(stop_reason: str) -> str:
    token = _normalize_stop_reason(stop_reason)
    if token == "class_end":
        return "lease_class_end_stop"
    if token == "lease_expired":
        return "lease_expired_auto_stop"
    if token == "idle_timeout":
        return "lease_idle_auto_stop"
    return "lease_stopped"


def _stop_mode_for_reason(stop_reason: str) -> str:
    token = _normalize_stop_reason(stop_reason)
    if token in {"lease_expired", "idle_timeout"}:
        return "auto"
    return "manual"


def _remote_backend_ready_probe() -> tuple[bool, str, str]:
    overrides = remote_compute_llm_overrides()
    if not overrides:
        return False, "remote_compute_probe_not_configured", "Remote helper warm probe could not resolve backend overrides."
    backend = resolve_backend_name(getenv=helper_getenv)
    started = time.monotonic()
    try:
        with helper_config_overrides(overrides):
            status = healthcheck_provider(
                backend,
                probe_chat=True,
                request_id="remote-compute-ready-probe",
            )
    except (
        LLMAuthError,
        LLMConfigError,
        LLMMalformedResponseError,
        LLMTimeoutError,
        LLMUpstreamUnavailableError,
        RuntimeError,
        ValueError,
    ) as exc:
        return False, exc.__class__.__name__, "Remote helper warm probe failed before ready verification."
    elapsed = max(time.monotonic() - started, 0.0)
    budget_seconds = float(remote_compute_ready_probe_max_seconds())
    if not status.ok:
        return False, str(status.detail or "remote_compute_probe_failed")[:80], "Remote helper warm probe is not yet healthy."
    if elapsed > budget_seconds:
        return (
            False,
            "remote_compute_probe_slow",
            f"Remote helper warm probe exceeded {int(budget_seconds)} second(s).",
        )
    return True, "", f"Remote helper warm probe succeeded in {elapsed:.1f} second(s)."


def _load_metrics(class_id: int) -> dict:
    return load_metrics(class_id)


def _persist_metrics(class_id: int, payload: dict) -> None:
    persist_metrics(class_id, payload)


def _record_activation(*, class_id: int, requested_at: str) -> None:
    metrics = _load_metrics(class_id)
    metrics["activation_count"] = _safe_int(metrics.get("activation_count")) + 1
    metrics["last_activation_at"] = str(requested_at or "").strip()[:64]
    _persist_metrics(class_id, metrics)


def _record_ready_transition(*, class_id: int, requested_at: str) -> None:
    metrics = _load_metrics(class_id)
    metrics["ready_transition_count"] = _safe_int(metrics.get("ready_transition_count")) + 1
    metrics["last_ready_at"] = _utc_now().isoformat()
    requested_at_dt = _parse_iso_datetime(str(requested_at or "").strip())
    if requested_at_dt is not None:
        elapsed_seconds = max(int((_utc_now() - requested_at_dt).total_seconds()), 0)
        metrics["cumulative_ready_seconds"] = _safe_int(metrics.get("cumulative_ready_seconds")) + elapsed_seconds
    _persist_metrics(class_id, metrics)


def _record_remote_route(*, class_id: int) -> None:
    metrics = _load_metrics(class_id)
    metrics["remote_route_count"] = _safe_int(metrics.get("remote_route_count")) + 1
    _persist_metrics(class_id, metrics)


def _record_fallback_local(*, class_id: int) -> None:
    metrics = _load_metrics(class_id)
    metrics["fallback_local_count"] = _safe_int(metrics.get("fallback_local_count")) + 1
    metrics["last_fallback_at"] = _utc_now().isoformat()
    _persist_metrics(class_id, metrics)


def _record_degraded_transition(*, class_id: int, error_code: str) -> None:
    metrics = _load_metrics(class_id)
    metrics["degraded_transition_count"] = _safe_int(metrics.get("degraded_transition_count")) + 1
    _persist_metrics(class_id, metrics)


def _record_provider_unreachable_if_needed(*, class_id: int, error_code: str) -> None:
    if not _looks_unreachable_error(error_code):
        return
    metrics = _load_metrics(class_id)
    metrics["provider_unreachable_count"] = _safe_int(metrics.get("provider_unreachable_count")) + 1
    _persist_metrics(class_id, metrics)


def _finalize_unused_activation_from_payload(payload: dict) -> None:
    class_id = _safe_int(payload.get("class_id"))
    if class_id <= 0:
        return
    requested_at = str(payload.get("requested_at") or "").strip()
    if not requested_at:
        return
    if str(payload.get("last_routed_at") or "").strip():
        return
    metrics = _load_metrics(class_id)
    metrics["unused_activation_count"] = _safe_int(metrics.get("unused_activation_count")) + 1
    _persist_metrics(class_id, metrics)


def _looks_unreachable_error(error_code: str) -> bool:
    return "unreachable" in str(error_code or "").strip().lower()


__all__ = [
    "RemoteComputeActionResult",
    "RemoteComputeLease",
    "activate_remote_compute",
    "active_remote_compute_overrides_for_class",
    "current_remote_compute_lease",
    "deactivate_remote_compute",
    "mark_remote_compute_fallback_local",
    "mark_remote_compute_degraded",
    "mark_remote_compute_routed",
    "reconcile_remote_compute_state",
    "remote_compute_duration_minutes",
]
