"""Structured audit logging for helper internal control/status endpoints."""

from __future__ import annotations

import ipaddress
import logging

from .engine import runtime as engine_runtime

logger = logging.getLogger("tutor.internal_audit")


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        for part in forwarded.split(","):
            candidate = part.strip()
            if not candidate:
                continue
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                continue

    remote = (request.META.get("REMOTE_ADDR", "") or "").strip()
    if remote:
        try:
            ipaddress.ip_address(remote)
            return remote
        except ValueError:
            pass
    return ""


def _clean_text(value, *, limit: int = 120) -> str:
    return engine_runtime.redact(str(value or "").strip())[:limit]


def log_internal_audit_event(level: str, event: str, *, request, request_id: str, **fields) -> None:
    payload = {
        "audit_kind": "helper_internal_api",
        "endpoint": _clean_text(getattr(request, "path", "")),
        "method": _clean_text(getattr(request, "method", ""), limit=16),
        "caller_ip": _client_ip(request),
    }
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, str):
            payload[key] = _clean_text(value, limit=200)
        else:
            payload[key] = value
    engine_runtime.log_chat_event(
        level,
        event,
        request_id_value=request_id,
        logger=logger,
        **payload,
    )


__all__ = ["log_internal_audit_event"]
