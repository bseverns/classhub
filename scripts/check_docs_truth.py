#!/usr/bin/env python3
"""Guardrail: keep key docs claims aligned with current repository state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


RISK_REGISTER_PATH = Path("docs/MAINTENANCE_RISK_REGISTER.md")
PUBLIC_OVERVIEW_PATH = Path("docs/PUBLIC_OVERVIEW.md")
CURRENT_STATE_PATH = Path("docs/CURRENT_STATE.md")
FEATURE_MATURITY_PATH = Path("docs/FEATURE_MATURITY.md")
CANONICAL_TRUTHS_PATH = Path("docs/CANONICAL_TRUTHS.md")
SECURITY_PATH = Path("docs/SECURITY.md")
MERGE_READINESS_PATH = Path("docs/MERGE_READINESS.md")
SECURITY_BASELINE_PATH = Path("docs/SECURITY_BASELINE.md")
RUNTIME_REGISTRY_PATH = Path("docs/_registry/runtime_contracts.json")
SHOTLIST_PATH = Path("press/screenshots/SHOTLIST.md")
PLACEHOLDERS_PATH = Path("press/screenshots/PLACEHOLDERS.md")
ENV_EXAMPLE_PATHS = (
    Path("compose/.env.example"),
    Path("compose/.env.example.local"),
    Path("compose/.env.example.domain"),
)

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


def _load_runtime_registry() -> dict:
    try:
        raw = json.loads(RUNTIME_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"unable to read {RUNTIME_REGISTRY_PATH}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"{RUNTIME_REGISTRY_PATH}: expected a top-level mapping")
    return raw


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


def _require_snippets(text: str, *, path: Path, snippets: list[str], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing required snippet {snippet!r}")


def _validate_runtime_registry_contracts(failures: list[str]) -> None:
    registry = _load_runtime_registry()
    contracts = registry.get("contracts") or {}
    features = registry.get("features") or {}

    current_state_text = _read(CURRENT_STATE_PATH)
    feature_maturity_text = _read(FEATURE_MATURITY_PATH)
    canonical_truths_text = _read(CANONICAL_TRUTHS_PATH)
    security_text = _read(SECURITY_PATH)
    merge_readiness_text = _read(MERGE_READINESS_PATH)
    security_baseline_text = _read(SECURITY_BASELINE_PATH)

    _require_snippets(
        current_state_text,
        path=CURRENT_STATE_PATH,
        snippets=list(contracts.get("current_state_required_notes") or []),
        failures=failures,
    )
    _require_snippets(
        security_text,
        path=SECURITY_PATH,
        snippets=list(contracts.get("security_required_notes") or []),
        failures=failures,
    )
    _require_snippets(
        canonical_truths_text,
        path=CANONICAL_TRUTHS_PATH,
        snippets=list(contracts.get("canonical_truths_required_snippets") or []),
        failures=failures,
    )

    for feature in features.values():
        if not isinstance(feature, dict):
            continue
        capability = str(feature.get("capability") or "").strip()
        status = str(feature.get("status") or "").strip()
        toggle = str(feature.get("toggle") or "").strip()
        if not capability or not status:
            continue
        row_pattern = re.compile(
            rf"^\|\s*{re.escape(capability)}\s*\|\s*{re.escape(status)}\s*\|\s*(.+?)\s*\|",
            flags=re.MULTILINE,
        )
        match = row_pattern.search(feature_maturity_text)
        if match is None:
            failures.append(
                f"{FEATURE_MATURITY_PATH}: missing feature maturity row for {capability!r} with status {status!r}"
            )
            continue
        if toggle and toggle not in match.group(1):
            failures.append(
                f"{FEATURE_MATURITY_PATH}: row for {capability!r} is missing toggle contract {toggle!r}"
            )

    stale_phrases = [str(item).strip() for item in (contracts.get("stale_phrases") or []) if str(item).strip()]
    stale_targets = (
        CURRENT_STATE_PATH,
        FEATURE_MATURITY_PATH,
        CANONICAL_TRUTHS_PATH,
        SECURITY_PATH,
        MERGE_READINESS_PATH,
        SECURITY_BASELINE_PATH,
        *ENV_EXAMPLE_PATHS,
    )
    for path in stale_targets:
        text = _read(path)
        for phrase in stale_phrases:
            if phrase in text:
                failures.append(f"{path}: contains stale contract phrase {phrase!r}")

    csp_note = str(((registry.get("runtime") or {}).get("csp") or {}).get("note") or "").strip()
    if csp_note:
        if csp_note not in security_baseline_text:
            failures.append(f"{SECURITY_BASELINE_PATH}: missing CSP deployment-default note from runtime registry")


def main() -> int:
    failures: list[str] = []
    try:
        _validate_risk_register_line_counts(failures)
        _validate_shotlist_capture_targets(failures)
        _validate_no_stale_refresh_markers(failures)
        _validate_placeholder_backlog(failures)
        _validate_runtime_registry_contracts(failures)
    except RuntimeError as exc:
        print(f"[docs-truth-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("[docs-truth-guard] FAIL: docs truth drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[docs-truth-guard] update registry-backed docs, env examples, and screenshot trackers with current ground truth",
            file=sys.stderr,
        )
        return 1

    print("[docs-truth-guard] OK (maintenance metrics + registry-backed docs truth checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
