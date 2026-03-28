"""Factory and helper functions for provider-backed helper inference."""

from __future__ import annotations

import json
import logging
from typing import Callable
from urllib.parse import urlsplit

from ..engine.config_source import helper_getenv
from ..engine.runtime import env_bool, env_float, env_int, redact
from .base import LLMBackendConfig, LLMHealthStatus, LLMRequest, LLMResponse
from .providers import FallbackProvider, OllamaProvider, OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_LOCAL_HOSTS = {"", "127.0.0.1", "localhost", "ollama", "classhub_ollama"}
_BACKEND_ALIASES = {
    "ollama": "ollama",
    "openai": "openai_responses",
    "openai_responses": "openai_responses",
    "openai_compatible": "openai_compatible",
    "remote_openai_compatible": "openai_compatible",
    "mock": "mock",
}


def resolve_backend_name(*, getenv: Callable[[str, str], str] = helper_getenv) -> str:
    raw = (
        getenv("LLM_BACKEND", "")
        or getenv("HELPER_LLM_BACKEND", "ollama")
        or "ollama"
    ).strip().lower()
    return _BACKEND_ALIASES.get(raw, raw or "ollama")


def resolve_backend_runtime_config(
    provider_name: str | None = None,
    *,
    getenv: Callable[[str, str], str] = helper_getenv,
) -> LLMBackendConfig:
    provider = _BACKEND_ALIASES.get(
        (provider_name or resolve_backend_name(getenv=getenv) or "").strip().lower(),
        (provider_name or resolve_backend_name(getenv=getenv) or "ollama").strip().lower(),
    )
    enabled = env_bool("LLM_ENABLED", True, getenv=getenv)
    base_url = ""
    api_key = None
    model = ""
    timeout_seconds = max(env_int("LLM_TIMEOUT_SECONDS", 30, getenv=getenv), 1)
    max_tokens = max(env_int("LLM_MAX_TOKENS", 0, getenv=getenv), 0)
    num_ctx = max(env_int("LLM_NUM_CTX", 0, getenv=getenv), 0)
    temperature = max(env_float("LLM_TEMPERATURE", 0.2, getenv=getenv), 0.0)
    top_p = max(env_float("LLM_TOP_P", 0.9, getenv=getenv), 0.0)

    if provider == "ollama":
        base_url = (getenv("LLM_BASE_URL", "") or getenv("OLLAMA_BASE_URL", "http://ollama:11434")).strip()
        api_key = (getenv("LLM_API_KEY", "") or getenv("OLLAMA_API_KEY", "")).strip() or None
        model = (getenv("LLM_MODEL", "") or getenv("OLLAMA_MODEL", "llama3.2:1b")).strip()
        timeout_seconds = max(
            env_int("LLM_TIMEOUT_SECONDS", env_int("OLLAMA_TIMEOUT_SECONDS", 30, getenv=getenv), getenv=getenv),
            1,
        )
        max_tokens = max(
            env_int("LLM_MAX_TOKENS", env_int("OLLAMA_NUM_PREDICT", 0, getenv=getenv), getenv=getenv),
            0,
        )
        num_ctx = max(
            env_int("LLM_NUM_CTX", env_int("OLLAMA_NUM_CTX", 0, getenv=getenv), getenv=getenv),
            0,
        )
        temperature = max(
            env_float("LLM_TEMPERATURE", env_float("OLLAMA_TEMPERATURE", 0.2, getenv=getenv), getenv=getenv),
            0.0,
        )
        top_p = max(
            env_float("LLM_TOP_P", env_float("OLLAMA_TOP_P", 0.9, getenv=getenv), getenv=getenv),
            0.0,
        )
    elif provider == "openai_compatible":
        base_url = (getenv("LLM_BASE_URL", "") or "").strip()
        api_key = (getenv("LLM_API_KEY", "") or "").strip() or None
        model = (getenv("LLM_MODEL", "") or "").strip()
    elif provider == "openai_responses":
        model = (getenv("OPENAI_MODEL", "gpt-5.2") or "gpt-5.2").strip()
    elif provider == "mock":
        model = "mock"

    return LLMBackendConfig(
        provider=provider,
        enabled=enabled,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
        temperature=temperature,
        top_p=top_p,
        log_prompt_content=env_bool("LLM_LOG_PROMPT_CONTENT", False, getenv=getenv),
        redaction_enabled=env_bool("LLM_REDACTION_ENABLED", True, getenv=getenv),
        healthcheck_enabled=env_bool("LLM_HEALTHCHECK_ENABLED", True, getenv=getenv),
    )


