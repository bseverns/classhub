import json
import logging
import os
import time
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from common.helper_scope import parse_scope_token
from common.request_safety import (
    build_staff_or_student_actor_key,
    client_ip_from_request,
    fixed_window_allow,
)
from django.db import connection, transaction

from .classhub_events import emit_helper_chat_access_event
from .engine import auth as engine_auth
from .engine import backends as engine_backends
from .engine import circuit as engine_circuit
from .engine import heuristics as engine_heuristics
from .engine import memory as engine_memory
from .engine import reference as engine_reference
from .engine import runtime as engine_runtime
from .engine import service as engine_service
from .policy import build_instructions
from .queueing import acquire_slot, release_slot

DEFAULT_TEXT_LANGUAGE_KEYWORDS = engine_heuristics.DEFAULT_TEXT_LANGUAGE_KEYWORDS
DEFAULT_PIPER_CONTEXT_KEYWORDS = engine_heuristics.DEFAULT_PIPER_CONTEXT_KEYWORDS
DEFAULT_PIPER_HARDWARE_KEYWORDS = engine_heuristics.DEFAULT_PIPER_HARDWARE_KEYWORDS
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


def _backend_circuit_is_open(backend: str) -> bool:
    return engine_circuit.backend_circuit_is_open(
        cache_backend=cache,
        backend=backend,
        logger=logger,
    )


def _record_backend_failure(backend: str) -> None:
    threshold = max(_env_int("HELPER_CIRCUIT_BREAKER_FAILURES", 5), 1)
    ttl = max(_env_int("HELPER_CIRCUIT_BREAKER_TTL_SECONDS", 30), 1)
    engine_circuit.record_backend_failure(
        cache_backend=cache,
        backend=backend,
        threshold=threshold,
        ttl=ttl,
        logger=logger,
    )


def _reset_backend_failure_state(backend: str) -> None:
    engine_circuit.reset_backend_failure_state(
        cache_backend=cache,
        backend=backend,
        logger=logger,
    )


@lru_cache(maxsize=32)
def _table_exists(table_name: str) -> bool:
    """Best-effort table existence check without raising for missing tables."""
    return engine_auth.table_exists(
        connection=connection,
        transaction_module=transaction,
        table_name=table_name,
    )


def _student_session_exists(student_id: int, class_id: int) -> bool:
    """Validate student session against shared Class Hub table when available."""
    return engine_auth.student_session_exists(
        connection=connection,
        transaction_module=transaction,
        settings=settings,
        student_id=student_id,
        class_id=class_id,
        table_exists_fn=_table_exists,
    )


def _actor_key(request) -> str:
    return engine_auth.actor_key(
        request=request,
        build_actor_key_fn=build_staff_or_student_actor_key,
        student_session_exists_fn=_student_session_exists,
    )


def _load_scope_from_token(scope_token: str, *, max_age_seconds: int) -> dict:
    return parse_scope_token(scope_token, max_age_seconds=max_age_seconds)


def _ollama_chat(base_url: str, model: str, instructions: str, message: str) -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return engine_backends.ollama_chat(
        base_url=base_url,
        model=model,
        instructions=instructions,
        message=message,
        timeout_seconds=_env_int("OLLAMA_TIMEOUT_SECONDS", 30),
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        top_p=float(os.getenv("OLLAMA_TOP_P", "0.9")),
        num_predict=_env_int("OLLAMA_NUM_PREDICT", 0),
    )


def _openai_chat(model: str, instructions: str, message: str) -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return engine_backends.openai_chat(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model=model,
        instructions=instructions,
        message=message,
        max_output_tokens=_env_int("OPENAI_MAX_OUTPUT_TOKENS", 0),
    )


def _mock_chat() -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return engine_backends.mock_chat(text=os.getenv("HELPER_MOCK_RESPONSE_TEXT", ""))


def _truncate_response_text(text: str) -> tuple[str, bool]:
    return engine_heuristics.truncate_response_text(
        text,
        max_chars=_env_int("HELPER_RESPONSE_MAX_CHARS", 2200),
    )


def _invoke_backend(backend: str, instructions: str, message: str) -> tuple[str, str]:
    registry = {
        "ollama": engine_backends.CallableBackend(
            chat_fn=lambda system_instructions, user_message: _ollama_chat(
                os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
                system_instructions,
                user_message,
            )
        ),
        "openai": engine_backends.CallableBackend(
            chat_fn=lambda system_instructions, user_message: _openai_chat(
                os.getenv("OPENAI_MODEL", "gpt-5.2"),
                system_instructions,
                user_message,
            )
        ),
        "mock": engine_backends.CallableBackend(
            chat_fn=lambda _system_instructions, _user_message: _mock_chat()
        ),
    }
    return engine_backends.invoke_backend(
        backend,
        instructions=instructions,
        message=message,
        registry=registry,
    )


