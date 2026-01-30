import time
import uuid

from django.core.cache import cache


def acquire_slot(max_concurrency: int, max_wait_seconds: float, poll_seconds: float, ttl_seconds: int):
    """Acquire a queue slot using cache-backed locks.

    Returns (slot_key, token) or (None, None) on timeout.
    """
    if max_concurrency <= 0:
        return None, None

    deadline = time.monotonic() + max_wait_seconds
    token = uuid.uuid4().hex

    while True:
        for idx in range(max_concurrency):
            key = f"helper:slot:{idx}"
            if cache.add(key, token, timeout=ttl_seconds):
                return key, token
        if time.monotonic() >= deadline:
            return None, None
        time.sleep(poll_seconds)


def release_slot(slot_key: str | None, token: str | None):
    if not slot_key or not token:
        return
    try:
        current = cache.get(slot_key)
        if current == token:
            cache.delete(slot_key)
    except Exception:
        # Best-effort release; TTL will eventually clear the slot.
        return
