import logging
import os
import time
import urllib.error
from functools import lru_cache

from common.helper_scope import parse_scope_token
from common.request_safety import (
    build_staff_or_student_actor_key,
    client_ip_from_request,
    fixed_window_allow,
)
from django.conf import settings
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired
from django.db import connection, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .classhub_events import emit_helper_chat_access_event
from .engine import auth as engine_auth  # re-exported patch surface in tests
from .engine import service as engine_service
from .engine.config_source import helper_config_overrides, helper_getenv
from .llm import (
    LLMAuthError,
    LLMConfigError,
    LLMMalformedResponseError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)
from .policy import build_instructions
from .queueing import acquire_slot, release_slot
from .remote_compute_control import (
    active_remote_compute_overrides_for_class,
    mark_remote_compute_degraded,
    mark_remote_compute_routed,
)
from .views_chat_deps import DEFAULT_TEXT_LANGUAGE_KEYWORDS, build_chat_deps
from .views_chat_helpers import (
    _build_class_reentry_privacy_text,
    _build_follow_up_suggestions,
    _build_helper_event_details,
    _build_mouse_only_adaptation_text,
    _build_piper_hardware_triage_text,
    _build_publish_privacy_text,
    _build_score_condition_debug_text,
    _build_teamwork_decision_text,
    _build_wellbeing_reset_text,
    _classify_intent,
    _clear_conversation_turns,
    _compact_conversation,
    _conversation_scope_fingerprint,
    _env_bool,
    _env_float,
    _env_int,
    _format_conversation_for_prompt,
    _is_class_reentry_privacy_question,
    _is_mouse_only_access_question,
    _is_piper_context,
    _is_piper_hardware_question,
    _is_publish_privacy_question,
    _is_score_condition_debug_question,
    _is_teamwork_decision_question,
    _is_wellbeing_reset_question,
    _json_response,
    _load_conversation_state,
    _load_reference_chunks,
    _load_reference_text,
    _log_chat_event,
    _normalize_conversation_id,
    _redact,
    _request_id,
    _retrieve_curriculum_citations,
    _save_conversation_state,
    _truncate_response_text,
)
from .views_chat_request import (
    enforce_rate_limits,
    load_session_ids,
    parse_chat_payload,
    resolve_actor_and_client,
)
from .views_chat_runtime import (
    actor_key as runtime_actor_key,
)
from .views_chat_runtime import (
    backend_circuit_is_open as runtime_backend_circuit_is_open,
)
from .views_chat_runtime import (
    call_backend_with_retries as runtime_call_backend_with_retries,
)
from .views_chat_runtime import (
    invoke_backend as runtime_invoke_backend,
)
from .views_chat_runtime import (
    llm_backend_requires_acknowledgement as runtime_llm_backend_requires_acknowledgement,
)
from .views_chat_runtime import (
    llm_describe_backend_public as runtime_llm_describe_backend_public,
)
from .views_chat_runtime import (
    load_scope_from_token as runtime_load_scope_from_token,
)
from .views_chat_runtime import (
    mock_chat as runtime_mock_chat,
)
from .views_chat_runtime import (
    ollama_chat as runtime_ollama_chat,
)
from .views_chat_runtime import (
    openai_chat as runtime_openai_chat,
)
from .views_chat_runtime import (
    openai_compatible_chat as runtime_openai_compatible_chat,
)
from .views_chat_runtime import (
    record_backend_failure as runtime_record_backend_failure,
)
from .views_chat_runtime import (
    reset_backend_failure_state as runtime_reset_backend_failure_state,
)
from .views_chat_runtime import (
    student_session_exists as runtime_student_session_exists,
)
from .views_chat_runtime import (
    table_exists as runtime_table_exists,
)
from .views_internal_rag_status import internal_rag_status
from .views_remote_compute import internal_remote_compute_control, internal_remote_compute_status
from .views_reset import reset_class_conversations

