"""Telemetry split instrumentation helpers.

These helpers are intentionally lightweight in Phase 1 Slice 0:
- track write attempt/success/failure counters in cache,
- emit structured log fields for rollout diagnostics,
- avoid request-path failures when cache/logging is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_COUNTER_PREFIX = "classhub:telemetry_split:v1"
_COUNTER_NAMES = ("attempts", "successes", "failures")
_COUNTER_TTL_SECONDS = 7 * 24 * 3600


def _safe_token(value: str | None, *, fallback: str) -> str:
    token = str(value or "").strip().lower().replace("-", "_")
    return token or fallback


def _write_mode() -> str:
    return _safe_token(
        str(getattr(settings, "CLASSHUB_TELEMETRY_WRITE_MODE", "off") or "off"),
        fallback="off",
    )


def _read_mode() -> str:
    return _safe_token(
        str(getattr(settings, "CLASSHUB_TELEMETRY_READ_MODE", "core") or "core"),
        fallback="core",
    )


def _counter_key(name: str, *, target: str | None = None) -> str:
    if target:
        return f"{_COUNTER_PREFIX}:{target}:{name}"
    return f"{_COUNTER_PREFIX}:total:{name}"


def _cache_increment(key: str) -> int:
    try:
        current = cache.get(key)
    except Exception as exc:
        logger.warning("telemetry_split_counter_failed op=get key=%s error=%s", key, exc.__class__.__name__)
        return -1

    if current is None:
        try:
            cache.set(key, 1, timeout=_COUNTER_TTL_SECONDS)
            return 1
        except Exception as exc:
            logger.warning("telemetry_split_counter_failed op=set key=%s error=%s", key, exc.__class__.__name__)
            return -1

    try:
        return int(cache.incr(key))
    except Exception as exc:
        logger.warning("telemetry_split_counter_failed op=incr key=%s error=%s", key, exc.__class__.__name__)
        try:
            value = int(current) + 1
            cache.set(key, value, timeout=_COUNTER_TTL_SECONDS)
            return value
        except Exception:
            return -1


def _counter_value(name: str, *, target: str | None = None) -> int:
    try:
        value = cache.get(_counter_key(name, target=target))
    except Exception:
        return 0
    if value is None:
        return 0
    try:
        return int(value)
    except Exception:
        return 0


def _record(status: str, *, source: str, target: str, error: str = "") -> None:
    counter_name = {
        "attempt": "attempts",
        "success": "successes",
        "failure": "failures",
    }.get(status)
    if counter_name is None:
        return

    source_token = _safe_token(source, fallback="unknown")
    target_token = _safe_token(target, fallback="unknown")
    _cache_increment(_counter_key(counter_name))
    _cache_increment(_counter_key(counter_name, target=target_token))

    fields: dict[str, Any] = {
        "status": status,
        "source": source_token,
        "target": target_token,
        "write_mode": _write_mode(),
        "read_mode": _read_mode(),
        "attempts_total": _counter_value("attempts"),
        "successes_total": _counter_value("successes"),
        "failures_total": _counter_value("failures"),
    }
    if error:
        fields["error"] = _safe_token(error, fallback="error")

    message = (
        "telemetry_split_write "
        + " ".join(f"{key}={value}" for key, value in fields.items())
    )
    if status == "failure":
        logger.warning(message)
    elif fields["write_mode"] != "off" or fields["read_mode"] != "core":
        logger.info(message)
    else:
        logger.debug(message)


def record_dual_write_attempt(*, source: str, target: str) -> None:
    _record("attempt", source=source, target=target)


def record_dual_write_success(*, source: str, target: str) -> None:
    _record("success", source=source, target=target)


def record_dual_write_failure(*, source: str, target: str, error: str = "") -> None:
    _record("failure", source=source, target=target, error=error)


def dual_write_counters(*, target: str | None = None) -> dict[str, int]:
    target_token = _safe_token(target, fallback="") if target else None
    return {name: _counter_value(name, target=target_token) for name in _COUNTER_NAMES}


def reset_dual_write_counters() -> None:
    keys: list[str] = []
    for name in _COUNTER_NAMES:
        keys.extend(
            [
                _counter_key(name),
                _counter_key(name, target="core"),
                _counter_key(name, target="telemetry"),
            ]
        )
    cache.delete_many(keys)


__all__ = [
    "dual_write_counters",
    "record_dual_write_attempt",
    "record_dual_write_failure",
    "record_dual_write_success",
    "reset_dual_write_counters",
]
