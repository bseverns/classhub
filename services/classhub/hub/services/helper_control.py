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
        with urllib.request.urlopen(request, timeout=timeout) as response:
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
