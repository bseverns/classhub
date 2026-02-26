import os

from .engine import auth as engine_auth
from .engine import backends as engine_backends
from .engine import circuit as engine_circuit


def backend_circuit_is_open(*, cache_backend, backend: str, logger) -> bool:
    return engine_circuit.backend_circuit_is_open(
        cache_backend=cache_backend,
        backend=backend,
        logger=logger,
    )


def record_backend_failure(*, cache_backend, backend: str, threshold: int, ttl: int, logger) -> None:
    engine_circuit.record_backend_failure(
        cache_backend=cache_backend,
        backend=backend,
        threshold=threshold,
        ttl=ttl,
        logger=logger,
    )


def reset_backend_failure_state(*, cache_backend, backend: str, logger) -> None:
    engine_circuit.reset_backend_failure_state(
        cache_backend=cache_backend,
        backend=backend,
        logger=logger,
    )


def table_exists(*, connection, transaction_module, table_name: str) -> bool:
    return engine_auth.table_exists(
        connection=connection,
        transaction_module=transaction_module,
        table_name=table_name,
    )


def student_session_exists(
    *,
    connection,
    transaction_module,
    settings,
    student_id: int,
    class_id: int,
    table_exists_fn,
) -> bool:
    return engine_auth.student_session_exists(
        connection=connection,
        transaction_module=transaction_module,
        settings=settings,
        student_id=student_id,
        class_id=class_id,
        table_exists_fn=table_exists_fn,
    )


def actor_key(*, request, build_actor_key_fn, student_session_exists_fn) -> str:
    return engine_auth.actor_key(
        request=request,
        build_actor_key_fn=build_actor_key_fn,
        student_session_exists_fn=student_session_exists_fn,
    )


def load_scope_from_token(*, scope_token: str, max_age_seconds: int, parse_scope_token_fn) -> dict:
    return parse_scope_token_fn(scope_token, max_age_seconds=max_age_seconds)


def ollama_chat(
    *,
    base_url: str,
    model: str,
    instructions: str,
    message: str,
    timeout_seconds: int,
    temperature: float,
    top_p: float,
    num_predict: int,
) -> tuple[str, str]:
    return engine_backends.ollama_chat(
        base_url=base_url,
        model=model,
        instructions=instructions,
        message=message,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        top_p=top_p,
        num_predict=num_predict,
    )


def openai_chat(
    *,
    api_key: str | None,
    model: str,
    instructions: str,
    message: str,
    max_output_tokens: int,
) -> tuple[str, str]:
    return engine_backends.openai_chat(
        api_key=api_key,
        model=model,
        instructions=instructions,
        message=message,
        max_output_tokens=max_output_tokens,
    )


def mock_chat(*, text: str) -> tuple[str, str]:
    return engine_backends.mock_chat(text=text)


def invoke_backend(
    *,
    backend: str,
    instructions: str,
    message: str,
    ollama_chat_fn,
    openai_chat_fn,
    mock_chat_fn,
) -> tuple[str, str]:
    registry = {
        "ollama": engine_backends.CallableBackend(
            chat_fn=lambda system_instructions, user_message: ollama_chat_fn(
                os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
                system_instructions,
                user_message,
            )
        ),
        "openai": engine_backends.CallableBackend(
            chat_fn=lambda system_instructions, user_message: openai_chat_fn(
                os.getenv("OPENAI_MODEL", "gpt-5.2"),
                system_instructions,
                user_message,
            )
        ),
        "mock": engine_backends.CallableBackend(
            chat_fn=lambda _system_instructions, _user_message: mock_chat_fn()
        ),
    }
    return engine_backends.invoke_backend(
        backend,
        instructions=instructions,
        message=message,
        registry=registry,
    )


def call_backend_with_retries(
    *,
    backend: str,
    instructions: str,
    message: str,
    invoke_backend_fn,
    max_attempts: int,
    base_backoff: float,
    sleeper,
) -> tuple[str, str, int]:
    return engine_backends.call_backend_with_retries(
        backend,
        instructions=instructions,
        message=message,
        invoke_backend_fn=invoke_backend_fn,
        max_attempts=max_attempts,
        base_backoff=base_backoff,
        sleeper=sleeper,
    )


__all__ = [
    "actor_key",
    "backend_circuit_is_open",
    "call_backend_with_retries",
    "invoke_backend",
    "load_scope_from_token",
    "mock_chat",
    "ollama_chat",
    "openai_chat",
    "record_backend_failure",
    "reset_backend_failure_state",
    "student_session_exists",
    "table_exists",
]
