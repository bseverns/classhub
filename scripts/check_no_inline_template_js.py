#!/usr/bin/env python3
"""Guardrail: fail when HTML templates include inline JS execution surfaces.

This blocks:
- <script> tags without a src attribute
- inline event handler attributes like onclick= / onsubmit=
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


SERVICES_ROOT = Path("services")
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*\bsrc\b)[^>]*>", re.IGNORECASE)
INLINE_HANDLER_RE = re.compile(r"\b(on[a-z]+)\s*=\s*['\"]", re.IGNORECASE)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _iter_template_files() -> list[Path]:
    roots = sorted(path for path in SERVICES_ROOT.rglob("templates") if path.is_dir())
    files: list[Path] = []
    for root in roots:
        files.extend(sorted(root.rglob("*.html")))
    return files


def _collect_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []

    for match in INLINE_SCRIPT_RE.finditer(text):
        line = _line_number(text, match.start())
        violations.append(f"{path}:{line}: inline <script> tag without src")

    for match in INLINE_HANDLER_RE.finditer(text):
        line = _line_number(text, match.start())
        attr = (match.group(1) or "").lower()
        violations.append(f"{path}:{line}: inline event handler attribute '{attr}'")

    return violations


def main() -> int:
    if not SERVICES_ROOT.exists():
        print(f"[inline-template-js-guard] FAIL: missing services root: {SERVICES_ROOT}", file=sys.stderr)
        return 1

    templates = _iter_template_files()
    if not templates:
        print("[inline-template-js-guard] FAIL: no template files found", file=sys.stderr)
        return 1

    violations: list[str] = []
    for template in templates:
        violations.extend(_collect_violations(template))

    if violations:
        print("[inline-template-js-guard] FAIL: inline JS surfaces detected:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print(f"[inline-template-js-guard] OK ({len(templates)} templates checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
