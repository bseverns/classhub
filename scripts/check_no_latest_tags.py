#!/usr/bin/env python3
"""Guardrail: committed compose/env config must not use :latest image tags."""

from __future__ import annotations

import sys
from pathlib import Path


TARGET_PATTERNS = (
    "compose/docker-compose*.yml",
    "compose/.env.example*",
)


def _iter_target_files() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in TARGET_PATTERNS:
        for path in sorted(Path().glob(pattern)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    return paths


def _find_latest_tag_violations(path: Path) -> list[str]:
    violations: list[str] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":latest" not in stripped:
            continue
        violations.append(f"{path}:{lineno}: {stripped}")
    return violations


def main() -> int:
    targets = _iter_target_files()
    if not targets:
        print("[image-tag-guard] FAIL: no target files matched", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in targets:
        violations.extend(_find_latest_tag_violations(path))

    if violations:
        print("[image-tag-guard] FAIL: found disallowed ':latest' image tags:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("[image-tag-guard] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
