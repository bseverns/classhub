"""Chat orchestration service for helper requests."""

from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from ..llm import (
    LLMAuthError,
    LLMConfigError,
    LLMMalformedResponseError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)
from .context_envelope import ScopeResolutionError, resolve_context_envelope
from .execution_config import resolve_execution_config
from .runtime_config import resolve_policy_bundle


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
    retrieve_curriculum_citations: Callable[..., Awaitable[list[dict]]]
    build_reference_citations: Callable[..., list[dict]]
    format_reference_citations_for_prompt: Callable[[list[dict]], str]
    parse_csv_list: Callable[[str], list[str]]
    contains_text_language: Callable[[str, list[str]], bool]
    is_scratch_context: Callable[[str, list[str], str], bool]
    is_stem_technology_question: Callable[..., bool]
    is_piper_context: Callable[[str, list[str], str, str], bool]
    is_piper_hardware_question: Callable[[str], bool]
    build_piper_hardware_triage_text: Callable[..., str]
    is_mouse_only_access_question: Callable[[str], bool]
    build_mouse_only_adaptation_text: Callable[..., str]
    is_teamwork_decision_question: Callable[[str], bool]
    build_teamwork_decision_text: Callable[..., str]
    is_class_reentry_privacy_question: Callable[[str], bool]
    build_class_reentry_privacy_text: Callable[..., str]
    is_publish_privacy_question: Callable[[str], bool]
    build_publish_privacy_text: Callable[..., str]
    is_score_condition_debug_question: Callable[[str], bool]
    build_score_condition_debug_text: Callable[..., str]
    is_wellbeing_reset_question: Callable[[str], bool]
    build_wellbeing_reset_text: Callable[..., str]
    is_context_dependent_follow_up: Callable[[str], bool]
    allowed_topic_overlap: Callable[..., bool]
    build_instructions: Callable[..., str]
    normalize_response_language: Callable[[str], str]
    build_text_language_redirect: Callable[[str], str]
    build_allowed_topics_redirect: Callable[[str, list[str]], str]
    backend_circuit_is_open: Callable[[str], bool]
    llm_backend_requires_acknowledgement: Callable[[str], bool]
    call_backend_with_retries: Callable[[str, str, str], Awaitable[tuple[str, str, int]]]
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


