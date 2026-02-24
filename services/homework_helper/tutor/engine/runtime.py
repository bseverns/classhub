"""Runtime helpers for helper request handling."""

from __future__ import annotations

import json
import re
import uuid
from django.http import JsonResponse

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def redact(text: str) -> str:
    value = str(text or "")
    value = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = PHONE_RE.sub("[REDACTED_PHONE]", value)
    return value


def env_int(name: str, default: int, *, getenv) -> int:
    raw = getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def env_float(name: str, default: float, *, getenv) -> float:
    raw = getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def env_bool(name: str, default: bool, *, getenv) -> bool:
    raw = getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def request_id(request) -> str:
    header_value = (request.META.get("HTTP_X_REQUEST_ID", "") or "").strip()
    if header_value:
        return header_value[:80]
    return uuid.uuid4().hex


def json_response(payload: dict, *, request_id_value: str, status: int = 200) -> JsonResponse:
    body = dict(payload or {})
    body.setdefault("request_id", request_id_value)
    resp = JsonResponse(body, status=status)
    resp["X-Request-ID"] = request_id_value
    resp["Cache-Control"] = "no-store"
    resp["Pragma"] = "no-cache"
    return resp


def log_chat_event(level: str, event: str, *, request_id_value: str, logger, **fields):
    row = {"event": event, "request_id": request_id_value, **fields}
    line = json.dumps(row, sort_keys=True, default=str)
    if level == "warning":
        logger.warning(line)
    elif level == "error":
        logger.error(line)
    else:
        logger.info(line)

