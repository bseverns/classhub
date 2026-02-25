"""Conversation-memory helpers for helper chat sessions."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Sequence

logger = logging.getLogger(__name__)

_ROLE_LABELS = {
    "student": "Student",
    "assistant": "Tutor",
}
_ALLOWED_INTENTS = {
    "debug",
    "concept",
    "strategy",
    "reflection",
    "status",
    "general",
}
_UUID_HEX_RE = re.compile(r"^[a-f0-9]{32}$")
_ACTOR_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9:_-]")
_STUDENT_ACTOR_CLASS_RE = re.compile(r"^student:(\d+):\d+$")


def _normalize_intent(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in _ALLOWED_INTENTS:
        return value
    return ""


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


def conversation_actor_index_key(*, actor_key: str) -> str:
    actor = _ACTOR_SANITIZE_RE.sub("_", (actor_key or "").strip())[:96] or "unknown"
    return f"helper:conversation:index:actor:{actor}"


def _class_id_from_actor_key(actor_key: str) -> int | None:
    match = _STUDENT_ACTOR_CLASS_RE.match((actor_key or "").strip())
    if not match:
        return None
    try:
        class_id = int(match.group(1))
    except Exception:
        return None
    if class_id <= 0:
        return None
    return class_id


def conversation_class_index_key(*, class_id: int) -> str:
    return f"helper:conversation:index:class:{max(int(class_id), 0)}"


def _coerce_key_list(raw, *, max_items: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if not value:
            continue
        out.append(value)
    if max_items > 0 and len(out) > max_items:
        out = out[-max_items:]
    return out


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
        intent = _normalize_intent(str(row.get("intent") or ""))
        turn: dict[str, str] = {"role": role, "content": content}
        if intent:
            turn["intent"] = intent
        turns.append(turn)
    return turns


def _coerce_summary(raw, *, max_chars: int) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    limit = max(int(max_chars), 120)
    if len(text) <= limit:
        return text
    return text[-limit:].lstrip()


def _coerce_state(raw, *, max_messages: int) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {"summary": "", "turns": []}
    turns = _coerce_turns(raw.get("turns"))
    if max_messages > 0 and len(turns) > max_messages:
        turns = turns[-max_messages:]
    summary = _coerce_summary(raw.get("summary"), max_chars=2000)
    return {"summary": summary, "turns": turns}


def load_state(*, cache_backend, key: str, max_messages: int) -> dict[str, object]:
    try:
        stored = cache_backend.get(key)
    except Exception:
        logger.warning("conversation_memory_cache_get_failed key=%s", key)
        return {"summary": "", "turns": []}
    return _coerce_state(stored, max_messages=max_messages)


def _register_index_key(
    *,
    cache_backend,
    index_key: str,
    conversation_key: str,
    ttl_seconds: int,
    max_entries: int = 1200,
) -> None:
    if not index_key:
        return
    try:
        existing = cache_backend.get(index_key)
    except Exception:
        logger.warning("conversation_memory_cache_get_failed key=%s", index_key)
        return
    values = _coerce_key_list(existing, max_items=max_entries)
    if conversation_key in values:
        values = [item for item in values if item != conversation_key]
    values.append(conversation_key)
    if max_entries > 0 and len(values) > max_entries:
        values = values[-max_entries:]
    try:
        cache_backend.set(index_key, values, timeout=max(int(ttl_seconds), 300))
    except Exception:
        logger.warning("conversation_memory_cache_set_failed key=%s", index_key)


def save_state(
    *,
    cache_backend,
    key: str,
    turns: list[dict[str, str]],
    summary: str,
    ttl_seconds: int,
    actor_key: str = "",
) -> None:
    normalized = _coerce_turns(turns)
    payload = {
        "v": 2,
        "summary": _coerce_summary(summary, max_chars=2000),
        "turns": normalized,
    }
    timeout = max(int(ttl_seconds), 60)
    try:
        cache_backend.set(key, payload, timeout=timeout)
    except Exception:
        logger.warning("conversation_memory_cache_set_failed key=%s", key)
        return
    actor_index_key = conversation_actor_index_key(actor_key=actor_key)
    _register_index_key(
        cache_backend=cache_backend,
        index_key=actor_index_key,
        conversation_key=key,
        ttl_seconds=timeout,
    )
    class_id = _class_id_from_actor_key(actor_key)
    if class_id is not None:
        _register_index_key(
            cache_backend=cache_backend,
            index_key=conversation_class_index_key(class_id=class_id),
            conversation_key=key,
            ttl_seconds=timeout,
        )


def load_turns(*, cache_backend, key: str, max_messages: int) -> list[dict[str, str]]:
    state = load_state(cache_backend=cache_backend, key=key, max_messages=max_messages)
    turns = state.get("turns")
    if not isinstance(turns, list):
        return []
    return turns


def save_turns(
    *,
    cache_backend,
    key: str,
    turns: list[dict[str, str]],
    ttl_seconds: int,
    actor_key: str = "",
) -> None:
    save_state(
        cache_backend=cache_backend,
        key=key,
        turns=turns,
        summary="",
        ttl_seconds=ttl_seconds,
        actor_key=actor_key,
    )


def clear_turns(*, cache_backend, key: str) -> None:
    try:
        cache_backend.delete(key)
    except Exception:
        logger.warning("conversation_memory_cache_delete_failed key=%s", key)


def _format_turn_line(row: dict[str, str]) -> str:
    role = _ROLE_LABELS.get(row["role"], "Tutor")
    content = row["content"]
    if row["role"] == "student":
        intent = _normalize_intent(str(row.get("intent") or ""))
        if intent:
            return f"{role} [{intent}]: {content}"
    return f"{role}: {content}"


def compact_turns(
    *,
    turns: Sequence[dict[str, str]],
    max_messages: int,
    summary: str,
    summary_max_chars: int,
) -> tuple[str, list[dict[str, str]], bool]:
    normalized = _coerce_turns(list(turns))
    max_keep = max(int(max_messages), 0)
    if len(normalized) <= max_keep:
        return (_coerce_summary(summary, max_chars=summary_max_chars), normalized, False)

    overflow = normalized[: len(normalized) - max_keep] if max_keep > 0 else normalized
    keep = normalized[-max_keep:] if max_keep > 0 else []
    next_summary = summarize_turns(
        turns=overflow,
        previous_summary=summary,
        max_chars=summary_max_chars,
    )
    return (next_summary, keep, True)


def summarize_turns(
    *,
    turns: Sequence[dict[str, str]],
    previous_summary: str = "",
    max_chars: int,
) -> str:
    cap = max(int(max_chars), 200)
    segments: list[str] = []
    existing = _coerce_summary(previous_summary, max_chars=cap)
    if existing:
        segments.extend([part.strip() for part in existing.split(" | ") if part.strip()])
    for row in _coerce_turns(list(turns)):
        segments.append(_format_turn_line(row))
    if not segments:
        return ""

    picked: list[str] = []
    used = 0
    for segment in reversed(segments):
        seg_len = len(segment) + (3 if picked else 0)
        if picked and used + seg_len > cap:
            break
        if not picked and seg_len > cap:
            picked.append(segment[-cap:])
            used = len(picked[0])
            break
        picked.append(segment)
        used += seg_len
    picked.reverse()
    if not picked:
        return ""
    summary = " | ".join(picked)
    return _coerce_summary(summary, max_chars=cap)


def clear_class_conversations(*, cache_backend, class_id: int, max_keys: int = 4000) -> int:
    class_key = conversation_class_index_key(class_id=class_id)
    try:
        indexed = cache_backend.get(class_key)
    except Exception:
        logger.warning("conversation_memory_cache_get_failed key=%s", class_key)
        return 0

    keys = _coerce_key_list(indexed, max_items=max(int(max_keys), 1))
    if not keys:
        try:
            cache_backend.delete(class_key)
        except Exception:
            logger.warning("conversation_memory_cache_delete_failed key=%s", class_key)
        return 0

    deleted = 0
    for key in keys:
        try:
            cache_backend.delete(key)
            deleted += 1
        except Exception:
            logger.warning("conversation_memory_cache_delete_failed key=%s", key)
    try:
        cache_backend.delete(class_key)
    except Exception:
        logger.warning("conversation_memory_cache_delete_failed key=%s", class_key)
    return deleted


def format_turns_for_prompt(*, turns: list[dict[str, str]], max_chars: int, summary: str = "") -> str:
    normalized = _coerce_turns(turns)
    summary_text = _coerce_summary(summary, max_chars=max(int(max_chars), 300))
    if not normalized and not summary_text:
        return ""

    selected: list[str] = []
    used = 0
    for row in reversed(normalized):
        line = _format_turn_line(row)
        line_len = len(line) + 1
        if max_chars > 0 and selected and used + line_len > max_chars:
            break
        selected.append(line)
        used += line_len

    selected.reverse()
    sections: list[str] = []
    if summary_text:
        sections.append("Conversation summary:\n" + summary_text)
    if selected:
        sections.append("Recent conversation:\n" + "\n".join(selected))
    if not sections:
        return ""
    return "\n\n".join(sections)