async def handle_chat(
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
    response_language_code = "en"

    def _response(body: dict, *, status: int = 200):
        payload_with_conversation = dict(body or {})
        payload_with_conversation["conversation_id"] = conversation_id
        payload_with_conversation["conversation_enabled"] = conversation_enabled
        payload_with_conversation["response_language"] = response_language_code
        if intent and "intent" not in payload_with_conversation:
            payload_with_conversation["intent"] = intent
        if "conversation_compacted" not in payload_with_conversation:
            payload_with_conversation["conversation_compacted"] = conversation_compacted
        return deps.json_response(payload_with_conversation, status=status, request_id=request_id)

    execution_config = resolve_execution_config(
        env_int=deps.env_int,
        env_float=deps.env_float,
        env_bool=deps.env_bool,
        parse_csv_list=deps.parse_csv_list,
        default_text_language_keywords=default_text_language_keywords,
    )

    try:
        envelope = resolve_context_envelope(
            payload=payload,
            actor_type=actor_type,
            require_scope_for_staff=bool(getattr(settings, "HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF", False)),
            max_scope_token_age_seconds=execution_config.scope_token_max_age_seconds,
            load_scope_from_token=deps.load_scope_from_token,
            signature_expired_exc=signature_expired_exc,
            bad_signature_exc=bad_signature_exc,
        )
    except ScopeResolutionError as exc:
        deps.log_chat_event(
            exc.log_level,
            exc.log_event,
            request_id=request_id,
            actor_type=actor_type,
            ip=client_ip,
        )
        return _response({"error": exc.response_error}, status=400)

    if envelope.ignored_unsigned_scope_fields:
        deps.log_chat_event(
            "info",
            "unsigned_scope_fields_ignored",
            request_id=request_id,
            actor_type=actor_type,
            ip=client_ip,
        )

    scope_token = envelope.scope_token
    context_value = envelope.context
    topics = envelope.topics
    allowed_topics = envelope.allowed_topics
    reference_key = envelope.reference_key
    scope_verified = envelope.scope_verified

    conversation_enabled = execution_config.conversation_enabled and bool(actor_key)
    conversation_scope_fp = deps.scope_fingerprint(scope_token)
    max_conversation_messages = execution_config.conversation_max_messages
    conversation_ttl_seconds = execution_config.conversation_ttl_seconds
    conversation_turn_max_chars = execution_config.conversation_turn_max_chars
    conversation_history_max_chars = execution_config.conversation_history_max_chars
    conversation_summary_max_chars = execution_config.conversation_summary_max_chars
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

    response_language_code = deps.normalize_response_language(str(payload.get("language_code") or ""))
    message = deps.redact(message)[:8000]
    intent = deps.classify_intent(message)
    follow_up_suggestions = deps.build_follow_up_suggestions(
        intent=intent,
        context=context_value or "",
        topics=topics,
        allowed_topics=allowed_topics,
        history_summary=history_summary,
        max_items=execution_config.follow_up_suggestions_max,
        response_language_code=response_language_code,
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
                backend=execution_config.backend,
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

    backend = execution_config.backend
    if not execution_config.llm_enabled:
        deps.log_chat_event("warning", "llm_disabled", request_id=request_id, backend=backend)
        return _response({"error": "llm_disabled"}, status=503)
    if actor_type not in set(execution_config.llm_allowed_actor_types):
        deps.log_chat_event(
            "warning",
            "llm_access_disabled",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        return _response({"error": "llm_access_disabled"}, status=403)
    policy_bundle = resolve_policy_bundle()
    strictness = policy_bundle.strictness
    scope_mode = policy_bundle.scope_mode
    remote_mode_acknowledged = bool(getattr(settings, "HELPER_REMOTE_MODE_ACKNOWLEDGED", False)) or deps.env_bool(
        "HELPER_REMOTE_MODE_ACKNOWLEDGED",
        False,
    )
    if deps.llm_backend_requires_acknowledgement(backend) and not remote_mode_acknowledged:
        deps.log_chat_event(
            "warning",
            "remote_backend_not_acknowledged",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        return _response({"error": "remote_backend_not_acknowledged"}, status=503)

    reference_dir = execution_config.reference_dir
    reference_map_raw = execution_config.reference_map_raw
    default_reference_file = execution_config.default_reference_file

    if deps.is_mouse_only_access_question(message) and deps.is_piper_context(context_value or "", topics, "", reference_key):
        deps.log_chat_event(
            "info",
            "policy_redirect_mouse_only_adaptation",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_mouse_only_adaptation_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if deps.is_teamwork_decision_question(message):
        deps.log_chat_event(
            "info",
            "policy_redirect_teamwork_protocol",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_teamwork_decision_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if deps.is_class_reentry_privacy_question(message):
        deps.log_chat_event(
            "info",
            "policy_redirect_class_reentry_privacy",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_class_reentry_privacy_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if deps.is_publish_privacy_question(message):
        deps.log_chat_event(
            "info",
            "policy_redirect_publish_privacy",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_publish_privacy_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if deps.is_score_condition_debug_question(message):
        deps.log_chat_event(
            "info",
            "policy_redirect_score_condition_debug",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_score_condition_debug_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if deps.is_wellbeing_reset_question(message):
        deps.log_chat_event(
            "info",
            "policy_redirect_wellbeing_reset",
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        guidance_text = deps.build_wellbeing_reset_text(response_language_code=response_language_code)
        _persist_turns(guidance_text)
        return _response(
            {
                "text": guidance_text,
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": [],
                "intent": intent,
                "follow_up_suggestions": follow_up_suggestions,
            }
        )

    if reference_key:
        reference_file = deps.resolve_reference_file(reference_key, reference_dir, reference_map_raw)
    else:
        reference_file = default_reference_file
    reference_text = deps.load_reference_text(reference_file)
    reference_chunks = deps.load_reference_chunks(reference_file)
    reference_source = reference_key or (Path(reference_file).stem if reference_file else "")
    prefer_stem_technology = deps.is_stem_technology_question(
        message,
        context_value=context_value or "",
        topics=topics,
        reference_text=reference_text,
    )
    citations: list[dict] = []
    if execution_config.rag_enabled:
        try:
            citations = await deps.retrieve_curriculum_citations(
                query_text=" ".join([message, context_value or "", " ".join(topics)]),
                reference_key=reference_source,
                max_items=execution_config.reference_max_citations,
                max_cosine_distance=execution_config.rag_max_cosine_distance,
                embedding_base_url=execution_config.rag_embedding_base_url,
                embedding_model=execution_config.rag_embedding_model,
                embedding_timeout_seconds=execution_config.rag_embedding_timeout_seconds,
                embedding_dimensions=execution_config.rag_embedding_dimensions,
                prefer_stem_technology=prefer_stem_technology,
            )
        except Exception as exc:
            deps.log_chat_event(
                "warning",
                "rag_retrieval_failed",
                request_id=request_id,
                actor_type=actor_type,
                backend=backend,
                error_type=exc.__class__.__name__,
            )
            citations = []
    if not citations:
        citations = deps.build_reference_citations(
            message=message,
            context=context_value or "",
            topics=topics,
            reference_chunks=reference_chunks,
            source_label=reference_source,
            max_items=execution_config.reference_max_citations,
            prefer_stem_technology=prefer_stem_technology,
        )
    reference_citations = deps.format_reference_citations_for_prompt(citations)
    lang_keywords = execution_config.text_language_keywords
    if deps.contains_text_language(message, lang_keywords) and deps.is_scratch_context(context_value or "", topics, reference_text):
        deps.log_chat_event("info", "policy_redirect_text_language", request_id=request_id, actor_type=actor_type, backend=backend)
        redirect_text = deps.build_text_language_redirect(response_language_code)
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
        execution_config.piper_hardware_triage_enabled
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
        triage_text = deps.build_piper_hardware_triage_text(
            message,
            response_language_code=response_language_code,
        )
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
        filter_mode = policy_bundle.topic_filter_mode
        topic_filter_input = message
        if conversation_enabled and (history_turns or history_summary) and deps.is_context_dependent_follow_up(message):
            recent_student_lines = [
                str(row.get("content") or "").strip()
                for row in history_turns
                if str(row.get("role") or "").strip().lower() == "student" and str(row.get("content") or "").strip()
            ]
            recent_student_lines = recent_student_lines[-2:]
            topic_filter_input = "\n".join([*recent_student_lines, history_summary, message]).strip()
        if filter_mode == "strict" and not deps.allowed_topic_overlap(
            topic_filter_input,
            allowed_topics,
            context=context_value or "",
            topics=topics,
            reference_text=reference_text,
        ):
            deps.log_chat_event("info", "policy_redirect_allowed_topics", request_id=request_id, actor_type=actor_type, backend=backend)
            redirect_text = deps.build_allowed_topics_redirect(response_language_code, allowed_topics)
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
        response_language_code=response_language_code,
    )

    if deps.backend_circuit_is_open(backend):
        deps.log_chat_event("warning", "backend_circuit_open", request_id=request_id, backend=backend)
        return _response({"error": "backend_unavailable"}, status=503)

    max_concurrency = execution_config.queue_max_concurrency
    max_wait = execution_config.queue_max_wait_seconds
    poll = execution_config.queue_poll_seconds
    ttl = execution_config.queue_slot_ttl_seconds
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
        text, model_used, attempts_used = await deps.call_backend_with_retries(backend, instructions, model_message)
    except LLMTimeoutError:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_timeout", request_id=request_id, backend=backend)
        return _response({"error": "backend_timeout"}, status=504)
    except LLMUpstreamUnavailableError:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_unavailable", request_id=request_id, backend=backend)
        return _response({"error": "backend_unavailable"}, status=503)
    except (LLMAuthError, LLMConfigError):
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_config_error", request_id=request_id, backend=backend)
        return _response({"error": "backend_config_error"}, status=503)
    except LLMMalformedResponseError:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_malformed_response", request_id=request_id, backend=backend)
        return _response({"error": "backend_malformed_response"}, status=502)
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
