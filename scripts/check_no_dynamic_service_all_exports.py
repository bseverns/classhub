#!/usr/bin/env python3
"""Guardrail: service modules must not define dynamic __all__ exports."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SERVICE_ROOTS = (
    Path("services/classhub/hub/services"),
    Path("services/homework_helper/tutor/engine"),
)
DYNAMIC_ALL_RE = re.compile(r"__all__\s*=\s*\[\s*name\s+for\s+name\s+in\s+globals\(\)", re.IGNORECASE)


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
        print("[service-all-export-guard] FAIL: no service files found", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in DYNAMIC_ALL_RE.finditer(text):
            line = _line_number(text, match.start())
            violations.append(f"{path}:{line}: dynamic __all__ export")

    if violations:
        print("[service-all-export-guard] FAIL: dynamic __all__ exports detected:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print(f"[service-all-export-guard] OK ({len(files)} service files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
