"""Private/server-to-server Ollama provider."""

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


class OllamaProvider(LLMProvider):
    def __init__(self, config: LLMBackendConfig):
        self.config = config

    def chat(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.message},
            ],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
            },
        }
        if self.config.max_tokens > 0:
            payload["options"]["num_predict"] = self.config.max_tokens
        if self.config.num_ctx > 0:
            payload["options"]["num_ctx"] = self.config.num_ctx
        parsed = self._request_json("/api/chat", payload)
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("ollama_response_not_object")
        message = parsed.get("message") or {}
        text = ""
        if isinstance(message, dict):
            text = str(message.get("content") or "").strip()
        if not text:
            text = str(parsed.get("response") or "").strip()
        if not text:
            raise LLMMalformedResponseError("ollama_missing_message_content")
        model = str(parsed.get("model") or self.config.model).strip() or self.config.model
        return LLMResponse(text=text, model=model)

    def healthcheck(self) -> LLMHealthStatus:
        parsed = self._request_json("/api/tags", None)
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("ollama_tags_not_object")
        models = parsed.get("models") or []
        model_present = False
        if isinstance(models, list):
            for item in models:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if name == self.config.model:
                    model_present = True
                    break
        detail = "ollama_reachable"
        if self.config.model and not model_present:
            detail = "ollama_model_not_listed"
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
        url = self.config.base_url.rstrip("/") + path
        headers = dict(_DEFAULT_HEADERS)
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=int(self.config.timeout_seconds)) as resp:  # nosec B310
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise LLMAuthError(f"ollama_http_{exc.code}") from exc
            if exc.code in {408, 409, 425, 429, 500, 502, 503, 504}:
                raise LLMUpstreamUnavailableError(f"ollama_http_{exc.code}") from exc
            raise LLMConfigError(f"ollama_http_{exc.code}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError):
                raise LLMTimeoutError("ollama_timeout") from exc
            if isinstance(reason, socket.timeout):
                raise LLMTimeoutError("ollama_timeout") from exc
            raise LLMUpstreamUnavailableError("ollama_transport_error") from exc
        except TimeoutError as exc:
            raise LLMTimeoutError("ollama_timeout") from exc
        except socket.timeout as exc:
            raise LLMTimeoutError("ollama_timeout") from exc
        try:
            return json.loads(body)
        except Exception as exc:
            raise LLMMalformedResponseError("ollama_invalid_json") from exc
