"""Helper control-plane calls used by teacher actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class HelperResetResult:
    ok: bool
    deleted_conversations: int = 0
    archived_conversations: int = 0
    archive_path: str = ""
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
    if class_id <= 0:
        return HelperResetResult(ok=False, error_code="invalid_class_id")
    if not endpoint_url:
        return HelperResetResult(ok=False, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperResetResult(ok=False, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperResetResult(ok=False, error_code="invalid_endpoint_url_scheme")

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
        },
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperResetResult(ok=False, error_code=error_code, status_code=status)
    except urllib.error.URLError:
        return HelperResetResult(ok=False, error_code="helper_unreachable")
    except Exception:
        return HelperResetResult(ok=False, error_code="helper_request_failed")

    if status < 200 or status >= 300:
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperResetResult(ok=False, error_code=error_code, status_code=status)

    parsed = _safe_json_dict(body)
    if not parsed.get("ok"):
        return HelperResetResult(
            ok=False,
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
        status_code=status,
    )


def fetch_rag_status(
    *,
    endpoint_url: str,
    internal_token: str,
    timeout_seconds: float,
) -> HelperRagStatusResult:
    if not endpoint_url:
        return HelperRagStatusResult(ok=False, error_code="helper_endpoint_not_configured")
    if not internal_token:
        return HelperRagStatusResult(ok=False, error_code="helper_token_not_configured")
    if not endpoint_url.lower().startswith(("http://", "https://")):
        return HelperRagStatusResult(ok=False, error_code="invalid_endpoint_url_scheme")

    request = urllib.request.Request(
        endpoint_url,
        method="GET",
        headers={"Authorization": f"Bearer {internal_token}"},
    )
    timeout = max(float(timeout_seconds), 0.2)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            status = int(getattr(response, "status", 200) or 200)
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperRagStatusResult(ok=False, error_code=error_code, status_code=status)
    except urllib.error.URLError:
        return HelperRagStatusResult(ok=False, error_code="helper_unreachable")
    except Exception:
        return HelperRagStatusResult(ok=False, error_code="helper_request_failed")

    if status < 200 or status >= 300:
        error_code = _extract_error_code(body) or "helper_http_error"
        return HelperRagStatusResult(ok=False, error_code=error_code, status_code=status)

    payload = _safe_json_dict(body)
    if not payload.get("ok"):
        return HelperRagStatusResult(
            ok=False,
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
        status_code=status,
    )


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
