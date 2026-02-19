#!/usr/bin/env python3
"""Guardrail: internal services must not publish non-localhost ports."""

from __future__ import annotations

import re
import sys
from pathlib import Path


COMPOSE_FILE = Path("compose/docker-compose.yml")
INTERNAL_SERVICES = {"postgres", "redis", "ollama", "minio"}


def _parse_mapping(raw: str) -> str:
    text = raw.strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    return text.strip()


def _is_localhost_binding(mapping: str) -> bool:
    return mapping.startswith("127.0.0.1:") or mapping.startswith("[::1]:")


def main() -> int:
    if not COMPOSE_FILE.exists():
        print(f"[port-guard] missing compose file: {COMPOSE_FILE}", file=sys.stderr)
        return 1

    lines = COMPOSE_FILE.read_text(encoding="utf-8").splitlines()
    in_services = False
    current_service = ""
    in_ports = False
    violations: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if re.match(r"^services:\s*$", line):
            in_services = True
            current_service = ""
            in_ports = False
            continue

        if not in_services:
            continue

        # End of services block (top-level key at column 0).
        if re.match(r"^[A-Za-z0-9_-]+:\s*$", line):
            in_services = False
            current_service = ""
            in_ports = False
            continue

        service_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if service_match:
            current_service = service_match.group(1)
            in_ports = False
            continue

        if current_service not in INTERNAL_SERVICES:
            continue

        if re.match(r"^    ports:\s*$", line):
            in_ports = True
            continue

        if in_ports and re.match(r"^    [A-Za-z0-9_-]+:\s*$", line):
            in_ports = False
            continue

        if in_ports:
            port_match = re.match(r"^      -\s+(.+?)\s*$", line)
            if not port_match:
                continue
            mapping = _parse_mapping(port_match.group(1))
            if not _is_localhost_binding(mapping):
                violations.append(
                    f"{COMPOSE_FILE}:{idx} service={current_service} mapping={mapping} "
                    f"(must bind localhost only)"
                )

    if violations:
        print("[port-guard] FAIL: found non-localhost published ports on internal services:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print("[port-guard] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
