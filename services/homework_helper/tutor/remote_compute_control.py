"""Bounded remote helper compute lifecycle and status helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from django.core.cache import cache

from .engine.config_source import helper_explicit_env, helper_getenv
from .remote_compute_provider import build_remote_compute_provider

_LEASE_CACHE_KEY = "helper:remote_compute:lease"
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
    remaining_minutes: int = 0
    provider_label: str = ""
    provider_request_id: str = ""
    provider_adapter: str = ""
    control_url_configured: bool = False
    healthcheck_url_configured: bool = False
    auto_stop_on_idle: bool = False
    idle_timeout_seconds: int = 0
    last_error_code: str = ""
    status_detail: str = ""
    last_transition_at: str = ""
    last_healthcheck_at: str = ""
    last_routed_at: str = ""


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


def activate_remote_compute(*, class_id: int, requested_by: str, duration_minutes: int) -> RemoteComputeActionResult:
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

    provider = build_remote_compute_provider()
    provider_result = provider.activate(
        class_id=class_id,
        requested_by=requested_by,
        duration_minutes=duration,
    )
    if not provider_result.ok:
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

    now = _utc_now()
    expires_at = now + timedelta(minutes=duration)
    state = _normalize_state(provider_result.state, default="ready")
    payload = {
        "state": state,
        "class_id": int(class_id),
        "requested_by": str(requested_by or "").strip()[:150],
        "requested_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "provider_request_id": provider_result.provider_request_id,
        "status_detail": provider_result.detail,
        "last_error_code": "",
        "last_transition_at": now.isoformat(),
        "last_healthcheck_at": "",
        "last_routed_at": "",
    }
    _persist_state(payload, timeout_seconds=max(duration * 60, 60))
    return RemoteComputeActionResult(
        ok=True,
        action="activate",
        lease=current_remote_compute_lease(class_id=class_id),
        provider_request_id=str(provider_result.provider_request_id or "")[:120],
        detail=str(provider_result.detail or "").strip()[:160],
        status_code=int(provider_result.status_code),
    )


def deactivate_remote_compute(*, class_id: int, requested_by: str) -> RemoteComputeActionResult:
    lease = current_remote_compute_lease(class_id=class_id)
    if not lease.feature_enabled:
        return RemoteComputeActionResult(ok=False, action="deactivate", lease=lease, error_code="remote_compute_disabled")
    if not remote_compute_control_url_configured("deactivate"):
        return RemoteComputeActionResult(
            ok=False,
            action="deactivate",
            lease=lease,
            error_code="remote_compute_control_not_configured",
        )

    provider = build_remote_compute_provider()
    provider_result = provider.deactivate(class_id=class_id, requested_by=requested_by)
    if not provider_result.ok:
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
        cache.delete(_LEASE_CACHE_KEY)
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
    payload["state"] = "degraded"
    payload["last_error_code"] = str(error_code or "").strip()[:80]
    payload["status_detail"] = "Remote helper compute fell back to local/default mode."
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))


def mark_remote_compute_routed(*, class_id: int) -> None:
    payload = _load_cached_state()
    if not payload or _safe_int(payload.get("class_id")) != int(class_id):
        return
    if _normalize_state(payload.get("state")) != "ready":
        return
    payload["last_routed_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))


def _load_cached_state() -> dict:
    cached = cache.get(_LEASE_CACHE_KEY) or {}
    if isinstance(cached, dict):
        return dict(cached)
    return {}


def _persist_state(payload: dict, *, timeout_seconds: int) -> None:
    cache.set(_LEASE_CACHE_KEY, payload, timeout=max(timeout_seconds, 60))


def _expire_elapsed_lease(payload: dict) -> dict:
    if not payload:
        return {}
    expires_at = _parse_iso_datetime(str(payload.get("expires_at") or "").strip())
    if expires_at is None:
        return payload
    if expires_at > _utc_now():
        return payload
    cache.delete(_LEASE_CACHE_KEY)
    return {}


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
    )
    if result.ok:
        cache.delete(_LEASE_CACHE_KEY)
        return {}
    payload["state"] = "error"
    payload["last_error_code"] = result.error_code or "remote_compute_idle_stop_failed"
    payload["status_detail"] = "Idle auto-stop could not return remote helper compute to off."
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
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
    )
    payload["last_healthcheck_at"] = _utc_now().isoformat()
    if not result.ok:
        if state in {"requested", "starting"}:
            payload["status_detail"] = payload.get("status_detail") or "Remote helper compute is still starting."
        else:
            payload["state"] = "degraded"
            payload["last_error_code"] = result.error_code or "remote_compute_healthcheck_failed"
            payload["status_detail"] = "Remote helper compute healthcheck failed; helper stays on local/default mode."
            payload["last_transition_at"] = _utc_now().isoformat()
        _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
        return payload
    next_state = _normalize_state(result.state, default="ready")
    if next_state == "off":
        cache.delete(_LEASE_CACHE_KEY)
        return {}
    payload["state"] = next_state
    payload["provider_request_id"] = result.provider_request_id or str(payload.get("provider_request_id") or "")
    payload["status_detail"] = result.detail or str(payload.get("status_detail") or "")
    payload["last_error_code"] = ""
    payload["last_transition_at"] = _utc_now().isoformat()
    _persist_state(payload, timeout_seconds=_state_timeout_seconds(payload))
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
        status_detail=str(payload.get("status_detail") or "").strip()[:160],
        last_transition_at=str(payload.get("last_transition_at") or "").strip()[:64],
        last_healthcheck_at=str(payload.get("last_healthcheck_at") or "").strip()[:64],
        last_routed_at=str(payload.get("last_routed_at") or "").strip()[:64],
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


__all__ = [
    "RemoteComputeActionResult",
    "RemoteComputeLease",
    "activate_remote_compute",
    "active_remote_compute_overrides_for_class",
    "current_remote_compute_lease",
    "deactivate_remote_compute",
    "mark_remote_compute_degraded",
    "mark_remote_compute_routed",
    "remote_compute_duration_minutes",
]
