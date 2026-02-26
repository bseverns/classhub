import json
import logging
import os
import re
from functools import lru_cache

from django.core.cache import cache
from django.http import JsonResponse

from .engine import heuristics as engine_heuristics
from .engine import memory as engine_memory
from .engine import reference as engine_reference
from .engine import runtime as engine_runtime


DEFAULT_TEXT_LANGUAGE_KEYWORDS = engine_heuristics.DEFAULT_TEXT_LANGUAGE_KEYWORDS
DEFAULT_PIPER_CONTEXT_KEYWORDS = engine_heuristics.DEFAULT_PIPER_CONTEXT_KEYWORDS
DEFAULT_PIPER_HARDWARE_KEYWORDS = engine_heuristics.DEFAULT_PIPER_HARDWARE_KEYWORDS
_SAFE_TOKEN_RE = re.compile(r"^[a-z0-9_-]+$")
logger = logging.getLogger(__name__)


def _redact(text: str) -> str:
    """Apply lightweight redaction before model invocation/logging."""
    return engine_runtime.redact(text)


def _env_int(name: str, default: int) -> int:
    return engine_runtime.env_int(name, default, getenv=os.getenv)


def _env_float(name: str, default: float) -> float:
    return engine_runtime.env_float(name, default, getenv=os.getenv)


def _env_bool(name: str, default: bool) -> bool:
    return engine_runtime.env_bool(name, default, getenv=os.getenv)


def _request_id(request) -> str:
    return engine_runtime.request_id(request)


def _json_response(payload: dict, *, request_id: str, status: int = 200) -> JsonResponse:
    return engine_runtime.json_response(payload, request_id_value=request_id, status=status)


def _log_chat_event(level: str, event: str, *, request_id: str, **fields):
    engine_runtime.log_chat_event(
        level,
        event,
        request_id_value=request_id,
        logger=logger,
        **fields,
    )


def _truncate_response_text(text: str) -> tuple[str, bool]:
    return engine_heuristics.truncate_response_text(
        text,
        max_chars=_env_int("HELPER_RESPONSE_MAX_CHARS", 2200),
    )


def _is_piper_context(context_value: str, topics: list[str], reference_text: str, reference_key: str = "") -> bool:
    context_keywords = engine_heuristics.parse_csv_list(os.getenv("HELPER_PIPER_CONTEXT_KEYWORDS", ""))
    keywords = context_keywords or DEFAULT_PIPER_CONTEXT_KEYWORDS
    return engine_heuristics.is_piper_context(
        context_value,
        topics,
        reference_text,
        reference_key=reference_key,
        keywords=keywords,
    )


def _is_piper_hardware_question(message: str) -> bool:
    hardware_keywords = engine_heuristics.parse_csv_list(os.getenv("HELPER_PIPER_HARDWARE_KEYWORDS", ""))
    keywords = hardware_keywords or DEFAULT_PIPER_HARDWARE_KEYWORDS
    return engine_heuristics.is_piper_hardware_question(message, keywords=keywords)


def _build_piper_hardware_triage_text(message: str) -> str:
    return engine_heuristics.build_piper_hardware_triage_text(message)


@lru_cache(maxsize=4)
def _load_reference_chunks(path_str: str) -> tuple[str, ...]:
    return engine_reference.load_reference_chunks(path_str, logger=logger)


@lru_cache(maxsize=4)
def _load_reference_text(path_str: str) -> str:
    return engine_reference.load_reference_text(path_str, logger=logger)


def _normalize_conversation_id(raw: str) -> str:
    return engine_memory.normalize_conversation_id(raw)


def _conversation_scope_fingerprint(scope_token: str) -> str:
    return engine_memory.scope_fingerprint(scope_token)


def _load_conversation_state(*, conversation_id: str, actor_key: str, scope_fingerprint: str, max_messages: int) -> dict:
    key = engine_memory.conversation_cache_key(
        actor_key=actor_key,
        scope_fp=scope_fingerprint,
        conversation_id=conversation_id,
    )
    return engine_memory.load_state(
        cache_backend=cache,
        key=key,
        max_messages=max_messages,
    )


