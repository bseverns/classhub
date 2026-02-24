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


def handle_chat(
    *,
    request,
    payload: dict,
    request_id: str,
    actor_type: str,
    client_ip: str,
    settings,
    started_at: float,
    default_text_language_keywords: list[str],
    signature_expired_exc: type[Exception],
    bad_signature_exc: type[Exception],
    deps: ChatDeps,
):
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
            return deps.json_response({"error": "invalid_scope_token"}, status=400, request_id=request_id)
        except (bad_signature_exc, ValueError):
            deps.log_chat_event("warning", "scope_token_invalid", request_id=request_id, actor_type=actor_type, ip=client_ip)
            return deps.json_response({"error": "invalid_scope_token"}, status=400, request_id=request_id)
    else:
        require_scope_for_staff = bool(getattr(settings, "HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF", False))
        if actor_type == "student" or (actor_type == "staff" and require_scope_for_staff):
            deps.log_chat_event("warning", "scope_token_missing", request_id=request_id, actor_type=actor_type, ip=client_ip)
            return deps.json_response({"error": "missing_scope_token"}, status=400, request_id=request_id)
        if any(payload.get(k) for k in ("context", "topics", "allowed_topics", "reference")):
            deps.log_chat_event(
                "info",
                "unsigned_scope_fields_ignored",
                request_id=request_id,
                actor_type=actor_type,
                ip=client_ip,
            )

    message = (payload.get("message") or "").strip()
    if not message:
        return deps.json_response({"error": "missing_message"}, status=400, request_id=request_id)

    message = deps.redact(message)[:8000]

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
        return deps.json_response({"error": "remote_backend_not_acknowledged"}, status=503, request_id=request_id)

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
        return deps.json_response(
            {
                "text": (
                    "We’re using Scratch blocks in this class, not text programming languages. "
                    "Tell me which Scratch block or part of your project you’re stuck on, "
                    "and I’ll help you with the Scratch version."
                ),
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "citations": citations,
            },
            request_id=request_id,
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
        return deps.json_response(
            {
                "text": deps.build_piper_hardware_triage_text(message),
                "model": "",
                "backend": backend,
                "strictness": strictness,
                "attempts": 0,
                "scope_verified": scope_verified,
                "triage_mode": "piper_hardware",
                "citations": citations,
            },
            request_id=request_id,
        )
    if allowed_topics:
        filter_mode = (os.getenv("HELPER_TOPIC_FILTER_MODE", "soft") or "soft").lower()
        if filter_mode == "strict" and not deps.allowed_topic_overlap(message, allowed_topics):
            deps.log_chat_event("info", "policy_redirect_allowed_topics", request_id=request_id, actor_type=actor_type, backend=backend)
            return deps.json_response(
                {
                    "text": (
                        "Let’s keep this focused on today’s lesson topics: "
                        + ", ".join(allowed_topics)
                        + ". Which part of that do you need help with?"
                    ),
                    "model": "",
                    "backend": backend,
                    "strictness": strictness,
                    "attempts": 0,
                    "scope_verified": scope_verified,
                    "citations": citations,
                },
                request_id=request_id,
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
        return deps.json_response({"error": "backend_unavailable"}, status=503, request_id=request_id)

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
            return deps.json_response({"error": "busy"}, status=503, request_id=request_id)

    attempts_used = 0
    model_used = ""
    try:
        text, model_used, attempts_used = deps.call_backend_with_retries(backend, instructions, message)
    except RuntimeError as exc:
        deps.record_backend_failure(backend)
        if str(exc) == "openai_not_installed":
            deps.log_chat_event("error", "openai_not_installed", request_id=request_id, backend=backend)
            return deps.json_response({"error": "openai_not_installed"}, status=500, request_id=request_id)
        if str(exc) == "unknown_backend":
            deps.log_chat_event("error", "unknown_backend", request_id=request_id, backend=backend)
            return deps.json_response({"error": "unknown_backend"}, status=500, request_id=request_id)
        deps.log_chat_event(
            "error",
            "backend_runtime_error",
            request_id=request_id,
            backend=backend,
            error_type=exc.__class__.__name__,
        )
        return deps.json_response({"error": "backend_error"}, status=502, request_id=request_id)
    except (urllib.error.URLError, urllib.error.HTTPError):
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_transport_error", request_id=request_id, backend=backend)
        if backend == "ollama":
            return deps.json_response({"error": "ollama_error"}, status=502, request_id=request_id)
        return deps.json_response({"error": "backend_error"}, status=502, request_id=request_id)
    except ValueError:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_parse_error", request_id=request_id, backend=backend)
        return deps.json_response({"error": "backend_error"}, status=502, request_id=request_id)
    except Exception:
        deps.record_backend_failure(backend)
        deps.log_chat_event("error", "backend_error", request_id=request_id, backend=backend)
        return deps.json_response({"error": "backend_error"}, status=502, request_id=request_id)
    finally:
        deps.release_slot(slot_key, token)

    safe_text, truncated = deps.truncate_response_text(text or "")

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
    )
    return deps.json_response(
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
        },
        request_id=request_id,
    )

