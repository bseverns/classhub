#!/usr/bin/env python3
"""Guardrail: keep teacher top-task choreography wired into /teach."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TOP_TASKS_DOC = Path("docs/TEACHER_TOP_TASKS.md")
TEACH_HOME_TEMPLATE = Path("services/classhub/templates/teach_home.html")
START_HERE_TEMPLATE = Path("services/classhub/templates/includes/teach_home/start_here_today.html")
SETUP_SECTIONS_TEMPLATE = Path("services/classhub/templates/includes/teach_home/setup_sections.html")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _validate_top_tasks_doc(text: str, failures: list[str]) -> None:
    rows = re.findall(r"^\|\s*(\d+)\s*\|", text, flags=re.MULTILINE)
    numeric_rows = [int(row) for row in rows if row.isdigit()]
    expected = list(range(1, 11))
    if numeric_rows[:10] != expected:
        failures.append(
            f"{TOP_TASKS_DOC}: expected task-map rows 1..10 in order; found {numeric_rows[:10] or 'none'}"
        )


def _require_snippets(text: str, *, path: Path, snippets: list[str], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing snippet {snippet!r}")


def main() -> int:
    failures: list[str] = []
    try:
        top_tasks_text = _read(TOP_TASKS_DOC)
        teach_home_text = _read(TEACH_HOME_TEMPLATE)
        start_here_text = _read(START_HERE_TEMPLATE)
        setup_sections_text = _read(SETUP_SECTIONS_TEMPLATE)
    except RuntimeError as exc:
        print(f"[teacher-top-tasks-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    _validate_top_tasks_doc(top_tasks_text, failures)
    _require_snippets(
        teach_home_text,
        path=TEACH_HOME_TEMPLATE,
        snippets=['{% include "includes/teach_home/start_here_today.html" %}'],
        failures=failures,
    )
    _require_snippets(
        start_here_text,
        path=START_HERE_TEMPLATE,
        snippets=[
            "Start Here Today",
            "Daily teaching workflows (tasks 1-8)",
            "Operator + policy workflows (tasks 9-10)",
            "/teach/lessons?class_id={{ teacher_start_class.id }}",
            "/teach/class/{{ teacher_start_class.id }}/join-card",
            "/teach/class/{{ teacher_start_class.id }}/export-summary-csv",
        ],
        failures=failures,
    )
    _require_snippets(
        setup_sections_text,
        path=SETUP_SECTIONS_TEMPLATE,
        snippets=[
            "Superuser operator + policy workflows live behind Show operator tools.",
        ],
        failures=failures,
    )

    if failures:
        print("[teacher-top-tasks-guard] FAIL: teacher top-task contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[teacher-top-tasks-guard] keep docs/TEACHER_TOP_TASKS.md and /teach choreography aligned", file=sys.stderr)
        return 1

    print("[teacher-top-tasks-guard] OK (top-task doc + /teach choreography contracts are aligned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
