#!/usr/bin/env python3
"""Guardrail: prevent dense view functions from silently growing."""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path


VIEW_ROOTS = (
    Path("services/classhub/hub/views"),
    Path("services/homework_helper/tutor/views.py"),
)
BUDGET_FILE = Path("scripts/view_function_budgets.json")
DENSE_THRESHOLD = int(os.getenv("VIEW_FUNCTION_DENSE_THRESHOLD_LINES", "60"))
ABSOLUTE_MAX_LINES = int(os.getenv("VIEW_FUNCTION_ABSOLUTE_MAX_LINES", "320"))


def _iter_view_files() -> list[Path]:
    files: list[Path] = []
    for root in VIEW_ROOTS:
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
        elif root.is_file():
            files.append(root)
    return files


def _load_budgets() -> dict[str, int]:
    if not BUDGET_FILE.exists():
        print(f"[view-function-budget-guard] FAIL: missing budget file: {BUDGET_FILE}", file=sys.stderr)
        raise SystemExit(1)
    payload = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    budgets = payload.get("max_lines_by_function")
    if not isinstance(budgets, dict) or not budgets:
        print(f"[view-function-budget-guard] FAIL: invalid budgets in {BUDGET_FILE}", file=sys.stderr)
        raise SystemExit(1)
    normalized: dict[str, int] = {}
    for key, value in budgets.items():
        try:
            normalized[str(key)] = int(value)
        except Exception:
            print(f"[view-function-budget-guard] FAIL: invalid budget value for {key!r}: {value!r}", file=sys.stderr)
            raise SystemExit(1)
    return normalized


def _top_level_functions(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rows: list[tuple[str, int]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end_lineno = getattr(node, "end_lineno", node.lineno)
        lines = end_lineno - node.lineno + 1
        key = f"{path.as_posix()}::{node.name}"
        rows.append((key, lines))
    return rows


def main() -> int:
    files = _iter_view_files()
    if not files:
        print("[view-function-budget-guard] FAIL: no view files found", file=sys.stderr)
        return 1

    budgets = _load_budgets()
    failures: list[str] = []
    seen: set[str] = set()

    for path in files:
        for key, lines in _top_level_functions(path):
            seen.add(key)
            if lines > ABSOLUTE_MAX_LINES:
                failures.append(
                    f"{key}: {lines} lines exceeds absolute limit {ABSOLUTE_MAX_LINES}; split function"
                )
                continue
            max_lines = budgets.get(key)
            if max_lines is not None:
                if lines > max_lines:
                    failures.append(f"{key}: {lines} lines exceeds budget {max_lines}")
                continue
            if lines > DENSE_THRESHOLD:
                failures.append(
                    f"{key}: {lines} lines exceeds dense threshold {DENSE_THRESHOLD} without budget entry"
                )

    stale_entries = sorted(key for key in budgets if key not in seen)
    for key in stale_entries:
        failures.append(f"{key}: budget entry points to missing function")

    if failures:
        print("[view-function-budget-guard] FAIL: view function budget violations detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(f"[view-function-budget-guard] update {BUDGET_FILE} when intentional and documented", file=sys.stderr)
        return 1

    print(
        f"[view-function-budget-guard] OK ({len(files)} view files checked; dense threshold {DENSE_THRESHOLD}, absolute max {ABSOLUTE_MAX_LINES})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
