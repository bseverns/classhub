#!/usr/bin/env python3
"""Guardrail: keep key docs claims aligned with current repository state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


RISK_REGISTER_PATH = Path("docs/MAINTENANCE_RISK_REGISTER.md")
README_PATH = Path("README.md")
PUBLIC_OVERVIEW_PATH = Path("docs/PUBLIC_OVERVIEW.md")
CURRENT_STATE_PATH = Path("docs/CURRENT_STATE.md")
FEATURE_MATURITY_PATH = Path("docs/FEATURE_MATURITY.md")
CANONICAL_TRUTHS_PATH = Path("docs/CANONICAL_TRUTHS.md")
SECURITY_PATH = Path("docs/SECURITY.md")
MERGE_READINESS_PATH = Path("docs/MERGE_READINESS.md")
SECURITY_BASELINE_PATH = Path("docs/SECURITY_BASELINE.md")
PRIVATE_LLM_PATH = Path("docs/PRIVATE_LLM_BACKEND.md")
HEADSCALE_PATH = Path("docs/HEADSCALE_CONTROL_PLANE.md")
REMOTE_HELPER_COMPUTE_PATH = Path("docs/REMOTE_HELPER_COMPUTE_CONTROL.md")
EVIDENCE_REMOTE_COMPUTE_PATH = Path("docs/EVIDENCE_REMOTE_COMPUTE.md")
RUNBOOK_PATH = Path("docs/RUNBOOK.md")
TROUBLESHOOTING_PATH = Path("docs/TROUBLESHOOTING.md")
REMOTE_HELPER_OPS_PATH = Path("ops/remote-helper-compute/README.md")
RUNTIME_REGISTRY_PATH = Path("docs/_registry/runtime_contracts.json")
PRESS_ARCHITECTURE_PATH = Path("press/architecture.md")
PRESS_ONE_PAGER_PATH = Path("press/one_pager.md")
PRESS_EVALUATOR_QUICK_PACK_PATH = Path("press/evaluator_quick_pack.md")
PRESS_CONFERENCE_PACKET_PATH = Path("press/conference_packet.md")
PRESS_STACK_CLAIMS_PATH = Path("press/stack_claims_and_evidence.md")
PRESS_STAGE_SAFE_CLAIMS_PATH = Path("press/stage_safe_claims.md")
PRESS_FAILURE_MATRIX_PATH = Path("press/failure_degradation_matrix.md")
PRESS_ARCHITECTURE_DIAGRAM_SOURCE_PATH = Path("press/diagrams/classhub_boundary_architecture.mmd")
PRESS_REMOTE_STATE_DIAGRAM_SOURCE_PATH = Path("press/diagrams/remote_helper_compute_state.mmd")
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
    readme_text = _read(README_PATH)
    security_text = _read(SECURITY_PATH)
    private_llm_text = _read(PRIVATE_LLM_PATH)
    headscale_text = _read(HEADSCALE_PATH)
    remote_helper_compute_text = _read(REMOTE_HELPER_COMPUTE_PATH)
    evidence_remote_compute_text = _read(EVIDENCE_REMOTE_COMPUTE_PATH)
    press_architecture_text = _read(PRESS_ARCHITECTURE_PATH)
    press_one_pager_text = _read(PRESS_ONE_PAGER_PATH)
    press_evaluator_quick_pack_text = _read(PRESS_EVALUATOR_QUICK_PACK_PATH)
    press_conference_packet_text = _read(PRESS_CONFERENCE_PACKET_PATH)
    press_stack_claims_text = _read(PRESS_STACK_CLAIMS_PATH)
    press_stage_safe_claims_text = _read(PRESS_STAGE_SAFE_CLAIMS_PATH)
    press_failure_matrix_text = _read(PRESS_FAILURE_MATRIX_PATH)
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
        readme_text,
        path=README_PATH,
        snippets=list(contracts.get("readme_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        canonical_truths_text,
        path=CANONICAL_TRUTHS_PATH,
        snippets=list(contracts.get("canonical_truths_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        private_llm_text,
        path=PRIVATE_LLM_PATH,
        snippets=list(contracts.get("private_llm_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        headscale_text,
        path=HEADSCALE_PATH,
        snippets=list(contracts.get("headscale_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        remote_helper_compute_text,
        path=REMOTE_HELPER_COMPUTE_PATH,
        snippets=list(contracts.get("remote_helper_compute_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        evidence_remote_compute_text,
        path=EVIDENCE_REMOTE_COMPUTE_PATH,
        snippets=list(contracts.get("evidence_remote_compute_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_conference_packet_text,
        path=PRESS_CONFERENCE_PACKET_PATH,
        snippets=list(contracts.get("press_conference_packet_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_stack_claims_text,
        path=PRESS_STACK_CLAIMS_PATH,
        snippets=list(contracts.get("press_stack_claims_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_stage_safe_claims_text,
        path=PRESS_STAGE_SAFE_CLAIMS_PATH,
        snippets=list(contracts.get("press_stage_safe_claims_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_failure_matrix_text,
        path=PRESS_FAILURE_MATRIX_PATH,
        snippets=list(contracts.get("press_failure_matrix_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_architecture_text,
        path=PRESS_ARCHITECTURE_PATH,
        snippets=list(contracts.get("press_architecture_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_one_pager_text,
        path=PRESS_ONE_PAGER_PATH,
        snippets=list(contracts.get("press_one_pager_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        press_evaluator_quick_pack_text,
        path=PRESS_EVALUATOR_QUICK_PACK_PATH,
        snippets=list(contracts.get("press_evaluator_quick_pack_required_snippets") or []),
        failures=failures,
    )
    _require_snippets(
        _read(SHOTLIST_PATH),
        path=SHOTLIST_PATH,
        snippets=list(contracts.get("press_shotlist_required_snippets") or []),
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
        README_PATH,
        CURRENT_STATE_PATH,
        FEATURE_MATURITY_PATH,
        CANONICAL_TRUTHS_PATH,
        SECURITY_PATH,
        PRIVATE_LLM_PATH,
        HEADSCALE_PATH,
        REMOTE_HELPER_COMPUTE_PATH,
        EVIDENCE_REMOTE_COMPUTE_PATH,
        RUNBOOK_PATH,
        TROUBLESHOOTING_PATH,
        REMOTE_HELPER_OPS_PATH,
        MERGE_READINESS_PATH,
        SECURITY_BASELINE_PATH,
        PRESS_ARCHITECTURE_PATH,
        PRESS_ONE_PAGER_PATH,
        PRESS_EVALUATOR_QUICK_PACK_PATH,
        PRESS_CONFERENCE_PACKET_PATH,
        PRESS_STACK_CLAIMS_PATH,
        PRESS_STAGE_SAFE_CLAIMS_PATH,
        PRESS_FAILURE_MATRIX_PATH,
        *ENV_EXAMPLE_PATHS,
    )
    for path in stale_targets:
        text = _read(path)
        for phrase in stale_phrases:
            if phrase in text:
                failures.append(f"{path}: contains stale contract phrase {phrase!r}")

    forbidden_snippets = [
        str(item).strip() for item in (contracts.get("forbidden_snippets") or []) if str(item).strip()
    ]
    forbidden_targets = (
        README_PATH,
        PRIVATE_LLM_PATH,
        HEADSCALE_PATH,
        REMOTE_HELPER_COMPUTE_PATH,
        EVIDENCE_REMOTE_COMPUTE_PATH,
        RUNBOOK_PATH,
        TROUBLESHOOTING_PATH,
        REMOTE_HELPER_OPS_PATH,
        CANONICAL_TRUTHS_PATH,
        PRESS_ARCHITECTURE_PATH,
        PRESS_ONE_PAGER_PATH,
        PRESS_EVALUATOR_QUICK_PACK_PATH,
        PRESS_CONFERENCE_PACKET_PATH,
        PRESS_STACK_CLAIMS_PATH,
        PRESS_STAGE_SAFE_CLAIMS_PATH,
        PRESS_FAILURE_MATRIX_PATH,
        *ENV_EXAMPLE_PATHS,
    )
    for path in forbidden_targets:
        text = _read(path)
        for snippet in forbidden_snippets:
            if snippet in text:
                failures.append(f"{path}: contains forbidden topology phrase {snippet!r}")

    csp_note = str(((registry.get("runtime") or {}).get("csp") or {}).get("note") or "").strip()
    if csp_note:
        if csp_note not in security_baseline_text:
            failures.append(f"{SECURITY_BASELINE_PATH}: missing CSP deployment-default note from runtime registry")

    for path, required in (
        (PRESS_ARCHITECTURE_DIAGRAM_SOURCE_PATH, ["Homework Helper", "Headscale", "server-to-server only"]),
        (PRESS_REMOTE_STATE_DIAGRAM_SOURCE_PATH, ["stateDiagram-v2", "ready", "degraded"]),
    ):
        text = _read(path)
        for snippet in required:
            if snippet not in text:
                failures.append(f"{path}: missing required diagram-source snippet {snippet!r}")


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
