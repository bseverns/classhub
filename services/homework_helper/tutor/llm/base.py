"""Shared contracts and typed errors for helper LLM providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


class LLMError(Exception):
    """Base error for provider-layer failures."""

    code = "llm_error"
    transient = False


class LLMConfigError(LLMError):
    code = "config_error"


class LLMTimeoutError(LLMError):
    code = "timeout"
    transient = True


class LLMUpstreamUnavailableError(LLMError):
    code = "upstream_unavailable"
    transient = True


class LLMAuthError(LLMError):
    code = "auth_error"


class LLMMalformedResponseError(LLMError):
    code = "malformed_response"


@dataclass(frozen=True)
class LLMBackendConfig:
    provider: str
    enabled: bool
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: int
    max_tokens: int
    num_ctx: int
    temperature: float
    top_p: float
    log_prompt_content: bool
    redaction_enabled: bool
    healthcheck_enabled: bool


@dataclass(frozen=True)
class LLMRequest:
    instructions: str
    message: str
    request_id: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str


@dataclass(frozen=True)
class LLMHealthStatus:
    ok: bool
    provider: str
    model: str
    detail: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    config: LLMBackendConfig

    def chat(self, request: LLMRequest) -> LLMResponse:
        """Run a single non-streaming completion."""

    def healthcheck(self) -> LLMHealthStatus:
        """Probe provider reachability/config with a lightweight call."""
