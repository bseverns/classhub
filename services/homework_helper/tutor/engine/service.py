"""Chat orchestration service for helper requests."""

from __future__ import annotations

import os
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ChatDeps:
    json_response: Callable[..., object]
    log_chat_event: Callable[..., None]
    env_int: Callable[[str, int], int]
    env_float: Callable[[str, float], float]
    env_bool: Callable[[str, bool], bool]
    redact: Callable[[str], str]
    load_scope_from_token: Callable[..., dict]
    resolve_reference_file: Callable[[str | None, str, str], str]
    load_reference_text: Callable[[str], str]
    load_reference_chunks: Callable[[str], tuple[str, ...]]
    build_reference_citations: Callable[..., list[dict]]
    format_reference_citations_for_prompt: Callable[[list[dict]], str]
    parse_csv_list: Callable[[str], list[str]]
    contains_text_language: Callable[[str, list[str]], bool]
    is_scratch_context: Callable[[str, list[str], str], bool]
    is_piper_context: Callable[[str, list[str], str, str], bool]
    is_piper_hardware_question: Callable[[str], bool]
    build_piper_hardware_triage_text: Callable[[str], str]
    allowed_topic_overlap: Callable[[str, list[str]], bool]
    build_instructions: Callable[..., str]
    backend_circuit_is_open: Callable[[str], bool]
    call_backend_with_retries: Callable[[str, str, str], tuple[str, str, int]]
    record_backend_failure: Callable[[str], None]
    reset_backend_failure_state: Callable[[str], None]
    acquire_slot: Callable[[int, float, float, int], tuple[str | None, str | None]]
    release_slot: Callable[[str | None, str | None], None]
    truncate_response_text: Callable[[str], tuple[str, bool]]
    normalize_conversation_id: Callable[[str], str]
    scope_fingerprint: Callable[[str], str]
    load_conversation_state: Callable[..., dict]
    save_conversation_state: Callable[..., None]
    compact_conversation: Callable[..., tuple[str, list[dict], bool]]
    clear_conversation_turns: Callable[..., None]
    format_conversation_for_prompt: Callable[..., str]
    classify_intent: Callable[[str], str]
    build_follow_up_suggestions: Callable[..., list[str]]


