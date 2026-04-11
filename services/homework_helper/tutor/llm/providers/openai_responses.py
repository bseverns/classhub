"""Hosted OpenAI Responses API provider."""

from __future__ import annotations

from ..base import (
    LLMAuthError,
    LLMBackendConfig,
    LLMConfigError,
    LLMHealthStatus,
    LLMMalformedResponseError,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)


class OpenAIResponsesProvider(LLMProvider):
    def __init__(self, config: LLMBackendConfig):
        self.config = config

    def chat(self, request: LLMRequest) -> LLMResponse:
        client = self._build_client()
        create_kwargs = {
            "model": self.config.model,
            "instructions": request.instructions,
            "input": request.message,
        }
        if self.config.max_tokens > 0:
            create_kwargs["max_output_tokens"] = self.config.max_tokens
        try:
            response = client.responses.create(**create_kwargs)
        except Exception as exc:
            raise self._map_error(exc) from exc
        text = str(getattr(response, "output_text", "") or "").strip()
        if not text:
            raise LLMMalformedResponseError("openai_responses_missing_output_text")
        model = str(getattr(response, "model", "") or self.config.model).strip() or self.config.model
        return LLMResponse(text=text, model=model)

    def healthcheck(self) -> LLMHealthStatus:
        client = self._build_client()
        try:
            models = client.models.list()
        except Exception as exc:
            raise self._map_error(exc) from exc
        model_present = False
        for item in getattr(models, "data", []) or []:
            if str(getattr(item, "id", "") or "").strip() == self.config.model:
                model_present = True
                break
        detail = "openai_responses_reachable"
        if self.config.model and not model_present:
            detail = "openai_responses_model_not_listed"
        return LLMHealthStatus(
            ok=True,
            provider=self.config.provider,
            model=self.config.model,
            detail=detail,
            metadata={"model_present": model_present},
        )

    def _build_client(self):
        if not self.config.api_key:
            raise LLMConfigError("missing_api_key")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency
            raise LLMConfigError("openai_not_installed") from exc
        return OpenAI(
            api_key=self.config.api_key,
            timeout=max(int(self.config.timeout_seconds), 1),
        )

    def _map_error(self, exc: Exception) -> Exception:
        name = exc.__class__.__name__
        status_code = getattr(exc, "status_code", None)
        if name in {"AuthenticationError", "PermissionDeniedError"} or status_code in {401, 403}:
            return LLMAuthError("openai_responses_auth_error")
        if name in {"APITimeoutError"}:
            return LLMTimeoutError("openai_responses_timeout")
        if name in {"APIConnectionError"}:
            return LLMUpstreamUnavailableError("openai_responses_transport_error")
        if name in {"RateLimitError", "InternalServerError"} or status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
            return LLMUpstreamUnavailableError("openai_responses_upstream_error")
        if name in {"BadRequestError", "NotFoundError", "ConflictError", "UnprocessableEntityError"}:
            return LLMConfigError("openai_responses_request_error")
        if isinstance(exc, TimeoutError):
            return LLMTimeoutError("openai_responses_timeout")
        return LLMConfigError("openai_responses_request_error")
