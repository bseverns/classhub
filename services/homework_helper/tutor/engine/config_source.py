"""Optional YAML-backed config source for helper runtime settings.

Precedence:
1) Explicit environment variable value (existing behavior)
2) Value from HELPER_CONFIG_FILE (YAML)
3) Caller-provided default
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - dependency is provided in runtime images
    yaml = None


ENV_TO_YAML_PATH = {
    "LLM_ENABLED": ("backend", "enabled"),
    "LLM_ALLOWED_ACTOR_TYPES": ("backend", "allowed_actor_types"),
    "LLM_BACKEND": ("backend", "name"),
    "HELPER_LLM_BACKEND": ("backend", "name"),
    "HELPER_MOCK_RESPONSE_TEXT": ("backend", "mock_response_text"),
    "OLLAMA_BASE_URL": ("backend", "ollama", "base_url"),
    "OLLAMA_MODEL": ("backend", "ollama", "model"),
    "OLLAMA_TIMEOUT_SECONDS": ("backend", "ollama", "timeout_seconds"),
    "OLLAMA_TEMPERATURE": ("backend", "ollama", "temperature"),
    "OLLAMA_TOP_P": ("backend", "ollama", "top_p"),
    "OLLAMA_NUM_CTX": ("backend", "ollama", "num_ctx"),
    "OLLAMA_NUM_PREDICT": ("backend", "ollama", "num_predict"),
    "LLM_NUM_CTX": ("backend", "ollama", "num_ctx"),
    "OPENAI_MODEL": ("backend", "openai", "model"),
    "OPENAI_MAX_OUTPUT_TOKENS": ("backend", "openai", "max_output_tokens"),
    "HELPER_STRICTNESS": ("policy", "strictness"),
    "HELPER_SCOPE_MODE": ("policy", "scope_mode"),
    "HELPER_TOPIC_FILTER_MODE": ("policy", "topic_filter_mode"),
    "HELPER_RATE_LIMIT_PER_MINUTE": ("rate_limits", "actor_per_minute"),
    "HELPER_RATE_LIMIT_PER_IP_PER_MINUTE": ("rate_limits", "ip_per_minute"),
    "HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS": ("security", "scope_token_max_age_seconds"),
    "HELPER_RESPONSE_MAX_CHARS": ("response", "max_chars"),
    "HELPER_FOLLOW_UP_SUGGESTIONS_MAX": ("response", "follow_up_suggestions_max"),
    "HELPER_TEXT_LANGUAGE_KEYWORDS": ("heuristics", "text_language_keywords"),
    "HELPER_PIPER_CONTEXT_KEYWORDS": ("heuristics", "piper_context_keywords"),
    "HELPER_PIPER_HARDWARE_KEYWORDS": ("heuristics", "piper_hardware_keywords"),
    "HELPER_PIPER_HARDWARE_TRIAGE_ENABLED": ("heuristics", "piper_hardware_triage_enabled"),
    "HELPER_CONVERSATION_ENABLED": ("conversation", "enabled"),
    "HELPER_CONVERSATION_MAX_MESSAGES": ("conversation", "max_messages"),
    "HELPER_CONVERSATION_TTL_SECONDS": ("conversation", "ttl_seconds"),
    "HELPER_CONVERSATION_TURN_MAX_CHARS": ("conversation", "turn_max_chars"),
    "HELPER_CONVERSATION_HISTORY_MAX_CHARS": ("conversation", "history_max_chars"),
    "HELPER_CONVERSATION_SUMMARY_MAX_CHARS": ("conversation", "summary_max_chars"),
    "HELPER_REFERENCE_DIR": ("references", "directory"),
    "HELPER_REFERENCE_MAP": ("references", "map"),
    "HELPER_REFERENCE_FILE": ("references", "default_file"),
    "HELPER_REFERENCE_MAX_CITATIONS": ("references", "max_citations"),
    "HELPER_RAG_ENABLED": ("rag", "enabled"),
    "HELPER_RAG_EMBED_BASE_URL": ("rag", "embed_base_url"),
    "HELPER_RAG_EMBED_MODEL": ("rag", "embed_model"),
    "HELPER_RAG_EMBED_TIMEOUT_SECONDS": ("rag", "embed_timeout_seconds"),
    "HELPER_RAG_EMBED_DIMENSIONS": ("rag", "embed_dimensions"),
    "HELPER_RAG_MAX_COSINE_DISTANCE": ("rag", "max_cosine_distance"),
    "HELPER_MAX_CONCURRENCY": ("queue", "max_concurrency"),
    "HELPER_QUEUE_MAX_WAIT_SECONDS": ("queue", "max_wait_seconds"),
    "HELPER_QUEUE_POLL_SECONDS": ("queue", "poll_seconds"),
    "HELPER_QUEUE_SLOT_TTL_SECONDS": ("queue", "slot_ttl_seconds"),
    "HELPER_BACKEND_MAX_ATTEMPTS": ("resilience", "backend_max_attempts"),
    "HELPER_BACKOFF_SECONDS": ("resilience", "backoff_seconds"),
    "HELPER_CIRCUIT_BREAKER_FAILURES": ("resilience", "circuit_breaker_failures"),
    "HELPER_CIRCUIT_BREAKER_TTL_SECONDS": ("resilience", "circuit_breaker_ttl_seconds"),
    "HELPER_CLASS_RESET_MAX_KEYS": ("reset_archives", "max_keys"),
    "HELPER_CLASS_RESET_ARCHIVE_ENABLED": ("reset_archives", "enabled"),
    "HELPER_CLASS_RESET_ARCHIVE_DIR": ("reset_archives", "directory"),
    "HELPER_CLASS_RESET_ARCHIVE_MAX_MESSAGES": ("reset_archives", "max_messages"),
}

ENV_ALIASES = {
    "HELPER_LLM_BACKEND": ("LLM_BACKEND",),
    "OLLAMA_BASE_URL": ("LLM_BASE_URL",),
    "OLLAMA_API_KEY": ("LLM_API_KEY",),
    "OLLAMA_MODEL": ("LLM_MODEL",),
    "OLLAMA_TIMEOUT_SECONDS": ("LLM_TIMEOUT_SECONDS",),
    "OLLAMA_TEMPERATURE": ("LLM_TEMPERATURE",),
    "OLLAMA_TOP_P": ("LLM_TOP_P",),
    "OLLAMA_NUM_PREDICT": ("LLM_MAX_TOKENS",),
    "OLLAMA_NUM_CTX": ("LLM_NUM_CTX",),
    "OPENAI_MODEL": ("LLM_MODEL",),
    "OPENAI_MAX_OUTPUT_TOKENS": ("LLM_MAX_TOKENS",),
}


def helper_getenv(name: str, default: str = "") -> str:
    """Return config value for a helper setting with env-first precedence."""
    explicit = os.getenv(name)
    if explicit not in (None, ""):
        return explicit

    for alias in ENV_ALIASES.get(name, ()):
        alias_value = os.getenv(alias)
        if alias_value not in (None, ""):
            return alias_value

    path = ENV_TO_YAML_PATH.get(name)
    if not path:
        return default

    config_file = (os.getenv("HELPER_CONFIG_FILE", "") or "").strip()
    if not config_file:
        return default

    yaml_doc = _load_yaml_config(config_file)
    raw_value = _nested_get(yaml_doc, path)
    rendered = _render_scalar(raw_value)
    if rendered == "":
        return default
    return rendered


@lru_cache(maxsize=8)
def _load_yaml_config(config_file: str) -> dict:
    if yaml is None:
        return {}
    path = Path(config_file)
    if not path.is_file():
        return {}
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _nested_get(source: dict, keys: tuple[str, ...]):
    cursor = source
    for key in keys:
        if not isinstance(cursor, dict):
            return None
        if key not in cursor:
            return None
        cursor = cursor.get(key)
    return cursor


def _render_scalar(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)


def clear_helper_config_cache() -> None:
    _load_yaml_config.cache_clear()


__all__ = [
    "ENV_TO_YAML_PATH",
    "clear_helper_config_cache",
    "helper_getenv",
]