def handle_chat(
    *,
    request,
    payload: dict,
    request_id: str,
    actor_key: str,
    actor_type: str,
    client_ip: str,
    settings,
    started_at: float,
    default_text_language_keywords: list[str],
    signature_expired_exc: type[Exception],
    bad_signature_exc: type[Exception],
    deps: ChatDeps,
):
    conversation_id = deps.normalize_conversation_id(str(payload.get("conversation_id") or ""))
    conversation_enabled = False
    intent = ""
    conversation_compacted = False

    def _response(body: dict, *, status: int = 200):
        payload_with_conversation = dict(body or {})
        payload_with_conversation["conversation_id"] = conversation_id
        payload_with_conversation["conversation_enabled"] = conversation_enabled
        if intent and "intent" not in payload_with_conversation:
            payload_with_conversation["intent"] = intent
        if "conversation_compacted" not in payload_with_conversation:
            payload_with_conversation["conversation_compacted"] = conversation_compacted
        return deps.json_response(payload_with_conversation, status=status, request_id=request_id)

    scope_token = str(payload.get("scope_token") or "").strip()
    context_value = ""
    topics: list[str] = []
    allowed_topics: list[str] = []
    reference_key = ""
    scope_verified = False

    if scope_token:
        try:
            scope = deps.load_scope_from_token(
                scope_token,
                max_age_seconds=max(deps.env_int("HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS", 7200), 60),
            )
            context_value = scope.get("context", "")
            topics = scope.get("topics", [])
            allowed_topics = scope.get("allowed_topics", [])
            reference_key = scope.get("reference", "")
            scope_verified = True
        except signature_expired_exc:
            deps.log_chat_event("warning", "scope_token_expired", request_id=request_id, actor_type=actor_type, ip=client_ip)
            return _response({"error": "invalid_scope_token"}, status=400)
        except (bad_signature_exc, ValueError):
            deps.log_chat_event("warning", "scope_token_invalid", request_id=request_id, actor_type=actor_type, ip=client_ip)
            return _response({"error": "invalid_scope_token"}, status=400)
    else:
        require_scope_for_staff = bool(getattr(settings, "HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF", False))
        if actor_type == "student" or (actor_type == "staff" and require_scope_for_staff):
            deps.log_chat_event("warning", "scope_token_missing", request_id=request_id, actor_type=actor_type, ip=client_ip)
            return _response({"error": "missing_scope_token"}, status=400)
        if any(payload.get(k) for k in ("context", "topics", "allowed_topics", "reference")):
            deps.log_chat_event(
                "info",
                "unsigned_scope_fields_ignored",
                request_id=request_id,
                actor_type=actor_type,
                ip=client_ip,
            )

    conversation_enabled = deps.env_bool("HELPER_CONVERSATION_ENABLED", True) and bool(actor_key)
    conversation_scope_fp = deps.scope_fingerprint(scope_token)
    max_conversation_messages = max(deps.env_int("HELPER_CONVERSATION_MAX_MESSAGES", 8), 0)
    conversation_ttl_seconds = max(deps.env_int("HELPER_CONVERSATION_TTL_SECONDS", 3600), 60)
    conversation_turn_max_chars = max(deps.env_int("HELPER_CONVERSATION_TURN_MAX_CHARS", 800), 80)
    conversation_history_max_chars = max(deps.env_int("HELPER_CONVERSATION_HISTORY_MAX_CHARS", 2400), 300)
    conversation_summary_max_chars = max(deps.env_int("HELPER_CONVERSATION_SUMMARY_MAX_CHARS", 900), 200)
    if max_conversation_messages <= 0:
        conversation_enabled = False

    if conversation_enabled and bool(payload.get("reset_conversation")):
        deps.clear_conversation_turns(
            conversation_id=conversation_id,
            actor_key=actor_key,
            scope_fingerprint=conversation_scope_fp,
        )

    history_turns: list[dict] = []
    history_summary = ""
    if conversation_enabled:
        conversation_state = deps.load_conversation_state(
            conversation_id=conversation_id,
            actor_key=actor_key,
            scope_fingerprint=conversation_scope_fp,
            max_messages=max_conversation_messages,
        )
        history_turns = list(conversation_state.get("turns") or [])
        history_summary = str(conversation_state.get("summary") or "").strip()

    message = (payload.get("message") or "").strip()
    if not message:
        return _response({"error": "missing_message"}, status=400)

    message = deps.redact(message)[:8000]
    intent = deps.classify_intent(message)
    follow_up_suggestions = deps.build_follow_up_suggestions(
        intent=intent,
        context=context_value or "",
        topics=topics,
        allowed_topics=allowed_topics,
        history_summary=history_summary,
        max_items=max(deps.env_int("HELPER_FOLLOW_UP_SUGGESTIONS_MAX", 3), 1),
    )

    def _persist_turns(assistant_text: str) -> None:
        nonlocal history_turns, history_summary, conversation_compacted
        if not conversation_enabled:
            return
        user_turn = {"role": "student", "content": message[:conversation_turn_max_chars], "intent": intent}
        assistant_turn = {"role": "assistant", "content": deps.redact(assistant_text)[:conversation_turn_max_chars], "intent": intent}
        next_turns = [*history_turns, user_turn, assistant_turn]
        next_summary, next_turns, compacted = deps.compact_conversation(
            turns=next_turns,
            max_messages=max_conversation_messages,
            summary=history_summary,
            summary_max_chars=conversation_summary_max_chars,
        )
        deps.save_conversation_state(
            conversation_id=conversation_id,
            actor_key=actor_key,
            scope_fingerprint=conversation_scope_fp,
            turns=next_turns,
            summary=next_summary,
            ttl_seconds=conversation_ttl_seconds,
        )
        history_turns = next_turns
        history_summary = next_summary
        if compacted:
            conversation_compacted = True
            deps.log_chat_event(
                "info",
                "conversation_compacted",
                request_id=request_id,
                actor_type=actor_type,
                backend=(os.getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower(),
                conversation_id=conversation_id,
            )

    conversation_prompt = ""
    if conversation_enabled and (history_turns or history_summary):
        conversation_prompt = deps.format_conversation_for_prompt(
            history_turns,
            max_chars=conversation_history_max_chars,
            summary=history_summary,
        )
    model_message = message
    if conversation_prompt:
        model_message = f"{conversation_prompt}\n\nStudent (latest):\n{message}"

    backend = (os.getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()
    strictness = (os.getenv("HELPER_STRICTNESS", "light") or "light").lower()
    scope_mode = (os.getenv("HELPER_SCOPE_MODE", "soft") or "soft").lower()
    if backend == "openai" and not bool(getattr(settings, "HELPER_REMOTE_MODE_ACKNOWLEDGED", False)):
        deps.log_chat_event(
            "warning",
            "remote_backend_not_acknowledged",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        return _response({"error": "remote_backend_not_acknowledged"}, status=503)

    reference_dir = os.getenv("HELPER_REFERENCE_DIR", "/app/tutor/reference").strip()
    reference_map_raw = os.getenv("HELPER_REFERENCE_MAP", "").strip()
    default_reference_file = os.getenv("HELPER_REFERENCE_FILE", "").strip()
    if reference_key:
        reference_file = deps.resolve_reference_file(reference_key, reference_dir, reference_map_raw)
    else:
        reference_file = default_reference_file
    reference_text = deps.load_reference_text(reference_file)
    reference_chunks = deps.load_reference_chunks(reference_file)
    reference_source = reference_key or (Path(reference_file).stem if reference_file else "")
    citations = deps.build_reference_citations(
        message=message,
        context=context_value or "",
        topics=topics,
        reference_chunks=reference_chunks,
        source_label=reference_source,
        max_items=max(deps.env_int("HELPER_REFERENCE_MAX_CITATIONS", 3), 1),
    )
    reference_citations = deps.format_reference_citations_for_prompt(citations)
    env_keywords = deps.parse_csv_list(os.getenv("HELPER_TEXT_LANGUAGE_KEYWORDS", ""))
    lang_keywords = env_keywords or default_text_language_keywords
    if deps.contains_text_language(message, lang_keywords) and deps.is_scratch_context(context_value or "", topics, reference_text):
        deps.log_chat_event("info", "policy_redirect_text_language", request_id=request_id, actor_type=actor_type, backend=backend)
        redirect_text = (
            "We’re using Scratch blocks in this class, not text programming languages. "
            "Tell me which Scratch block or part of your project you’re stuck on, "
            "and I’ll help you with the Scratch version."
        )
        _persist_turns(redirect_text)
        return _response(
            {
                "text": redirect_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": citations,
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )
    if (
        deps.env_bool("HELPER_PIPER_HARDWARE_TRIAGE_ENABLED", True)
        and deps.is_piper_context(context_value or "", topics, reference_text, reference_key)
        and deps.is_piper_hardware_question(message)
        and not citations
    ):
        deps.log_chat_event(
            "info",
            "policy_redirect_piper_hardware_triage",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        triage_text = deps.build_piper_hardware_triage_text(message)
        _persist_turns(triage_text)
        return _response(
            {
                "text": triage_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "triage_mode": "piper_hardware",
                "citations": citations,
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )
    if allowed_topics:
        filter_mode = (os.getenv("HELPER_TOPIC_FILTER_MODE", "soft") or "soft").lower()
        if filter_mode == "strict" and not deps.allowed_topic_overlap(message, allowed_topics):
            deps.log_chat_event("info", "policy_redirect_allowed_topics", request_id=request_id, actor_type=actor_type, backend=backend)
            redirect_text = (
                "Let’s keep this focused on today’s lesson topics: "
                + ", ".join(allowed_topics)
                + ". Which part of that do you need help with?"
            )
            _persist_turns(redirect_text)
            return _response(
                {
                    "text": redirect_text,
                    "model": "",
                    "backend": backend,
                    "strictness": strictness,
                    "attempts": 0,
                    "scope_verified": scope_verified,
                    "citations": citations,
                    "intent": intent,
                    "follow_up_suggestions": follow_up_suggestions,
                }
            )
    instructions = deps.build_instructions(
        strictness,
        context=context_value or "",
        topics=topics,
        scope_mode=scope_mode,
        allowed_topics=allowed_topics,
        reference_text=reference_text,
        reference_citations=reference_citations,
    )

    if deps.backend_circuit_is_open(backend):
        deps.log_chat_event("warning", "backend_circuit_open", request_id=request_id, backend=backend)
        return _response({"error": "backend_unavailable"}, status=503)

    max_concurrency = deps.env_int("HELPER_MAX_CONCURRENCY", 2)
    max_wait = deps.env_float("HELPER_QUEUE_MAX_WAIT_SECONDS", 10.0)
    poll = deps.env_float("HELPER_QUEUE_POLL_SECONDS", 0.2)
    ttl = deps.env_int("HELPER_QUEUE_SLOT_TTL_SECONDS", 120)
    queue_started_at = time.monotonic()
    slot_key, token = None, None
    queue_error = False
    try:
        slot_key, token = deps.acquire_slot(max_concurrency, max_wait, poll, ttl)
    except Exception as exc:
        queue_error = True
        deps.log_chat_event(
            "warning",
            "queue_unavailable",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
            error_type=exc.__class__.__name__,
        )
    queue_wait_ms = int((time.monotonic() - queue_started_at) * 1000)
    if max_concurrency > 0 and slot_key is None:
        if queue_error:
            deps.log_chat_event(
                "warning",
                "queue_fail_open",
                request_id=request_id,
                actor_type=actor_type,
                backend=backend,
                queue_wait_ms=queue_wait_ms,
            )
        else:
            deps.log_chat_event(
                "warning",
                "queue_busy",
                request_id=request_id,
                actor_type=actor_type,
                backend=backend,
                queue_wait_ms=queue_wait_ms,
            )
            return _response({"error": "busy"}, status=503)

    attempts_used = 0
    model_used = ""
    try:
        text, model_used, attempts_used = deps.call_backend_with_retries(backend, instructions, model_message)
    except RuntimeError as exc:
        deps.record_backend_failure(backend)
        if str(exc) == "openai_not_installed":
            deps.log_chat_event("error", "openai_not_installed", request_id=request_id, backend=backend)
            return _response({"error": "openai_not_installed"}, status=500)
        if str(exc) == "unknown_backend":
            deps.log_chat_event("error", "unknown_backend", request_id=request_id, backend=backend)
            return _response({"error": "unknown_backend"}, status=500)
        deps.log_chat_event(
            "error",
            "backend_runtime_error",
            request_id=request_id,
            backend=backend,
            error_type=exc.__class__.__name__,
        )
        return _response({"error": "backend_error"}, status=502)
    except (urllib.error.URLError, urllib.error.HTTPError):
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_transport_error", request_id=request_id, backend=backend)
        if backend == "ollama":
            return _response({"error": "ollama_error"}, status=502)
        return _response({"error": "backend_error"}, status=502)
    except ValueError:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_parse_error", request_id=request_id, backend=backend)
        return _response({"error": "backend_error"}, status=502)
    except Exception:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_error", request_id=request_id, backend=backend)
        return _response({"error": "backend_error"}, status=502)
    finally:
        deps.release_slot(slot_key, token)

    safe_text, truncated = deps.truncate_response_text(text or "")
    _persist_turns(safe_text)

    deps.reset_backend_failure_state(backend)
    total_ms = int((time.monotonic() - started_at) * 1000)
    deps.log_chat_event(
        "info",
        "success",
        request_id=request_id,
        actor_type=actor_type,
        backend=backend,
        attempts=attempts_used,
        queue_wait_ms=queue_wait_ms,
        response_chars=len(safe_text),
        truncated=truncated,
        total_ms=total_ms,
        intent=intent,
    )
    return _response(
        {
            "text": safe_text,
            "model": model_used,
            "backend": backend,
            "strictness": strictness,
            "attempts": attempts_used,
            "queue_wait_ms": queue_wait_ms,
            "total_ms": total_ms,
            "truncated": truncated,
            "scope_verified": scope_verified,
            "citations": citations,
            "intent": intent,
            "follow_up_suggestions": follow_up_suggestions,
        }
    )
