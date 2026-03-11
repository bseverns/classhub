#!/usr/bin/env python3
"""Guardrail: keep key docs claims aligned with current repository state."""

from __future__ import annotations

import re
import sys
from pathlib import Path


RISK_REGISTER_PATH = Path("docs/MAINTENANCE_RISK_REGISTER.md")
PUBLIC_OVERVIEW_PATH = Path("docs/PUBLIC_OVERVIEW.md")
CURRENT_STATE_PATH = Path("docs/CURRENT_STATE.md")
SHOTLIST_PATH = Path("press/screenshots/SHOTLIST.md")
PLACEHOLDERS_PATH = Path("press/screenshots/PLACEHOLDERS.md")

RISK_LINE_COUNT_PATHS = (
    Path("services/classhub/templates/teach_home.html"),
    Path("services/classhub/templates/teach_class.html"),
    Path("services/classhub/hub/views/teacher_parts/roster_class.py"),
)

SHOTLIST_EXPECTED_FILES = [
    "01-student-join.png",
    "02-student-class-view.png",
    "03-teacher-dashboard.png",
    "04-teacher-lesson-tracker.png",
    "05-lesson-with-helper.png",
    "06-submission-dropbox.png",
    "07-admin-login.png",
    "08-health-checks-terminal.png",
    "09-teacher-profile-tab.png",
    "10-org-management-tab.png",
    "11-invite-only-enrollment.png",
    "12-certificate-eligibility.png",
    "13-a11y-smoke-terminal.png",
    "14-student-compact-view.png",
    "15-lesson-helper-collapsed.png",
    "16-student-standard-view.png",
    "17-student-expanded-view.png",
    "18-teacher-landing-editor.png",
    "19-rbac-tools-tab.png",
    "20-data-lifespan-evidence.png",
    "21-data-lifespan-export-terminal.png",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _validate_risk_register_line_counts(failures: list[str]) -> None:
    text = _read(RISK_REGISTER_PATH)
    for target_path in RISK_LINE_COUNT_PATHS:
        # Expected style:
        # `services/.../file.py` is 123 lines
        pattern = re.compile(rf"`{re.escape(target_path.as_posix())}`\s+is\s+(\d+)\s+lines")
        match = pattern.search(text)
        if match is None:
            failures.append(f"{RISK_REGISTER_PATH}: missing line-count claim for {target_path.as_posix()}")
            continue
        claimed = int(match.group(1))
        actual = _line_count(target_path)
        if claimed != actual:
            failures.append(
                f"{RISK_REGISTER_PATH}: stale line-count claim for {target_path.as_posix()} "
                f"(claimed {claimed}, actual {actual})"
            )


def _extract_section(text: str, *, start_header: str, end_header: str) -> str:
    start = text.find(start_header)
    if start < 0:
        return ""
    end = text.find(end_header, start + len(start_header))
    if end < 0:
        end = len(text)
    return text[start:end]


def _validate_shotlist_capture_targets(failures: list[str]) -> None:
    text = _read(SHOTLIST_PATH)
    section = _extract_section(text, start_header="## Capture targets", end_header="## Storyline overlays")
    if not section:
        failures.append(f"{SHOTLIST_PATH}: missing '## Capture targets' section")
        return

    rows = re.findall(r"^\s*(\d+)\.\s+`([^`]+)`", section, flags=re.MULTILINE)
    if len(rows) != len(SHOTLIST_EXPECTED_FILES):
        failures.append(
            f"{SHOTLIST_PATH}: expected {len(SHOTLIST_EXPECTED_FILES)} numbered capture targets, found {len(rows)}"
        )
        return

    for idx, (number, filename) in enumerate(rows, start=1):
        if int(number) != idx:
            failures.append(f"{SHOTLIST_PATH}: expected capture target number {idx}, found {number}")
            continue
        expected_file = SHOTLIST_EXPECTED_FILES[idx - 1]
        if filename != expected_file:
            failures.append(
                f"{SHOTLIST_PATH}: capture target {idx} expected `{expected_file}`, found `{filename}`"
            )


def _validate_no_stale_refresh_markers(failures: list[str]) -> None:
    for path in (PUBLIC_OVERVIEW_PATH, CURRENT_STATE_PATH):
        text = _read(path)
        if "refresh queued" in text:
            failures.append(f"{path}: contains stale 'refresh queued' marker")
        if "still being refreshed in the press kit shotlist" in text:
            failures.append(f"{path}: contains stale broad screenshot-refresh claim")


def _validate_placeholder_backlog(failures: list[str]) -> None:
    text = _read(PLACEHOLDERS_PATH)
    backlog_rows = re.findall(r"^\s*\d+\.\s+`([^`]+)`", text, flags=re.MULTILINE)
    for filename in backlog_rows:
        if not filename:
            continue
        backlog_path = Path("press/screenshots") / filename
        if backlog_path.exists():
            failures.append(
                f"{PLACEHOLDERS_PATH}: backlog file `{filename}` already exists in press/screenshots; remove or reclassify"
            )


def main() -> int:
    failures: list[str] = []
    try:
        _validate_risk_register_line_counts(failures)
        _validate_shotlist_capture_targets(failures)
        _validate_no_stale_refresh_markers(failures)
        _validate_placeholder_backlog(failures)
    except RuntimeError as exc:
        print(f"[docs-truth-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("[docs-truth-guard] FAIL: docs truth drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[docs-truth-guard] update docs and screenshot trackers with current ground truth", file=sys.stderr)
        return 1

    print("[docs-truth-guard] OK (maintenance metrics + screenshot docs truth checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
