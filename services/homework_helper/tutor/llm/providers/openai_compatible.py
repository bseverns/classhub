"""Future-swap provider for private OpenAI-compatible servers such as vLLM."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

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

_DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "ClassHub-HomeworkHelper/1.0",
}


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, config: LLMBackendConfig):
        self.config = config

    def chat(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.message},
            ],
            "temperature": self.config.temperature,
            "stream": False,
        }
        if self.config.max_tokens > 0:
            payload["max_tokens"] = self.config.max_tokens
        parsed = self._request_json("/v1/chat/completions", payload)
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("chat_completions_not_object")
        choices = parsed.get("choices") or []
        if not isinstance(choices, list) or not choices:
            raise LLMMalformedResponseError("chat_completions_missing_choices")
        first = choices[0] or {}
        message = first.get("message") or {}
        if not isinstance(message, dict):
            raise LLMMalformedResponseError("chat_completions_missing_message")
        text = str(message.get("content") or "").strip()
        if not text:
            raise LLMMalformedResponseError("chat_completions_missing_content")
        model = str(parsed.get("model") or self.config.model).strip() or self.config.model
        return LLMResponse(text=text, model=model)

    def healthcheck(self) -> LLMHealthStatus:
        parsed = self._request_json("/v1/models", None)
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("models_not_object")
        model_present = False
        data = parsed.get("data") or []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                if str(item.get("id") or "").strip() == self.config.model:
                    model_present = True
                    break
        detail = "openai_compatible_reachable"
        if self.config.model and not model_present:
            detail = "model_not_listed"
        return LLMHealthStatus(
            ok=True,
            provider=self.config.provider,
            model=self.config.model,
            detail=detail,
            metadata={"model_present": model_present},
        )

    def _request_json(self, path: str, payload: dict | None) -> dict | list:
        if not self.config.base_url.lower().startswith(("http://", "https://")):
            raise LLMConfigError("invalid_base_url_scheme")
        if not self.config.api_key:
            raise LLMConfigError("missing_api_key")
        url = self.config.base_url.rstrip("/") + path
        headers = {
            **_DEFAULT_HEADERS,
            "Authorization": f"Bearer {self.config.api_key}",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=int(self.config.timeout_seconds)) as resp:  # nosec B310
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise LLMAuthError(f"openai_compatible_http_{exc.code}") from exc
            if exc.code in {408, 409, 425, 429, 500, 502, 503, 504}:
                raise LLMUpstreamUnavailableError(f"openai_compatible_http_{exc.code}") from exc
            raise LLMConfigError(f"openai_compatible_http_{exc.code}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError):
                raise LLMTimeoutError("openai_compatible_timeout") from exc
            if isinstance(reason, socket.timeout):
                raise LLMTimeoutError("openai_compatible_timeout") from exc
            raise LLMUpstreamUnavailableError("openai_compatible_transport_error") from exc
        except TimeoutError as exc:
            raise LLMTimeoutError("openai_compatible_timeout") from exc
        except socket.timeout as exc:
            raise LLMTimeoutError("openai_compatible_timeout") from exc
        try:
            return json.loads(body)
        except Exception as exc:
            raise LLMMalformedResponseError("openai_compatible_invalid_json") from exc
