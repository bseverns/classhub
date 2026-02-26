#!/usr/bin/env python3
"""Guardrail: service-layer modules must not import from view modules."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SERVICE_ROOTS = (
    Path("services/classhub/hub/services"),
    Path("services/homework_helper/tutor/engine"),
)
VIEW_IMPORT_PATTERNS = (
    re.compile(r"^\s*from\s+(\.+)?views(\.|[\s])", re.MULTILINE),
    re.compile(r"^\s*from\s+hub\.views(\.|[\s])", re.MULTILINE),
    re.compile(r"^\s*import\s+hub\.views(\.|[\s]|$)", re.MULTILINE),
)


def _iter_service_files() -> list[Path]:
    files: list[Path] = []
    for root in SERVICE_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return files


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def main() -> int:
    files = _iter_service_files()
    if not files:
        print("[service-layer-import-guard] FAIL: no service-layer files found", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in VIEW_IMPORT_PATTERNS:
            for match in pattern.finditer(text):
                line = _line_number(text, match.start())
                snippet = text[match.start() : text.find("\n", match.start())].strip()
                violations.append(f"{path}:{line}: {snippet}")

    if violations:
        print("[service-layer-import-guard] FAIL: service modules importing views detected:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print(f"[service-layer-import-guard] OK ({len(files)} service files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
