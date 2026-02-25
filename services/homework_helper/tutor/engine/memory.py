"""Conversation-memory helpers for helper chat sessions."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid

logger = logging.getLogger(__name__)

_ROLE_LABELS = {
    "student": "Student",
    "assistant": "Tutor",
}
_UUID_HEX_RE = re.compile(r"^[a-f0-9]{32}$")
_ACTOR_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9:_-]")


def normalize_conversation_id(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return uuid.uuid4().hex
    if _UUID_HEX_RE.fullmatch(value):
        return value
    try:
        return uuid.UUID(value).hex
    except Exception:
        pass
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def scope_fingerprint(scope_token: str) -> str:
    token = (scope_token or "").strip()
    if not token:
        return "noscope"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def conversation_cache_key(*, actor_key: str, scope_fp: str, conversation_id: str) -> str:
    actor = _ACTOR_SANITIZE_RE.sub("_", (actor_key or "").strip())[:96] or "unknown"
    scope = (scope_fp or "").strip() or "noscope"
    conv = normalize_conversation_id(conversation_id)
    return f"helper:conversation:{actor}:{scope}:{conv}"


def _coerce_turns(raw) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    turns: list[dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip().lower()
        if role not in _ROLE_LABELS:
            continue
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        turns.append({"role": role, "content": content})
    return turns


def load_turns(*, cache_backend, key: str, max_messages: int) -> list[dict[str, str]]:
    try:
        stored = cache_backend.get(key)
    except Exception:
        logger.warning("conversation_memory_cache_get_failed key=%s", key)
        return []
    if not isinstance(stored, dict):
        return []
    turns = _coerce_turns(stored.get("turns"))
    if max_messages > 0 and len(turns) > max_messages:
        turns = turns[-max_messages:]
    return turns


def save_turns(*, cache_backend, key: str, turns: list[dict[str, str]], ttl_seconds: int) -> None:
    normalized = _coerce_turns(turns)
    payload = {"v": 1, "turns": normalized}
    try:
        cache_backend.set(key, payload, timeout=max(int(ttl_seconds), 60))
    except Exception:
        logger.warning("conversation_memory_cache_set_failed key=%s", key)


def clear_turns(*, cache_backend, key: str) -> None:
    try:
        cache_backend.delete(key)
    except Exception:
        logger.warning("conversation_memory_cache_delete_failed key=%s", key)


def format_turns_for_prompt(*, turns: list[dict[str, str]], max_chars: int) -> str:
    normalized = _coerce_turns(turns)
    if not normalized:
        return ""

    selected: list[str] = []
    used = 0
    for row in reversed(normalized):
        role = _ROLE_LABELS.get(row["role"], "Tutor")
        line = f"{role}: {row['content']}"
        line_len = len(line) + 1
        if max_chars > 0 and selected and used + line_len > max_chars:
            break
        selected.append(line)
        used += line_len

    selected.reverse()
    if not selected:
        return ""
    return "Recent conversation:\n" + "\n".join(selected)

