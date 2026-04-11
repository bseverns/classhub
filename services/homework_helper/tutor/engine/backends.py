"""Backend interface + retry helpers for helper chat execution."""

from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from .config_source import helper_config_overrides
from ..llm import (
    LLMAuthError,
    LLMBackendConfig,
    LLMConfigError,
    LLMMalformedResponseError,
    LLMRequest,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
    chat_with_provider,
)
from ..llm.providers import OllamaProvider

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
    if isinstance(exc, (LLMTimeoutError, LLMUpstreamUnavailableError)):
        return True
    if isinstance(exc, (LLMAuthError, LLMConfigError, LLMMalformedResponseError)):
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
    num_ctx: int,
    num_predict: int,
) -> tuple[str, str]:
    """Execute a non-streaming Ollama chat completion and return `(text, model_used)`."""
    provider = OllamaProvider(
        LLMBackendConfig(
            provider="ollama",
            enabled=True,
            base_url=base_url,
            api_key=None,
            model=model,
            timeout_seconds=max(int(timeout_seconds), 1),
            max_tokens=max(int(num_predict), 0),
            num_ctx=max(int(num_ctx), 0),
            temperature=float(temperature),
            top_p=float(top_p),
            log_prompt_content=False,
            redaction_enabled=True,
            healthcheck_enabled=True,
        )
    )
    response = provider.chat(LLMRequest(instructions=instructions, message=message))
    return response.text, response.model


def openai_compatible_chat(
    *,
    instructions: str,
    message: str,
) -> tuple[str, str]:
    response = chat_with_provider(
        "openai_compatible",
        instructions=instructions,
        message=message,
    )
    return response.text, response.model


def openai_chat(
    *,
    api_key: str | None,
    model: str,
    instructions: str,
    message: str,
    max_output_tokens: int,
) -> tuple[str, str]:
    """Execute an OpenAI Responses API request via the shared provider layer."""
    overrides = {
        "OPENAI_MODEL": model,
        "OPENAI_API_KEY": str(api_key or ""),
        "OPENAI_MAX_OUTPUT_TOKENS": str(max_output_tokens),
    }
    with helper_config_overrides(overrides):
        response = chat_with_provider(
            "openai_responses",
            instructions=instructions,
            message=message,
        )
    return response.text, response.model


def mock_chat(*, text: str) -> tuple[str, str]:
    """Return deterministic mock backend output for tests/local smoke."""
    normalized = (text or "").strip()
    if not normalized:
        normalized = "Let's solve this step by step. What did you try already?"
    return normalized, "mock-tutor-v1"