def _call_backend_with_retries(backend: str, instructions: str, message: str) -> tuple[str, str, int]:
    return engine_backends.call_backend_with_retries(
        backend,
        instructions=instructions,
        message=message,
        invoke_backend_fn=lambda backend_name, system_instructions, user_message: _invoke_backend(
            backend_name,
            system_instructions,
            user_message,
        ),
        max_attempts=max(_env_int("HELPER_BACKEND_MAX_ATTEMPTS", 2), 1),
        base_backoff=max(_env_float("HELPER_BACKOFF_SECONDS", 0.4), 0.0),
        sleeper=time.sleep,
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


def _load_conversation_turns(*, conversation_id: str, actor_key: str, scope_fingerprint: str, max_messages: int) -> list[dict]:
    key = engine_memory.conversation_cache_key(
        actor_key=actor_key,
        scope_fp=scope_fingerprint,
        conversation_id=conversation_id,
    )
    return engine_memory.load_turns(
        cache_backend=cache,
        key=key,
        max_messages=max_messages,
    )


def _save_conversation_turns(
    *,
    conversation_id: str,
    actor_key: str,
    scope_fingerprint: str,
    turns: list[dict],
    ttl_seconds: int,
) -> None:
    key = engine_memory.conversation_cache_key(
        actor_key=actor_key,
        scope_fp=scope_fingerprint,
        conversation_id=conversation_id,
    )
    engine_memory.save_turns(
        cache_backend=cache,
        key=key,
        turns=turns,
        ttl_seconds=ttl_seconds,
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


def _format_conversation_for_prompt(turns: list[dict], *, max_chars: int) -> str:
    return engine_memory.format_turns_for_prompt(turns=turns, max_chars=max_chars)


@require_GET
def healthz(request):
    backend = (os.getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()
    return JsonResponse({"ok": True, "backend": backend})


@require_POST
def chat(request):
    """POST /helper/chat"""
    started_at = time.monotonic()
    request_id = _request_id(request)
    actor = _actor_key(request)
    actor_type = actor.split(":", 1)[0] if actor else "anonymous"
    client_ip = client_ip_from_request(
        request,
        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
    )

    if not actor:
        _log_chat_event("warning", "unauthorized", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return _json_response({"error": "unauthorized"}, status=401, request_id=request_id)

    try:
        classroom_id = int(request.session.get("class_id") or 0)
    except Exception:
        classroom_id = 0
    try:
        student_id = int(request.session.get("student_id") or 0)
    except Exception:
        student_id = 0
    emit_helper_chat_access_event(
        classroom_id=classroom_id,
        student_id=student_id,
        ip_address=client_ip,
        details={"request_id": request_id, "actor_type": actor_type},
    )

    actor_limit = _env_int("HELPER_RATE_LIMIT_PER_MINUTE", 30)
    ip_limit = _env_int("HELPER_RATE_LIMIT_PER_IP_PER_MINUTE", 90)
    if not fixed_window_allow(
        f"rl:actor:{actor}:m",
        limit=actor_limit,
        window_seconds=60,
        cache_backend=cache,
        request_id=request_id,
    ):
        _log_chat_event("warning", "rate_limited_actor", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return _json_response({"error": "rate_limited"}, status=429, request_id=request_id)
    if not fixed_window_allow(
        f"rl:ip:{client_ip}:m",
        limit=ip_limit,
        window_seconds=60,
        cache_backend=cache,
        request_id=request_id,
    ):
        _log_chat_event("warning", "rate_limited_ip", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return _json_response({"error": "rate_limited"}, status=429, request_id=request_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        _log_chat_event("warning", "bad_json", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return _json_response({"error": "bad_json"}, status=400, request_id=request_id)

    deps = engine_service.ChatDeps(
        json_response=_json_response,
        log_chat_event=_log_chat_event,
        env_int=_env_int,
        env_float=_env_float,
        env_bool=_env_bool,
        redact=_redact,
        load_scope_from_token=_load_scope_from_token,
        resolve_reference_file=engine_reference.resolve_reference_file,
        load_reference_text=_load_reference_text,
        load_reference_chunks=_load_reference_chunks,
        build_reference_citations=engine_reference.build_reference_citations,
        format_reference_citations_for_prompt=engine_reference.format_reference_citations_for_prompt,
        parse_csv_list=engine_heuristics.parse_csv_list,
        contains_text_language=engine_heuristics.contains_text_language,
        is_scratch_context=engine_heuristics.is_scratch_context,
        is_piper_context=_is_piper_context,
        is_piper_hardware_question=_is_piper_hardware_question,
        build_piper_hardware_triage_text=_build_piper_hardware_triage_text,
        allowed_topic_overlap=engine_heuristics.allowed_topic_overlap,
        build_instructions=build_instructions,
        backend_circuit_is_open=_backend_circuit_is_open,
        call_backend_with_retries=_call_backend_with_retries,
        record_backend_failure=_record_backend_failure,
        reset_backend_failure_state=_reset_backend_failure_state,
        acquire_slot=acquire_slot,
        release_slot=release_slot,
        truncate_response_text=_truncate_response_text,
        normalize_conversation_id=_normalize_conversation_id,
        scope_fingerprint=_conversation_scope_fingerprint,
        load_conversation_turns=_load_conversation_turns,
        save_conversation_turns=_save_conversation_turns,
        clear_conversation_turns=_clear_conversation_turns,
        format_conversation_for_prompt=_format_conversation_for_prompt,
    )
    return engine_service.handle_chat(
        request=request,
        payload=payload,
        request_id=request_id,
        actor_key=actor,
        actor_type=actor_type,
        client_ip=client_ip,
        settings=settings,
        started_at=started_at,
        default_text_language_keywords=DEFAULT_TEXT_LANGUAGE_KEYWORDS,
        signature_expired_exc=SignatureExpired,
        bad_signature_exc=BadSignature,
        deps=deps,
    )