def _save_conversation_state(
    *,
    conversation_id: str,
    actor_key: str,
    scope_fingerprint: str,
    turns: list[dict],
    summary: str,
    ttl_seconds: int,
) -> None:
    key = engine_memory.conversation_cache_key(
        actor_key=actor_key,
        scope_fp=scope_fingerprint,
        conversation_id=conversation_id,
    )
    engine_memory.save_state(
        cache_backend=cache,
        key=key,
        turns=turns,
        summary=summary,
        ttl_seconds=ttl_seconds,
        actor_key=actor_key,
    )


def _clear_conversation_turns(*, conversation_id: str, actor_key: str, scope_fingerprint: str) -> None:
    key = engine_memory.conversation_cache_key(
        actor_key=actor_key,
        scope_fp=scope_fingerprint,
        conversation_id=conversation_id,
    )
    engine_memory.clear_turns(
        cache_backend=cache,
        key=key,
    )


def _format_conversation_for_prompt(turns: list[dict], *, max_chars: int, summary: str = "") -> str:
    return engine_memory.format_turns_for_prompt(turns=turns, max_chars=max_chars, summary=summary)


def _compact_conversation(*, turns: list[dict], max_messages: int, summary: str, summary_max_chars: int) -> tuple[str, list[dict], bool]:
    return engine_memory.compact_turns(
        turns=turns,
        max_messages=max_messages,
        summary=summary,
        summary_max_chars=summary_max_chars,
    )


def _classify_intent(message: str) -> str:
    return engine_heuristics.classify_intent(message)


def _build_follow_up_suggestions(
    *,
    intent: str,
    context: str,
    topics: list[str],
    allowed_topics: list[str],
    history_summary: str = "",
    max_items: int = 3,
) -> list[str]:
    return engine_heuristics.build_follow_up_suggestions(
        intent=intent,
        context=context,
        topics=topics,
        allowed_topics=allowed_topics,
        history_summary=history_summary,
        max_items=max_items,
    )


def _build_helper_event_details(*, response, request_id: str, actor_type: str, backend: str) -> dict:
    details: dict = {
        "request_id": request_id,
        "actor_type": actor_type,
    }
    backend_token = str(backend or "").strip().lower()
    if backend_token and _SAFE_TOKEN_RE.fullmatch(backend_token):
        details["backend"] = backend_token

    try:
        payload = json.loads(response.content.decode("utf-8"))
    except Exception:
        return details
    if not isinstance(payload, dict):
        return details

    backend_value = str(payload.get("backend") or "").strip().lower()
    if backend_value and _SAFE_TOKEN_RE.fullmatch(backend_value):
        details["backend"] = backend_value

    intent = str(payload.get("intent") or "").strip().lower()
    if intent and _SAFE_TOKEN_RE.fullmatch(intent):
        details["intent"] = intent

    if "scope_verified" in payload:
        details["scope_verified"] = bool(payload.get("scope_verified"))
    if "truncated" in payload:
        details["truncated"] = bool(payload.get("truncated"))
    if "conversation_compacted" in payload:
        details["conversation_compacted"] = bool(payload.get("conversation_compacted"))

    attempts_raw = payload.get("attempts")
    try:
        attempts = int(attempts_raw)
    except Exception:
        attempts = None
    if attempts is not None and attempts >= 0:
        details["attempts"] = attempts

    follow_up_suggestions = payload.get("follow_up_suggestions")
    if isinstance(follow_up_suggestions, list):
        valid_suggestions = [row for row in follow_up_suggestions if str(row or "").strip()]
        details["follow_up_suggestions_count"] = len(valid_suggestions)

    return details


__all__ = [
    "DEFAULT_PIPER_CONTEXT_KEYWORDS",
    "DEFAULT_PIPER_HARDWARE_KEYWORDS",
    "DEFAULT_TEXT_LANGUAGE_KEYWORDS",
    "_build_follow_up_suggestions",
    "_build_helper_event_details",
    "_build_piper_hardware_triage_text",
    "_classify_intent",
    "_clear_conversation_turns",
    "_compact_conversation",
    "_conversation_scope_fingerprint",
    "_env_bool",
    "_env_float",
    "_env_int",
    "_format_conversation_for_prompt",
    "_is_piper_context",
    "_is_piper_hardware_question",
    "_json_response",
    "_load_conversation_state",
    "_load_reference_chunks",
    "_load_reference_text",
    "_log_chat_event",
    "_normalize_conversation_id",
    "_redact",
    "_request_id",
    "_save_conversation_state",
    "_truncate_response_text",
]