def build_provider(
    provider_name: str | None = None,
    *,
    getenv: Callable[[str, str], str] = helper_getenv,
):
    config = resolve_backend_runtime_config(provider_name, getenv=getenv)
    if config.provider == "ollama":
        return OllamaProvider(config)
    if config.provider == "openai_compatible":
        return OpenAICompatibleProvider(config)
    if config.provider == "mock":
        return FallbackProvider(config, text=(getenv("HELPER_MOCK_RESPONSE_TEXT", "") or "").strip())
    raise RuntimeError("unknown_backend")


def backend_requires_acknowledgement(
    provider_name: str | None = None,
    *,
    getenv: Callable[[str, str], str] = helper_getenv,
) -> bool:
    config = resolve_backend_runtime_config(provider_name, getenv=getenv)
    if config.provider == "mock":
        return False
    if config.provider == "openai_responses":
        return True
    if config.provider == "openai_compatible":
        return True
    if config.provider != "ollama":
        return False
    host = (urlsplit(config.base_url).hostname or "").strip().lower()
    return host not in _LOCAL_HOSTS


def describe_backend(
    provider_name: str | None = None,
    *,
    getenv: Callable[[str, str], str] = helper_getenv,
) -> dict[str, object]:
    config = resolve_backend_runtime_config(provider_name, getenv=getenv)
    return {
        "provider": config.provider,
        "enabled": config.enabled,
        "model": config.model,
        "base_url": config.base_url,
        "remote_private": backend_requires_acknowledgement(config.provider, getenv=getenv),
        "healthcheck_enabled": config.healthcheck_enabled,
    }


def chat_with_provider(
    provider_name: str,
    *,
    instructions: str,
    message: str,
    request_id: str = "",
    metadata: dict[str, object] | None = None,
    redact_fn: Callable[[str], str] = redact,
    getenv: Callable[[str, str], str] = helper_getenv,
) -> LLMResponse:
    provider = build_provider(provider_name, getenv=getenv)
    config = provider.config
    outbound_message = str(message or "")
    if config.redaction_enabled:
        outbound_message = redact_fn(outbound_message)
    prompt_log = {
        "event": "llm_provider_request",
        "provider": config.provider,
        "request_id": request_id,
        "model": config.model,
        "message_chars": len(outbound_message),
        "instructions_chars": len(str(instructions or "")),
        "metadata": metadata or {},
    }
    if config.log_prompt_content:
        prompt_log["message_preview"] = outbound_message[:300]
    logger.info(json.dumps(prompt_log, sort_keys=True, default=str))
    response = provider.chat(
        LLMRequest(
            instructions=str(instructions or ""),
            message=outbound_message,
            request_id=request_id,
            metadata=metadata or {},
        )
    )
    logger.info(
        json.dumps(
            {
                "event": "llm_provider_response",
                "provider": config.provider,
                "request_id": request_id,
                "model": response.model,
                "response_chars": len(response.text or ""),
            },
            sort_keys=True,
            default=str,
        )
    )
    return response


def healthcheck_provider(
    provider_name: str | None = None,
    *,
    probe_chat: bool = False,
    request_id: str = "healthcheck",
    getenv: Callable[[str, str], str] = helper_getenv,
) -> LLMHealthStatus:
    provider = build_provider(provider_name, getenv=getenv)
    if not provider.config.enabled:
        return LLMHealthStatus(
            ok=False,
            provider=provider.config.provider,
            model=provider.config.model,
            detail="llm_disabled",
        )
    if not provider.config.healthcheck_enabled:
        return LLMHealthStatus(
            ok=True,
            provider=provider.config.provider,
            model=provider.config.model,
            detail="healthcheck_disabled",
        )
    status = provider.healthcheck()
    if probe_chat and status.ok:
        probe_response = chat_with_provider(
            provider.config.provider,
            instructions="Reply with exactly: ok",
            message="Health probe",
            request_id=request_id,
            metadata={"probe": "chat"},
            getenv=getenv,
        )
        return LLMHealthStatus(
            ok=True,
            provider=status.provider,
            model=probe_response.model or status.model,
            detail="chat_probe_ok",
            metadata={"response_preview": (probe_response.text or "")[:40]},
        )
    return status
