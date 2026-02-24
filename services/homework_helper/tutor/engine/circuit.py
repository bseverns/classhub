"""Cache-backed backend circuit-breaker primitives."""

from __future__ import annotations


def backend_circuit_key(backend: str) -> str:
    return f"helper:circuit_open:{backend}"


def backend_failure_counter_key(backend: str) -> str:
    return f"helper:circuit_failures:{backend}"


def backend_circuit_is_open(*, cache_backend, backend: str, logger) -> bool:
    try:
        return bool(cache_backend.get(backend_circuit_key(backend)))
    except Exception as exc:
        logger.warning(
            "helper_backend_circuit_check_failed backend=%s error=%s",
            backend,
            exc.__class__.__name__,
        )
        # Fail-open: cache outage should not block helper traffic.
        return False


def record_backend_failure(
    *,
    cache_backend,
    backend: str,
    threshold: int,
    ttl: int,
    logger,
) -> None:
    key = backend_failure_counter_key(backend)
    try:
        current = cache_backend.get(key)
    except Exception as exc:
        logger.warning(
            "helper_backend_circuit_record_failed backend=%s op=get error=%s",
            backend,
            exc.__class__.__name__,
        )
        return

    if current is None:
        try:
            cache_backend.set(key, 1, timeout=ttl)
        except Exception as exc:
            logger.warning(
                "helper_backend_circuit_record_failed backend=%s op=set error=%s",
                backend,
                exc.__class__.__name__,
            )
        count = 1
    else:
        try:
            count = int(cache_backend.incr(key))
        except Exception as exc:
            logger.warning(
                "helper_backend_circuit_record_failed backend=%s op=incr error=%s",
                backend,
                exc.__class__.__name__,
            )
            count = int(current) + 1
            try:
                cache_backend.set(key, count, timeout=ttl)
            except Exception:
                return

    if count >= threshold:
        try:
            cache_backend.set(backend_circuit_key(backend), 1, timeout=ttl)
        except Exception:
            return


def reset_backend_failure_state(*, cache_backend, backend: str, logger) -> None:
    try:
        cache_backend.delete(backend_failure_counter_key(backend))
        cache_backend.delete(backend_circuit_key(backend))
    except Exception as exc:
        logger.warning(
            "helper_backend_circuit_reset_failed backend=%s error=%s",
            backend,
            exc.__class__.__name__,
        )

