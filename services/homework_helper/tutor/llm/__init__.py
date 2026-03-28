"""Provider-based LLM service layer for Homework Helper."""

from .base import (
    LLMAuthError,
    LLMBackendConfig,
    LLMConfigError,
    LLMError,
    LLMHealthStatus,
    LLMMalformedResponseError,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)
from .service import (
    backend_requires_acknowledgement,
    chat_with_provider,
    describe_backend,
    healthcheck_provider,
    resolve_backend_name,
    resolve_backend_runtime_config,
)

__all__ = [
    "LLMAuthError",
    "LLMBackendConfig",
    "LLMConfigError",
    "LLMError",
    "LLMHealthStatus",
    "LLMMalformedResponseError",
    "LLMRequest",
    "LLMResponse",
    "LLMTimeoutError",
    "LLMUpstreamUnavailableError",
    "backend_requires_acknowledgement",
    "chat_with_provider",
    "describe_backend",
    "healthcheck_provider",
    "resolve_backend_name",
    "resolve_backend_runtime_config",
]
