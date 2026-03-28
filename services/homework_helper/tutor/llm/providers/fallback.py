"""Fallback provider for disabled/test paths."""

from __future__ import annotations

from ..base import LLMBackendConfig, LLMHealthStatus, LLMProvider, LLMRequest, LLMResponse


class FallbackProvider(LLMProvider):
    def __init__(self, config: LLMBackendConfig, *, text: str):
        self.config = config
        self._text = (text or "").strip() or "Helper is temporarily unavailable."

    def chat(self, request: LLMRequest) -> LLMResponse:
        del request
        return LLMResponse(text=self._text, model="fallback")

    def healthcheck(self) -> LLMHealthStatus:
        return LLMHealthStatus(
            ok=bool(self.config.enabled),
            provider=self.config.provider,
            model="fallback",
            detail="fallback_provider",
        )