logger = logging.getLogger(__name__)


def _backend_circuit_is_open(backend: str) -> bool:
    return runtime_backend_circuit_is_open(
        cache_backend=cache,
        backend=backend,
        logger=logger,
    )


def _record_backend_failure(backend: str) -> None:
    threshold = max(_env_int("HELPER_CIRCUIT_BREAKER_FAILURES", 5), 1)
    ttl = max(_env_int("HELPER_CIRCUIT_BREAKER_TTL_SECONDS", 30), 1)
    runtime_record_backend_failure(
        cache_backend=cache,
        backend=backend,
        threshold=threshold,
        ttl=ttl,
        logger=logger,
    )


def _reset_backend_failure_state(backend: str) -> None:
    runtime_reset_backend_failure_state(
        cache_backend=cache,
        backend=backend,
        logger=logger,
    )


@lru_cache(maxsize=32)
def _table_exists(table_name: str) -> bool:
    """Best-effort table existence check without raising for missing tables."""
    return runtime_table_exists(
        connection=connection,
        transaction_module=transaction,
        table_name=table_name,
    )


def _student_session_exists(student_id: int, class_id: int) -> bool:
    """Validate student session against shared Class Hub table when available."""
    return runtime_student_session_exists(
        connection=connection,
        transaction_module=transaction,
        settings=settings,
        student_id=student_id,
        class_id=class_id,
        table_exists_fn=_table_exists,
    )


def _actor_key(request) -> str:
    return runtime_actor_key(
        request=request,
        build_actor_key_fn=build_staff_or_student_actor_key,
        student_session_exists_fn=_student_session_exists,
    )


def _load_scope_from_token(scope_token: str, *, max_age_seconds: int) -> dict:
    return runtime_load_scope_from_token(
        scope_token=scope_token,
        max_age_seconds=max_age_seconds,
        scope_signing_key=str(getattr(settings, "HELPER_SCOPE_SIGNING_KEY", "") or ""),
        parse_scope_token_fn=parse_scope_token,
    )


def _ollama_chat(base_url: str, model: str, instructions: str, message: str) -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return runtime_ollama_chat(
        base_url=base_url,
        model=model,
        instructions=instructions,
        message=message,
        timeout_seconds=_env_int("OLLAMA_TIMEOUT_SECONDS", 30),
        temperature=float(helper_getenv("OLLAMA_TEMPERATURE", "0.2")),
        top_p=float(helper_getenv("OLLAMA_TOP_P", "0.9")),
        num_ctx=_env_int("OLLAMA_NUM_CTX", 0),
        num_predict=_env_int("OLLAMA_NUM_PREDICT", 0),
    )


def _openai_chat(model: str, instructions: str, message: str) -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return runtime_openai_chat(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model=model,
        instructions=instructions,
        message=message,
        max_output_tokens=_env_int("OPENAI_MAX_OUTPUT_TOKENS", 0),
    )


def _mock_chat() -> tuple[str, str]:
    """Compatibility shim for existing test patch targets."""
    return runtime_mock_chat(text=helper_getenv("HELPER_MOCK_RESPONSE_TEXT", ""))


def _openai_compatible_chat(*, instructions: str, message: str) -> tuple[str, str]:
    return runtime_openai_compatible_chat(
        instructions=instructions,
        message=message,
    )


def _invoke_backend(backend: str, instructions: str, message: str) -> tuple[str, str]:
    return runtime_invoke_backend(
        backend=backend,
        instructions=instructions,
        message=message,
        ollama_chat_fn=_ollama_chat,
        openai_chat_fn=_openai_chat,
        mock_chat_fn=_mock_chat,
        openai_compatible_chat_fn=_openai_compatible_chat,
    )


