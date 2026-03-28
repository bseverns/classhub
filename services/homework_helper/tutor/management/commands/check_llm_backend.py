from __future__ import annotations

import json
import socket
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError

from ...llm import (
    LLMError,
    describe_backend,
    healthcheck_provider,
    resolve_backend_name,
)


class Command(BaseCommand):
    help = "Check helper LLM backend config, DNS, reachability, and optional tiny completion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--backend",
            default="",
            help="Override backend name (default: env-driven current backend).",
        )
        parser.add_argument(
            "--probe-chat",
            action="store_true",
            help="Run a tiny completion after the health probe.",
        )
        parser.add_argument(
            "--require-healthy",
            action="store_true",
            help="Exit non-zero when the configured backend is unhealthy.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON only.",
        )

    def handle(self, *args, **options):
        backend = (options.get("backend") or "").strip().lower() or resolve_backend_name()
        if backend == "openai_responses":
            payload = {
                "ok": True,
                "backend": backend,
                "detail": "legacy_openai_responses_backend_not_probed",
            }
            self._write(payload, as_json=bool(options.get("json")))
            return

        details = describe_backend(backend)
        payload: dict[str, object] = {
            "ok": False,
            "backend": backend,
            "enabled": bool(details.get("enabled")),
            "provider": details.get("provider", backend),
            "model": details.get("model", ""),
            "base_url": details.get("base_url", ""),
            "remote_private": bool(details.get("remote_private")),
        }

        if not payload["enabled"]:
            payload["detail"] = "llm_disabled"
            self._write(payload, as_json=bool(options.get("json")))
            if options.get("require_healthy"):
                raise CommandError("LLM is disabled.")
            return

        host = str(urlsplit(str(payload["base_url"] or "")).hostname or "").strip()
        if host:
            try:
                addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
            except Exception as exc:
                payload["detail"] = "dns_resolution_failed"
                payload["dns_error"] = exc.__class__.__name__
                self._write(payload, as_json=bool(options.get("json")))
                if options.get("require_healthy"):
                    raise CommandError(f"Unable to resolve LLM host '{host}': {exc}") from exc
                return
            payload["resolved_host"] = host
            payload["resolved_addresses"] = addresses

        try:
            status = healthcheck_provider(backend, probe_chat=bool(options.get("probe_chat")))
        except LLMError as exc:
            payload["detail"] = exc.code
            self._write(payload, as_json=bool(options.get("json")))
            if options.get("require_healthy"):
                raise CommandError(f"LLM backend check failed: {exc.code}") from exc
            return

        payload["ok"] = bool(status.ok)
        payload["detail"] = status.detail
        payload["health_metadata"] = dict(status.metadata or {})
        if options.get("require_healthy") and not status.ok:
            self._write(payload, as_json=bool(options.get("json")))
            raise CommandError(f"LLM backend unhealthy: {status.detail}")
        self._write(payload, as_json=bool(options.get("json")))

    def _write(self, payload: dict[str, object], *, as_json: bool) -> None:
        if as_json:
            self.stdout.write(json.dumps(payload, sort_keys=True))
            return
        line = json.dumps(payload, sort_keys=True)
        if payload.get("ok"):
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(line))
