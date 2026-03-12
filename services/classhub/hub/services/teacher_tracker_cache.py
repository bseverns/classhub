"""Shared cache helpers for teacher dashboard tracker panels."""

from __future__ import annotations

import hashlib
import logging
from typing import Callable, TypeVar

from django.conf import settings
from django.core.cache import cache


_CACHE_KEY_PREFIX = "classhub:teacher-panel:v1"
_CACHE_KEY_LENGTH = 32
_CacheValue = TypeVar("_CacheValue")
logger = logging.getLogger(__name__)


def _teacher_panel_cache_ttl_seconds() -> int:
    try:
        ttl = int(getattr(settings, "CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS", 0) or 0)
    except Exception:
        ttl = 0
    return max(ttl, 0)


def _panel_signature_digest(parts: list[str]) -> str:
    joined = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:_CACHE_KEY_LENGTH]


def _cache_get_or_build(panel: str, *, key_parts: list[str], builder: Callable[[], _CacheValue]) -> _CacheValue:
    ttl = _teacher_panel_cache_ttl_seconds()
    if ttl <= 0:
        return builder()

    key = f"{_CACHE_KEY_PREFIX}:{panel}:{_panel_signature_digest(key_parts)}"
    try:
        cached = cache.get(key)
    except Exception:
        logger.warning("teacher_panel_cache_get_failed panel=%s", panel)
        return builder()
    if cached is not None:
        return cached

    value = builder()
    try:
        cache.set(key, value, timeout=ttl)
    except Exception:
        logger.warning("teacher_panel_cache_set_failed panel=%s", panel)
    return value


__all__ = ["_cache_get_or_build"]
