"""Execution-time configuration for helper request handling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ExecutionConfig:
    backend: str
    scope_token_max_age_seconds: int
    conversation_enabled: bool
    conversation_max_messages: int
    conversation_ttl_seconds: int
    conversation_turn_max_chars: int
    conversation_history_max_chars: int
    conversation_summary_max_chars: int
    follow_up_suggestions_max: int
    reference_dir: str
    reference_map_raw: str
    default_reference_file: str
    reference_max_citations: int
    text_language_keywords: list[str]
    piper_hardware_triage_enabled: bool
    queue_max_concurrency: int
    queue_max_wait_seconds: float
    queue_poll_seconds: float
    queue_slot_ttl_seconds: int


def resolve_execution_config(
    *,
    env_int: Callable[[str, int], int],
    env_float: Callable[[str, float], float],
    env_bool: Callable[[str, bool], bool],
    parse_csv_list: Callable[[str], list[str]],
    default_text_language_keywords: list[str],
    getenv: Callable[[str, str], str] = os.getenv,
) -> ExecutionConfig:
    backend = (getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()
    text_language_keywords = parse_csv_list(getenv("HELPER_TEXT_LANGUAGE_KEYWORDS", ""))
    if not text_language_keywords:
        text_language_keywords = list(default_text_language_keywords or [])

    return ExecutionConfig(
        backend=backend,
        scope_token_max_age_seconds=max(env_int("HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS", 7200), 60),
        conversation_enabled=env_bool("HELPER_CONVERSATION_ENABLED", True),
        conversation_max_messages=max(env_int("HELPER_CONVERSATION_MAX_MESSAGES", 8), 0),
        conversation_ttl_seconds=max(env_int("HELPER_CONVERSATION_TTL_SECONDS", 3600), 60),
        conversation_turn_max_chars=max(env_int("HELPER_CONVERSATION_TURN_MAX_CHARS", 800), 80),
        conversation_history_max_chars=max(env_int("HELPER_CONVERSATION_HISTORY_MAX_CHARS", 2400), 300),
        conversation_summary_max_chars=max(env_int("HELPER_CONVERSATION_SUMMARY_MAX_CHARS", 900), 200),
        follow_up_suggestions_max=max(env_int("HELPER_FOLLOW_UP_SUGGESTIONS_MAX", 3), 1),
        reference_dir=(getenv("HELPER_REFERENCE_DIR", "/app/tutor/reference") or "/app/tutor/reference").strip(),
        reference_map_raw=(getenv("HELPER_REFERENCE_MAP", "") or "").strip(),
        default_reference_file=(getenv("HELPER_REFERENCE_FILE", "") or "").strip(),
        reference_max_citations=max(env_int("HELPER_REFERENCE_MAX_CITATIONS", 3), 1),
        text_language_keywords=text_language_keywords,
        piper_hardware_triage_enabled=env_bool("HELPER_PIPER_HARDWARE_TRIAGE_ENABLED", True),
        queue_max_concurrency=env_int("HELPER_MAX_CONCURRENCY", 2),
        queue_max_wait_seconds=env_float("HELPER_QUEUE_MAX_WAIT_SECONDS", 10.0),
        queue_poll_seconds=env_float("HELPER_QUEUE_POLL_SECONDS", 0.2),
        queue_slot_ttl_seconds=env_int("HELPER_QUEUE_SLOT_TTL_SECONDS", 120),
    )


__all__ = ["ExecutionConfig", "resolve_execution_config"]
