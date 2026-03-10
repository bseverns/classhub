"""Classroom submission quota helpers with cache-backed byte accounting."""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _cache_key(*, classroom_id: int) -> str:
    return f"classhub:submission_quota:class:{int(classroom_id)}:bytes"


def _cache_ttl_seconds() -> int:
    try:
        ttl = int(getattr(settings, "CLASSHUB_CLASSROOM_QUOTA_CACHE_TTL_SECONDS", 300) or 300)
    except Exception:
        ttl = 300
    return max(ttl, 1)


def _scan_classroom_submission_bytes(*, classroom_id: int) -> int:
    class_dir = Path(settings.MEDIA_ROOT) / "submissions" / f"class_{int(classroom_id)}"
    if not class_dir.exists():
        return 0
    total_bytes = 0
    for path in class_dir.rglob("*"):
        try:
            if path.is_file():
                total_bytes += int(path.stat().st_size)
        except Exception:
            logger.warning(
                "submission_quota_scan_path_error classroom_id=%s path=%s",
                classroom_id,
                path,
            )
    return int(total_bytes)


def _cache_get(key: str):
    try:
        return cache.get(key)
    except Exception:
        logger.warning("submission_quota_cache_get_error key=%s", key, exc_info=True)
        return None


def _cache_set(key: str, value: int, *, timeout: int) -> None:
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning("submission_quota_cache_set_error key=%s", key, exc_info=True)


def _cache_delete(key: str) -> None:
    try:
        cache.delete(key)
    except Exception:
        logger.warning("submission_quota_cache_delete_error key=%s", key, exc_info=True)


def get_classroom_submission_bytes(*, classroom_id: int) -> int:
    """Return total bytes stored for class submissions.

    Uses a short-lived cache to avoid repeated full directory scans during upload bursts.
    """
    key = _cache_key(classroom_id=classroom_id)
    cached = _cache_get(key)
    if cached is not None:
        try:
            return max(int(cached), 0)
        except Exception:
            pass

    try:
        total_bytes = _scan_classroom_submission_bytes(classroom_id=classroom_id)
    except Exception:
        logger.warning(
            "submission_quota_scan_error classroom_id=%s",
            classroom_id,
            exc_info=True,
        )
        return 0
    _cache_set(key, total_bytes, timeout=_cache_ttl_seconds())
    return total_bytes


def bump_cached_classroom_submission_bytes(*, classroom_id: int, delta_bytes: int) -> None:
    """Bump cached class quota usage after a successful upload.

    This only mutates the cache when a value already exists, so cold caches still
    derive their baseline from filesystem scan on first read.
    """
    try:
        delta = int(delta_bytes or 0)
    except Exception:
        delta = 0
    if delta <= 0:
        return

    key = _cache_key(classroom_id=classroom_id)
    cached = _cache_get(key)
    if cached is None:
        return
    try:
        current = max(int(cached), 0)
    except Exception:
        return
    _cache_set(key, current + delta, timeout=_cache_ttl_seconds())


def invalidate_classroom_submission_quota_cache(*, classroom_id: int) -> None:
    _cache_delete(_cache_key(classroom_id=classroom_id))


__all__ = [
    "bump_cached_classroom_submission_bytes",
    "get_classroom_submission_bytes",
    "invalidate_classroom_submission_quota_cache",
]
