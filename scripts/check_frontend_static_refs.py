#!/usr/bin/env python3
"""Guardrail: classhub template static CSS/JS references must resolve."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TEMPLATES_ROOT = Path("services/classhub/templates")
STATIC_ROOT = Path("services/classhub/hub/static")
STATIC_TAG_PATTERN = re.compile(r"""{%\s*static\s+['"]([^'"]+)['"]\s*%}""")
LOCAL_PREFIXES = ("css/", "js/")


def _iter_templates() -> list[Path]:
    return sorted(TEMPLATES_ROOT.rglob("*.html"))


def _collect_missing_refs(path: Path) -> list[str]:
    missing: list[str] = []
    content = path.read_text(encoding="utf-8")
    for ref in STATIC_TAG_PATTERN.findall(content):
        normalized = ref.strip()
        if not normalized.startswith(LOCAL_PREFIXES):
            continue
        target = STATIC_ROOT / normalized
        if not target.exists():
            missing.append(f"{path}: missing static target '{normalized}' (expected {target})")
    return missing


def main() -> int:
    if not TEMPLATES_ROOT.exists():
        print(f"[frontend-static-guard] FAIL: missing templates root: {TEMPLATES_ROOT}", file=sys.stderr)
        return 1
    if not STATIC_ROOT.exists():
        print(f"[frontend-static-guard] FAIL: missing static root: {STATIC_ROOT}", file=sys.stderr)
        return 1

    templates = _iter_templates()
    if not templates:
        print("[frontend-static-guard] FAIL: no template files found", file=sys.stderr)
        return 1

    violations: list[str] = []
    for template_path in templates:
        violations.extend(_collect_missing_refs(template_path))

    if violations:
        print("[frontend-static-guard] FAIL: unresolved static references found:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print(f"[frontend-static-guard] OK ({len(templates)} templates checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
