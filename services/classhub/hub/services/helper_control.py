"""Helper control-plane calls used by teacher actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class HelperResetResult:
    ok: bool
    deleted_conversations: int = 0
    archived_conversations: int = 0
    archive_path: str = ""
    request_id: str = ""
    error_code: str = ""
    status_code: int = 0


@dataclass(frozen=True)
class HelperRagStatusResult:
    ok: bool
    rag_enabled: bool = False
    index_ready: bool = False
    indexed_chunk_count: int = 0
    reference_source_count: int = 0
    last_index_built_at: str = ""
    reference_sources: list[dict] | None = None
    configured_reference_keys: list[str] | None = None
    student_data_excluded_from_index: bool = True
    request_id: str = ""
    error_code: str = ""
    status_code: int = 0


@dataclass(frozen=True)
class HelperRemoteComputeStatusResult:
    ok: bool
    feature_enabled: bool = False
    paid_usage_acknowledged: bool = False
    backend_configured: bool = False
    active: bool = False
    active_for_class: bool = False
    use_remote_backend: bool = False
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
    requested_duration_minutes_total: int = 0
    starting_seconds_total: int = 0
    ready_seconds_total: int = 0
    degraded_seconds_total: int = 0
    manual_stop_count_total: int = 0
    auto_stop_count_total: int = 0
    leased_minutes_total: int = 0
    approximate_cost_usd_total: str = ""
    request_id: str = ""
    error_code: str = ""
    status_code: int = 0


@dataclass(frozen=True)
class HelperRemoteComputeEvidenceResult:
    ok: bool
    class_id: int = 0
    active_lease: dict | None = None
    summary: dict | None = None
    recent_sessions: list[dict] | None = None
    recent_events: list[dict] | None = None
    request_id: str = ""
    error_code: str = ""
    status_code: int = 0


@dataclass(frozen=True)
class HelperRemoteComputeActionResult:
    ok: bool
    action: str = ""
    active: bool = False
    active_for_class: bool = False
    use_remote_backend: bool = False
    state: str = "off"
    class_id: int = 0
    requested_by: str = ""
    requested_at: str = ""
    expires_at: str = ""
    remaining_minutes: int = 0
    provider_request_id: str = ""
    status_detail: str = ""
    detail: str = ""
    request_id: str = ""
    error_code: str = ""
    status_code: int = 0


def reset_class_conversations(
    *,
    class_id: int,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
    export_before_reset: bool = True,
) -> HelperResetResult:
    request_id = _request_id_value("")
    if class_id <= 0:
        return HelperResetResult(ok=False, request_id=request_id, error_code="invalid_class_id")
    if not endpoint_url:
        return HelperResetResult(ok=False, request_id=request_id, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperResetResult(ok=False, request_id=request_id, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperResetResult(ok=False, request_id=request_id, error_code="invalid_endpoint_url_scheme")

    payload = json.dumps(
        {"class_id": int(class_id), "export_before_reset": bool(export_before_reset)}
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {internal_token}",
            "X-Request-ID": request_id,
        },
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
            response_request_id = _response_request_id(response=response, body=body, fallback=request_id)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperResetResult(
            ok=False,
            request_id=_response_request_id(response=exc, body=body, fallback=request_id),
            error_code=error_code,
            status_code=status,
        )
    except urllib.error.URLError:
        return HelperResetResult(ok=False, request_id=request_id, error_code="helper_unreachable")
    except Exception:
        return HelperResetResult(ok=False, request_id=request_id, error_code="helper_request_failed")

    if status < 200 or status >= 300:
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperResetResult(ok=False, request_id=response_request_id, error_code=error_code, status_code=status)

    parsed = _safe_json_dict(body)
    if not parsed.get("ok"):
        return HelperResetResult(
            ok=False,
            request_id=response_request_id,
            error_code=str(parsed.get("error") or "helper_reset_failed"),
            status_code=status,
        )
    try:
        deleted = int(parsed.get("deleted_conversations") or 0)
    except Exception:
        deleted = 0
    try:
        archived = int(parsed.get("archived_conversations") or 0)
    except Exception:
        archived = 0
    archive_path = str(parsed.get("archive_path") or "").strip()
    return HelperResetResult(
        ok=True,
        deleted_conversations=max(deleted, 0),
        archived_conversations=max(archived, 0),
        archive_path=archive_path[:512],
        request_id=response_request_id,
        status_code=status,
    )


def fetch_rag_status(
    *,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
) -> HelperRagStatusResult:
    request_id = _request_id_value("")
    if not endpoint_url:
        return HelperRagStatusResult(ok=False, request_id=request_id, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperRagStatusResult(ok=False, request_id=request_id, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperRagStatusResult(ok=False, request_id=request_id, error_code="invalid_endpoint_url_scheme")

    request = urllib.request.Request(
        endpoint_url,
        method="GET",
        headers={"Authorization": f"Bearer {internal_token}", "X-Request-ID": request_id},
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
            response_request_id = _response_request_id(response=response, body=body, fallback=request_id)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperRagStatusResult(
            ok=False,
            request_id=_response_request_id(response=exc, body=body, fallback=request_id),
            error_code=error_code,
            status_code=status,
        )
    except urllib.error.URLError:
        return HelperRagStatusResult(ok=False, request_id=request_id, error_code="helper_unreachable")
    except Exception:
        return HelperRagStatusResult(ok=False, request_id=request_id, error_code="helper_request_failed")

    if status < 200 or status >= 300:
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperRagStatusResult(ok=False, request_id=response_request_id, error_code=error_code, status_code=status)

    payload = _safe_json_dict(body)
    if not payload.get("ok"):
        return HelperRagStatusResult(
            ok=False,
            request_id=response_request_id,
            error_code=str(payload.get("error") or "helper_status_failed"),
            status_code=status,
        )
    return HelperRagStatusResult(
        ok=True,
        rag_enabled=bool(payload.get("rag_enabled")),
        index_ready=bool(payload.get("index_ready")),
        indexed_chunk_count=_safe_non_negative_int(payload.get("indexed_chunk_count")),
        reference_source_count=_safe_non_negative_int(payload.get("reference_source_count")),
        last_index_built_at=str(payload.get("last_index_built_at") or "").strip()[:64],
        reference_sources=_safe_reference_rows(payload.get("reference_sources")),
        configured_reference_keys=_safe_reference_keys(payload.get("configured_reference_keys")),
        student_data_excluded_from_index=bool(payload.get("student_data_excluded_from_index", True)),
        request_id=response_request_id,
        status_code=status,
    )


def fetch_remote_compute_status(
    *,
    class_id: int,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
) -> HelperRemoteComputeStatusResult:
    request_id = _request_id_value("")
    if class_id <= 0:
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="invalid_class_id")
    if not endpoint_url:
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="invalid_endpoint_url_scheme")

    delimiter = "&" if "?" in endpoint_url else "?"
    request = urllib.request.Request(
        f"{endpoint_url}{delimiter}class_id={int(class_id)}",
        method="GET",
        headers={"Authorization": f"Bearer {internal_token}", "X-Request-ID": request_id},
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
            response_request_id = _response_request_id(response=response, body=body, fallback=request_id)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return HelperRemoteComputeStatusResult(
            ok=False,
            request_id=_response_request_id(response=exc, body=body, fallback=request_id),
            error_code=_extract_error_code(body) or "helper_http_error",
            status_code=status,
        )
    except urllib.error.URLError:
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="helper_unreachable")
    except Exception:
        return HelperRemoteComputeStatusResult(ok=False, request_id=request_id, error_code="helper_request_failed")

    payload = _safe_json_dict(body)
    if status < 200 or status >= 300 or not payload.get("ok"):
        return HelperRemoteComputeStatusResult(
            ok=False,
            request_id=response_request_id,
            error_code=str(payload.get("error") or "helper_status_failed"),
            status_code=status,
        )
    return HelperRemoteComputeStatusResult(
        ok=True,
        feature_enabled=bool(payload.get("feature_enabled")),
        paid_usage_acknowledged=bool(payload.get("paid_usage_acknowledged")),
        backend_configured=bool(payload.get("backend_configured")),
        active=bool(payload.get("active")),
        active_for_class=bool(payload.get("active_for_class")),
        use_remote_backend=bool(payload.get("use_remote_backend")),
        state=str(payload.get("state") or "off").strip()[:32],
        class_id=_safe_non_negative_int(payload.get("class_id")),
        requested_by=str(payload.get("requested_by") or "").strip()[:150],
        requested_at=str(payload.get("requested_at") or "").strip()[:64],
        expires_at=str(payload.get("expires_at") or "").strip()[:64],
        requested_duration_minutes=_safe_non_negative_int(payload.get("requested_duration_minutes")),
        remaining_minutes=_safe_non_negative_int(payload.get("remaining_minutes")),
        provider_label=str(payload.get("provider_label") or "").strip()[:80],
        provider_request_id=str(payload.get("provider_request_id") or "").strip()[:120],
        provider_adapter=str(payload.get("provider_adapter") or "").strip()[:80],
        control_url_configured=bool(payload.get("control_url_configured")),
        healthcheck_url_configured=bool(payload.get("healthcheck_url_configured")),
        auto_stop_on_idle=bool(payload.get("auto_stop_on_idle")),
        idle_timeout_seconds=_safe_non_negative_int(payload.get("idle_timeout_seconds")),
        last_error_code=str(payload.get("last_error_code") or "").strip()[:80],
        last_readiness_reason_code=str(payload.get("last_readiness_reason_code") or "").strip()[:80],
        status_detail=str(payload.get("status_detail") or "").strip()[:160],
        last_transition_at=str(payload.get("last_transition_at") or "").strip()[:64],
        last_healthcheck_at=str(payload.get("last_healthcheck_at") or "").strip()[:64],
        last_ready_probe_at=str(payload.get("last_ready_probe_at") or "").strip()[:64],
        last_ready_probe_ok_at=str(payload.get("last_ready_probe_ok_at") or "").strip()[:64],
        last_routed_at=str(payload.get("last_routed_at") or "").strip()[:64],
        activation_count=_safe_non_negative_int(payload.get("activation_count")),
        ready_transition_count=_safe_non_negative_int(payload.get("ready_transition_count")),
        avg_ready_seconds=_safe_non_negative_int(payload.get("avg_ready_seconds")),
        remote_route_count=_safe_non_negative_int(payload.get("remote_route_count")),
        fallback_local_count=_safe_non_negative_int(payload.get("fallback_local_count")),
        degraded_transition_count=_safe_non_negative_int(payload.get("degraded_transition_count")),
        provider_unreachable_count=_safe_non_negative_int(payload.get("provider_unreachable_count")),
        unused_activation_count=_safe_non_negative_int(payload.get("unused_activation_count")),
        last_activation_at=str(payload.get("last_activation_at") or "").strip()[:64],
        last_ready_at=str(payload.get("last_ready_at") or "").strip()[:64],
        last_fallback_at=str(payload.get("last_fallback_at") or "").strip()[:64],
        requested_duration_minutes_total=_safe_non_negative_int(payload.get("requested_duration_minutes_total")),
        starting_seconds_total=_safe_non_negative_int(payload.get("starting_seconds_total")),
        ready_seconds_total=_safe_non_negative_int(payload.get("ready_seconds_total")),
        degraded_seconds_total=_safe_non_negative_int(payload.get("degraded_seconds_total")),
        manual_stop_count_total=_safe_non_negative_int(payload.get("manual_stop_count_total")),
        auto_stop_count_total=_safe_non_negative_int(payload.get("auto_stop_count_total")),
        leased_minutes_total=_safe_non_negative_int(payload.get("leased_minutes_total")),
        approximate_cost_usd_total=str(payload.get("approximate_cost_usd_total") or "").strip()[:32],
        request_id=response_request_id,
        status_code=status,
    )


def fetch_remote_compute_evidence(
    *,
    class_id: int,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
) -> HelperRemoteComputeEvidenceResult:
    request_id = _request_id_value("")
    if class_id <= 0:
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="invalid_class_id")
    if not endpoint_url:
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="invalid_endpoint_url_scheme")

    delimiter = "&" if "?" in endpoint_url else "?"
    request = urllib.request.Request(
        f"{endpoint_url}{delimiter}class_id={int(class_id)}",
        method="GET",
        headers={"Authorization": f"Bearer {internal_token}", "X-Request-ID": request_id},
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
            response_request_id = _response_request_id(response=response, body=body, fallback=request_id)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return HelperRemoteComputeEvidenceResult(
            ok=False,
            request_id=_response_request_id(response=exc, body=body, fallback=request_id),
            error_code=_extract_error_code(body) or "helper_http_error",
            status_code=status,
        )
    except urllib.error.URLError:
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="helper_unreachable")
    except Exception:
        return HelperRemoteComputeEvidenceResult(ok=False, request_id=request_id, error_code="helper_request_failed")

    payload = _safe_json_dict(body)
    if status < 200 or status >= 300 or not payload.get("ok"):
        return HelperRemoteComputeEvidenceResult(
            ok=False,
            request_id=response_request_id,
            error_code=str(payload.get("error") or "helper_status_failed"),
            status_code=status,
        )
    active_lease = payload.get("active_lease") if isinstance(payload.get("active_lease"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    recent_sessions = payload.get("recent_sessions") if isinstance(payload.get("recent_sessions"), list) else []
    recent_events = payload.get("recent_events") if isinstance(payload.get("recent_events"), list) else []
    return HelperRemoteComputeEvidenceResult(
        ok=True,
        class_id=_safe_non_negative_int(payload.get("class_id")),
        active_lease=active_lease,
        summary=summary,
        recent_sessions=[item for item in recent_sessions if isinstance(item, dict)],
        recent_events=[item for item in recent_events if isinstance(item, dict)],
        request_id=response_request_id,
        status_code=status,
    )


def set_remote_compute_state(
    *,
    class_id: int,
    action: str,
    requested_by: str,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
    duration_minutes: int = 0,
) -> HelperRemoteComputeActionResult:
    request_id = _request_id_value("")
    if class_id <= 0:
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="invalid_class_id")
    if action not in {"activate", "deactivate"}:
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="invalid_action")
    if not requested_by:
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="missing_requested_by")
    if not endpoint_url:
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperRemoteComputeActionResult(ok=False, request_id=request_id, error_code="invalid_endpoint_url_scheme")

    payload = {
        "action": action,
        "class_id": int(class_id),
        "requested_by": str(requested_by).strip()[:150],
    }
    if action == "activate":
        payload["duration_minutes"] = max(int(duration_minutes or 0), 0)

    request = urllib.request.Request(
        endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {internal_token}",
            "X-Request-ID": request_id,
        },
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
            response_request_id = _response_request_id(response=response, body=body, fallback=request_id)
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return HelperRemoteComputeActionResult(
            ok=False,
            action=action,
            request_id=_response_request_id(response=exc, body=body, fallback=request_id),
            error_code=_extract_error_code(body) or "helper_http_error",
            status_code=status,
        )
    except urllib.error.URLError:
        return HelperRemoteComputeActionResult(ok=False, action=action, request_id=request_id, error_code="helper_unreachable")
    except Exception:
        return HelperRemoteComputeActionResult(ok=False, action=action, request_id=request_id, error_code="helper_request_failed")

    parsed = _safe_json_dict(body)
    lease = parsed.get("lease") if isinstance(parsed.get("lease"), dict) else {}
    if status < 200 or status >= 300 or not parsed.get("ok"):
        return HelperRemoteComputeActionResult(
            ok=False,
            action=action,
            active=bool(lease.get("active")),
            active_for_class=bool(lease.get("active_for_class")),
            use_remote_backend=bool(lease.get("use_remote_backend")),
            state=str(lease.get("state") or "off").strip()[:32],
            class_id=_safe_non_negative_int(lease.get("class_id")),
            expires_at=str(lease.get("expires_at") or "").strip()[:64],
            remaining_minutes=_safe_non_negative_int(lease.get("remaining_minutes")),
            request_id=response_request_id,
            error_code=str(parsed.get("error") or "remote_compute_control_failed"),
            status_code=status,
        )
    return HelperRemoteComputeActionResult(
        ok=True,
        action=str(parsed.get("action") or action),
        active=bool(lease.get("active")),
        active_for_class=bool(lease.get("active_for_class")),
        use_remote_backend=bool(lease.get("use_remote_backend")),
        state=str(lease.get("state") or "off").strip()[:32],
        class_id=_safe_non_negative_int(lease.get("class_id")),
        requested_by=str(lease.get("requested_by") or "").strip()[:150],
        requested_at=str(lease.get("requested_at") or "").strip()[:64],
        expires_at=str(lease.get("expires_at") or "").strip()[:64],
        remaining_minutes=_safe_non_negative_int(lease.get("remaining_minutes")),
        provider_request_id=str(parsed.get("provider_request_id") or "").strip()[:120],
        status_detail=str(parsed.get("detail") or "").strip()[:160],
        detail=str(parsed.get("detail") or "").strip()[:160],
        request_id=response_request_id,
        status_code=status,
    )


def _request_id_value(value: str) -> str:
    token = str(value or "").strip()[:80]
    return token or uuid4().hex


def _response_request_id(*, response, body: str, fallback: str) -> str:
    header_value = ""
    headers = getattr(response, "headers", None)
    if headers is not None:
        try:
            header_value = str(headers.get("X-Request-ID") or "").strip()
        except Exception:
            header_value = ""
    if header_value:
        return _request_id_value(header_value)
    parsed = _safe_json_dict(body)
    return _request_id_value(str(parsed.get("request_id") or fallback))


def _safe_json_dict(raw: str) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except Exception:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _extract_error_code(raw: str) -> str:
    payload = _safe_json_dict(raw)
    value = str(payload.get("error") or "").strip().lower()
    if not value:
        return ""
    return value[:80]


def _safe_non_negative_int(value) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return max(parsed, 0)


def _safe_reference_rows(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "reference_key": str(item.get("reference_key") or "").strip()[:80],
                "chunk_count": _safe_non_negative_int(item.get("chunk_count")),
                "last_indexed_at": str(item.get("last_indexed_at") or "").strip()[:64],
            }
        )
    return rows


def _safe_reference_keys(value) -> list[str]:
    if not isinstance(value, list):
        return []
    keys: list[str] = []
    for item in value:
        token = str(item or "").strip()
        if token:
            keys.append(token[:80])
    return keys
