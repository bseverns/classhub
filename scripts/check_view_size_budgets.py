#!/usr/bin/env python3
"""Guardrail: prevent dense view modules from silently growing.

Enforces per-file line budgets for known dense view modules and requires an
explicit budget entry when a new dense view file is introduced.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


VIEW_ROOTS = (
    Path("services/classhub/hub/views"),
    Path("services/homework_helper/tutor/views.py"),
)
BUDGET_FILE = Path("scripts/view_size_budgets.json")
DENSE_THRESHOLD = int(os.getenv("VIEW_DENSE_THRESHOLD_LINES", "350"))
ABSOLUTE_MAX_LINES = int(os.getenv("VIEW_ABSOLUTE_MAX_LINES", "1000"))


def _iter_view_files() -> list[Path]:
    files: list[Path] = []
    for root in VIEW_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
        elif root.is_file():
            files.append(root)
    return files


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _load_budgets() -> dict[str, int]:
    if not BUDGET_FILE.exists():
        print(f"[view-size-guard] FAIL: missing budget file: {BUDGET_FILE}", file=sys.stderr)
        raise SystemExit(1)
    payload = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    budgets = payload.get("max_lines_by_file")
    if not isinstance(budgets, dict) or not budgets:
        print(f"[view-size-guard] FAIL: invalid budgets in {BUDGET_FILE}", file=sys.stderr)
        raise SystemExit(1)
    normalized: dict[str, int] = {}
    for key, value in budgets.items():
        try:
            normalized[str(key)] = int(value)
        except Exception:
            print(f"[view-size-guard] FAIL: invalid budget value for {key!r}: {value!r}", file=sys.stderr)
            raise SystemExit(1)
    return normalized


def main() -> int:
    files = _iter_view_files()
    if not files:
        print("[view-size-guard] FAIL: no view files found", file=sys.stderr)
        return 1

    budgets = _load_budgets()
    files_by_rel = {path.as_posix(): path for path in files}

    failures: list[str] = []
    for rel_path, path in files_by_rel.items():
        lines = _line_count(path)
        if lines > ABSOLUTE_MAX_LINES:
            failures.append(
                f"{rel_path}: {lines} lines exceeds absolute limit {ABSOLUTE_MAX_LINES}; split module"
            )
            continue
        max_lines = budgets.get(rel_path)
        if max_lines is not None:
            if lines > max_lines:
                failures.append(f"{rel_path}: {lines} lines exceeds budget {max_lines}")
            continue
        if lines > DENSE_THRESHOLD:
            failures.append(
                f"{rel_path}: {lines} lines exceeds dense threshold {DENSE_THRESHOLD} without budget entry"
            )

    stale_entries = sorted(path for path in budgets if path not in files_by_rel)
    for path in stale_entries:
        failures.append(f"{path}: budget entry points to missing file")

    if failures:
        print("[view-size-guard] FAIL: view size budget violations detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(f"[view-size-guard] update {BUDGET_FILE} when intentional and documented", file=sys.stderr)
        return 1

    print(
        f"[view-size-guard] OK ({len(files)} view files checked; dense threshold {DENSE_THRESHOLD}, absolute max {ABSOLUTE_MAX_LINES})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
