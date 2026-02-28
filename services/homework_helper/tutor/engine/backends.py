"""Backend interface + retry helpers for helper chat execution."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
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


def ollama_chat(
    *,
    base_url: str,
    model: str,
    instructions: str,
    message: str,
    timeout_seconds: int,
    temperature: float,
    top_p: float,
    num_predict: int,
) -> tuple[str, str]:
    """Execute a non-streaming Ollama chat completion and return `(text, model_used)`."""
    if not base_url.lower().startswith(("http://", "https://")):
        raise ValueError("Invalid base URL scheme")
    url = base_url.rstrip("/") + "/api/chat"
    options: dict[str, float | int] = {
        "temperature": temperature,
        "top_p": top_p,
    }
    if num_predict > 0:
        options["num_predict"] = num_predict
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": message},
        ],
        "stream": False,
        "options": options,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=int(timeout_seconds)) as resp:  # nosec B310
        body = resp.read().decode("utf-8")
    parsed = json.loads(body)
    text = ""
    if isinstance(parsed, dict):
        msg = parsed.get("message") or {}
        text = msg.get("content") or parsed.get("response") or ""
    return text, parsed.get("model", model) if isinstance(parsed, dict) else model


def openai_chat(
    *,
    api_key: str | None,
    model: str,
    instructions: str,
    message: str,
    max_output_tokens: int,
) -> tuple[str, str]:
    """Execute an OpenAI Responses API request and return `(text, model_used)`."""
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("openai_not_installed") from exc

    client = OpenAI(api_key=api_key)
    create_kwargs = {
        "model": model,
        "instructions": instructions,
        "input": message,
    }
    if max_output_tokens > 0:
        create_kwargs["max_output_tokens"] = max_output_tokens
    response = client.responses.create(**create_kwargs)
    return (getattr(response, "output_text", "") or ""), model


def mock_chat(*, text: str) -> tuple[str, str]:
    """Return deterministic mock backend output for tests/local smoke."""
    normalized = (text or "").strip()
    if not normalized:
        normalized = "Let's solve this step by step. What did you try already?"
    return normalized, "mock-tutor-v1"
