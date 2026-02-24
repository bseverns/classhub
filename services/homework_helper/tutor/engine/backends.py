"""Backend interface + retry helpers for helper chat execution."""

from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol


class BackendInterface(Protocol):
    """Minimal backend contract used by chat runtime."""

    def chat(self, *, instructions: str, message: str) -> tuple[str, str]:
        """Return `(text, model_used)`."""


@dataclass(frozen=True)
class CallableBackend:
    """Adapter for simple function-based backend implementations."""

    chat_fn: Callable[[str, str], tuple[str, str]]

    def chat(self, *, instructions: str, message: str) -> tuple[str, str]:
        return self.chat_fn(instructions, message)


def invoke_backend(
    backend: str,
    *,
    instructions: str,
    message: str,
    registry: Mapping[str, BackendInterface],
) -> tuple[str, str]:
    implementation = registry.get((backend or "").strip().lower())
    if implementation is None:
        raise RuntimeError("unknown_backend")
    return implementation.chat(instructions=instructions, message=message)


def is_retryable_backend_error(exc: Exception) -> bool:
    if isinstance(exc, RuntimeError) and str(exc) in {"openai_not_installed", "unknown_backend"}:
        return False
    if isinstance(exc, (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError)):
        return True
    return exc.__class__.__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
    }


def call_backend_with_retries(
    backend: str,
    *,
    instructions: str,
    message: str,
    invoke_backend_fn: Callable[[str, str, str], tuple[str, str]],
    max_attempts: int,
    base_backoff: float,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[str, str, int]:
    attempts = max(int(max_attempts), 1)
    backoff = max(float(base_backoff), 0.0)
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            text, model_used = invoke_backend_fn(backend, instructions, message)
            return text, model_used, attempt
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or not is_retryable_backend_error(exc):
                raise
            sleep_seconds = backoff * (2 ** (attempt - 1))
            if sleep_seconds > 0:
                sleeper(sleep_seconds)

    raise last_exc or RuntimeError("backend_error")

