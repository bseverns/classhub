"""Provider adapters for bounded remote helper compute orchestration."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .engine.config_source import helper_explicit_env

_ALLOWED_STATES = {"off", "requested", "starting", "ready", "degraded", "stopping", "error"}


@dataclass(frozen=True)
class RemoteComputeProviderResult:
    ok: bool
    state: str = "error"
    detail: str = ""
    provider_request_id: str = ""
    error_code: str = ""
    status_code: int = 0


class GenericWebhookRemoteComputeProvider:
    """Minimal webhook-based orchestration bridge."""

    def __init__(self, *, provider_name: str = "generic_webhook"):
        self.provider_name = provider_name

    def activate(
        self,
        *,
        class_id: int,
        requested_by: str,
        duration_minutes: int,
        control_request_id: str = "",
    ) -> RemoteComputeProviderResult:
        return self._request(
            "activate",
            payload={
                "class_id": int(class_id),
                "requested_by": str(requested_by or "").strip()[:150],
                "duration_minutes": int(duration_minutes),
                "control_request_id": _control_request_id(control_request_id),
                "idempotency_key": _idempotency_key(
                    action="activate",
                    class_id=class_id,
                    control_request_id=control_request_id,
                ),
            },
            control_request_id=control_request_id,
            class_id=class_id,
        )

    def deactivate(
        self,
        *,
        class_id: int,
        requested_by: str,
        control_request_id: str = "",
        stop_reason: str = "",
    ) -> RemoteComputeProviderResult:
        return self._request(
            "deactivate",
            payload={
                "class_id": int(class_id),
                "requested_by": str(requested_by or "").strip()[:150],
                "control_request_id": _control_request_id(control_request_id),
                "idempotency_key": _idempotency_key(
                    action="deactivate",
                    class_id=class_id,
                    control_request_id=control_request_id,
                ),
                "stop_reason": str(stop_reason or "").strip()[:80],
            },
            control_request_id=control_request_id,
            class_id=class_id,
        )

    def healthcheck(
        self,
        *,
        class_id: int,
        provider_request_id: str = "",
        control_request_id: str = "",
    ) -> RemoteComputeProviderResult:
        url = (helper_explicit_env("HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL") or "").strip()
        if not url:
            return RemoteComputeProviderResult(ok=False, error_code="remote_compute_healthcheck_not_configured")
        delimiter = "&" if "?" in url else "?"
        query = urllib.parse.urlencode(
            {
                "class_id": int(class_id),
                "provider_request_id": str(provider_request_id or "").strip()[:120],
                "control_request_id": _control_request_id(control_request_id),
            }
        )
        return self._request_url(
            "GET",
            f"{url}{delimiter}{query}",
            payload=None,
            control_request_id=control_request_id,
            idempotency_key=_idempotency_key(
                action="healthcheck",
                class_id=class_id,
                control_request_id=control_request_id,
            ),
        )

    def supports_healthcheck(self) -> bool:
        return bool((helper_explicit_env("HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL") or "").strip())

    def _request(
        self,
        action: str,
        *,
        payload: dict,
        control_request_id: str = "",
        class_id: int = 0,
    ) -> RemoteComputeProviderResult:
        url = (helper_explicit_env(f"HELPER_REMOTE_COMPUTE_{action.upper()}_URL") or "").strip()
        if not url:
            return RemoteComputeProviderResult(ok=False, error_code="remote_compute_control_not_configured")
        return self._request_url(
            "POST",
            url,
            payload=payload,
            control_request_id=control_request_id,
            idempotency_key=_idempotency_key(
                action=action,
                class_id=class_id,
                control_request_id=control_request_id,
            ),
        )

    def _request_url(
        self,
        method: str,
        url: str,
        *,
        payload: dict | None,
        control_request_id: str = "",
        idempotency_key: str = "",
    ) -> RemoteComputeProviderResult:
        token = (helper_explicit_env("HELPER_REMOTE_COMPUTE_CONTROL_API_KEY") or "").strip()
        timeout_seconds = max(_safe_int(helper_explicit_env("HELPER_REMOTE_COMPUTE_CONTROL_TIMEOUT_SECONDS") or "8"), 1)
        headers = {
            "Accept": "application/json",
            "User-Agent": f"ClassHub-RemoteCompute/{self.provider_name}",
        }
        control_request_id = _control_request_id(control_request_id)
        if control_request_id:
            headers["X-Control-Request-ID"] = control_request_id
        if idempotency_key:
            headers["X-Idempotency-Key"] = str(idempotency_key or "").strip()[:160]
        body_bytes = None
        if method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            body_bytes = json.dumps(payload or {}).encode("utf-8")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            url,
            data=body_bytes,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
                status = int(getattr(response, "status", 200) or 200)
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return RemoteComputeProviderResult(
                ok=False,
                error_code="remote_compute_provider_http_error",
                status_code=int(getattr(exc, "code", 0) or 0),
            )
        except urllib.error.URLError:
            return RemoteComputeProviderResult(ok=False, error_code="remote_compute_provider_unreachable")
        except Exception:
            return RemoteComputeProviderResult(ok=False, error_code="remote_compute_provider_request_failed")
        if status < 200 or status >= 300:
            return RemoteComputeProviderResult(
                ok=False,
                error_code="remote_compute_provider_http_error",
                status_code=status,
            )
        payload_dict = _safe_json_dict(body)
        if payload_dict.get("ok") is False:
            return RemoteComputeProviderResult(
                ok=False,
                error_code=str(payload_dict.get("error") or "remote_compute_provider_error").strip()[:80],
                status_code=status,
            )
        state = _recognized_state(payload_dict.get("state"))
        if payload_dict.get("ok") is not True or state is None:
            return RemoteComputeProviderResult(
                ok=False,
                error_code="remote_compute_provider_invalid_response",
                status_code=status,
            )
        detail = str(payload_dict.get("detail") or payload_dict.get("message") or state).strip()[:160]
        provider_request_id = str(
            payload_dict.get("request_id") or payload_dict.get("provider_request_id") or ""
        ).strip()[:120]
        return RemoteComputeProviderResult(
            ok=True,
            state=state,
            detail=detail,
            provider_request_id=provider_request_id,
            status_code=status,
        )


class ThunderWebhookRemoteComputeProvider(GenericWebhookRemoteComputeProvider):
    """Thunder-oriented webhook seam with the same narrow generic contract."""

    def __init__(self):
        super().__init__(provider_name="thunder_webhook")


def build_remote_compute_provider():
    adapter = (helper_explicit_env("HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER") or "").strip().lower()
    if adapter == "thunder_webhook":
        return ThunderWebhookRemoteComputeProvider()
    return GenericWebhookRemoteComputeProvider(provider_name=adapter or "generic_webhook")


def _recognized_state(value) -> str | None:
    token = str(value or "").strip().lower()
    if token in _ALLOWED_STATES:
        return token
    aliases = {
        "warming": "starting",
        "booting": "starting",
        "running": "ready",
        "healthy": "ready",
        "stopped": "off",
        "inactive": "off",
    }
    return aliases.get(token)


def _safe_json_dict(raw: str) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except Exception:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _control_request_id(value: str) -> str:
    return str(value or "").strip()[:80]


def _idempotency_key(*, action: str, class_id: int, control_request_id: str) -> str:
    request_id = _control_request_id(control_request_id)
    if not request_id:
        return ""
    return f"remote-compute:{str(action or '').strip()[:32]}:{int(class_id or 0)}:{request_id}"[:160]


__all__ = [
    "GenericWebhookRemoteComputeProvider",
    "RemoteComputeProviderResult",
    "ThunderWebhookRemoteComputeProvider",
    "build_remote_compute_provider",
]
