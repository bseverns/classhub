#!/usr/bin/env python3
"""Guardrail: view modules must use shared security header helpers.

This blocks direct response assignments for security/cache headers in view files
so policies stay centralized in helper utilities.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


SECURITY_HEADERS = (
    "Cache-Control",
    "Pragma",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
)
VIEW_ROOTS = (
    Path("services/classhub/hub/views"),
    Path("services/homework_helper/tutor/views.py"),
)
HEADER_ASSIGNMENT_RE = re.compile(
    r"""\[\s*['"](?P<header>Cache-Control|Pragma|X-Content-Type-Options|Referrer-Policy|Content-Security-Policy)['"]\s*\]""",
    re.IGNORECASE,
)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _iter_view_files() -> list[Path]:
    files: list[Path] = []
    for root in VIEW_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
        elif root.is_file():
            files.append(root)
    return files


def _collect_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for match in HEADER_ASSIGNMENT_RE.finditer(text):
        line = _line_number(text, match.start())
        header = (match.group("header") or "").strip()
        violations.append(f"{path}:{line}: direct '{header}' header assignment")
    return violations


def main() -> int:
    files = _iter_view_files()
    if not files:
        roots = ", ".join(str(root) for root in VIEW_ROOTS)
        print(f"[view-header-helper-guard] FAIL: no view files found under {roots}", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in files:
        violations.extend(_collect_violations(path))

    if violations:
        print("[view-header-helper-guard] FAIL: direct security/cache header writes detected:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        allowed = ", ".join(SECURITY_HEADERS)
        print(f"[view-header-helper-guard] use helper functions instead of writing: {allowed}", file=sys.stderr)
        return 1

    print(f"[view-header-helper-guard] OK ({len(files)} view files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