def _call_backend_with_retries(backend: str, instructions: str, message: str) -> tuple[str, str, int]:
    return runtime_call_backend_with_retries(
        backend=backend,
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


def _call_backend_with_optional_remote_fallback(
    *,
    backend_name: str,
    instructions: str,
    model_message: str,
    remote_overrides,
    classroom_id: int | None,
    local_backend: str,
    request_id: str,
    actor_type: str,
):
    if not remote_overrides:
        return _call_backend_with_retries(backend_name, instructions, model_message)
    with helper_config_overrides(remote_overrides):
        try:
            result = _call_backend_with_retries(backend_name, instructions, model_message)
            mark_remote_compute_routed(class_id=classroom_id)
            return result
        except (
            LLMAuthError,
            LLMConfigError,
            LLMMalformedResponseError,
            LLMTimeoutError,
            LLMUpstreamUnavailableError,
            RuntimeError,
            urllib.error.URLError,
            urllib.error.HTTPError,
            ValueError,
        ) as exc:
            _log_chat_event(
                "warning",
                "remote_compute_fallback_local",
                request_id=request_id,
                actor_type=actor_type,
                backend=backend_name,
                class_id=classroom_id,
                error_type=exc.__class__.__name__,
            )
            mark_remote_compute_degraded(class_id=classroom_id, error_code=exc.__class__.__name__)
    return _call_backend_with_retries(local_backend, instructions, model_message)


def _emit_helper_event(
    *,
    response,
    classroom_id: int | None,
    student_id: int | None,
    client_ip: str,
    request_id: str,
    actor_type: str,
    backend: str,
) -> None:
    emit_helper_chat_access_event(
        classroom_id=classroom_id,
        student_id=student_id,
        ip_address=client_ip,
        details=_build_helper_event_details(
            response=response,
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        ),
    )


@require_GET
def healthz(request):
    backend = (helper_getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()
    backend_info = runtime_llm_describe_backend_public(backend=backend)
    return JsonResponse({"ok": True, "backend": backend, "llm": backend_info})


@require_POST
def chat(request):
    """POST /helper/chat"""
    started_at = time.monotonic()
    request_id = _request_id(request)
    actor, actor_type, client_ip = resolve_actor_and_client(
        request=request,
        actor_key_fn=_actor_key,
        settings=settings,
        client_ip_from_request_fn=client_ip_from_request,
    )
    backend = (helper_getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()

    if not actor:
        _log_chat_event("warning", "unauthorized", request_id=request_id, actor_type=actor_type, ip=client_ip)
        return _json_response({"error": "unauthorized"}, status=401, request_id=request_id)

    classroom_id, student_id = load_session_ids(request)
    remote_overrides = active_remote_compute_overrides_for_class(class_id=classroom_id)
    local_backend = (helper_getenv("HELPER_LLM_BACKEND", "ollama") or "ollama").lower()

    actor_limit = _env_int("HELPER_RATE_LIMIT_PER_MINUTE", 30)
    ip_limit = _env_int("HELPER_RATE_LIMIT_PER_IP_PER_MINUTE", 90)
    rate_limit_response = enforce_rate_limits(
        actor=actor,
        actor_type=actor_type,
        client_ip=client_ip,
        request_id=request_id,
        actor_limit=actor_limit,
        ip_limit=ip_limit,
        fixed_window_allow_fn=fixed_window_allow,
        cache_backend=cache,
        log_chat_event_fn=_log_chat_event,
        json_response_fn=_json_response,
    )
    if rate_limit_response is not None:
        _emit_helper_event(
            response=rate_limit_response,
            classroom_id=classroom_id,
            student_id=student_id,
            client_ip=client_ip,
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        return rate_limit_response

    payload, bad_payload_response = parse_chat_payload(
        request_body=request.body,
        request_id=request_id,
        actor_type=actor_type,
        client_ip=client_ip,
        log_chat_event_fn=_log_chat_event,
        json_response_fn=_json_response,
    )
    if bad_payload_response is not None:
        response = bad_payload_response
        _emit_helper_event(
            response=response,
            classroom_id=classroom_id,
            student_id=student_id,
            client_ip=client_ip,
            request_id=request_id,
            actor_type=actor_type,
            backend=backend,
        )
        return response

    deps = build_chat_deps(
        json_response_fn=_json_response,
        log_chat_event_fn=_log_chat_event,
        env_int_fn=_env_int,
        env_float_fn=_env_float,
        env_bool_fn=_env_bool,
        redact_fn=_redact,
        load_scope_from_token_fn=_load_scope_from_token,
        load_reference_text_fn=_load_reference_text,
        load_reference_chunks_fn=_load_reference_chunks,
        retrieve_curriculum_citations_fn=_retrieve_curriculum_citations,
        is_piper_context_fn=_is_piper_context,
        is_piper_hardware_question_fn=_is_piper_hardware_question,
        build_piper_hardware_triage_text_fn=_build_piper_hardware_triage_text,
        is_mouse_only_access_question_fn=_is_mouse_only_access_question,
        build_mouse_only_adaptation_text_fn=_build_mouse_only_adaptation_text,
        is_teamwork_decision_question_fn=_is_teamwork_decision_question,
        build_teamwork_decision_text_fn=_build_teamwork_decision_text,
        is_class_reentry_privacy_question_fn=_is_class_reentry_privacy_question,
        build_class_reentry_privacy_text_fn=_build_class_reentry_privacy_text,
        is_publish_privacy_question_fn=_is_publish_privacy_question,
        build_publish_privacy_text_fn=_build_publish_privacy_text,
        is_score_condition_debug_question_fn=_is_score_condition_debug_question,
        build_score_condition_debug_text_fn=_build_score_condition_debug_text,
        is_wellbeing_reset_question_fn=_is_wellbeing_reset_question,
        build_wellbeing_reset_text_fn=_build_wellbeing_reset_text,
        build_instructions_fn=build_instructions,
        backend_circuit_is_open_fn=_backend_circuit_is_open,
        llm_backend_requires_acknowledgement_fn=lambda backend: runtime_llm_backend_requires_acknowledgement(
            backend=backend
        ),
        call_backend_with_retries_fn=(
            lambda backend_name, instructions, model_message: _call_backend_with_optional_remote_fallback(
                backend_name=backend_name,
                instructions=instructions,
                model_message=model_message,
                remote_overrides=remote_overrides,
                classroom_id=classroom_id,
                local_backend=local_backend,
                request_id=request_id,
                actor_type=actor_type,
            )
        ),
        record_backend_failure_fn=_record_backend_failure,
        reset_backend_failure_state_fn=_reset_backend_failure_state,
        acquire_slot_fn=acquire_slot,
        release_slot_fn=release_slot,
        truncate_response_text_fn=_truncate_response_text,
        normalize_conversation_id_fn=_normalize_conversation_id,
        scope_fingerprint_fn=_conversation_scope_fingerprint,
        load_conversation_state_fn=_load_conversation_state,
        save_conversation_state_fn=_save_conversation_state,
        compact_conversation_fn=_compact_conversation,
        clear_conversation_turns_fn=_clear_conversation_turns,
        format_conversation_for_prompt_fn=_format_conversation_for_prompt,
        classify_intent_fn=_classify_intent,
        build_follow_up_suggestions_fn=_build_follow_up_suggestions,
    )
    with helper_config_overrides(remote_overrides):
        response = engine_service.handle_chat(
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
    _emit_helper_event(
        response=response,
        classroom_id=classroom_id,
        student_id=student_id,
        client_ip=client_ip,
        request_id=request_id,
        actor_type=actor_type,
        backend=backend,
    )
    return response


__all__ = [
    "chat",
    "engine_auth",
    "healthz",
    "internal_rag_status",
    "internal_remote_compute_control",
    "internal_remote_compute_status",
    "reset_class_conversations",
]
