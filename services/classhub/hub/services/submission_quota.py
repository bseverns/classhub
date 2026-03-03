"""Classroom submission quota helpers with cache-backed byte accounting."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.cache import cache


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
    return int(sum(path.stat().st_size for path in class_dir.rglob("*") if path.is_file()))


def get_classroom_submission_bytes(*, classroom_id: int) -> int:
    """Return total bytes stored for class submissions.

    Uses a short-lived cache to avoid repeated full directory scans during upload bursts.
    """
    key = _cache_key(classroom_id=classroom_id)
    cached = cache.get(key)
    if cached is not None:
        try:
            return max(int(cached), 0)
        except Exception:
            pass

    total_bytes = _scan_classroom_submission_bytes(classroom_id=classroom_id)
    cache.set(key, total_bytes, timeout=_cache_ttl_seconds())
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
    cached = cache.get(key)
    if cached is None:
        return
    try:
        current = max(int(cached), 0)
    except Exception:
        return
    cache.set(key, current + delta, timeout=_cache_ttl_seconds())


def invalidate_classroom_submission_quota_cache(*, classroom_id: int) -> None:
    cache.delete(_cache_key(classroom_id=classroom_id))


__all__ = [
    "bump_cached_classroom_submission_bytes",
    "get_classroom_submission_bytes",
    "invalidate_classroom_submission_quota_cache",
]

