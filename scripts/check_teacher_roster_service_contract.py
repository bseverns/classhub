#!/usr/bin/env python3
"""Guardrail: keep teacher roster dashboard service decomposition stable."""

from __future__ import annotations

import sys
from pathlib import Path


ROSTER_FACADE = Path("services/classhub/hub/services/teacher_roster_class.py")
ROSTER_DASHBOARD = Path("services/classhub/hub/services/teacher_roster_class_dashboard.py")
MAX_ROSTER_FACADE_LINES = 140
MAX_ROSTER_DASHBOARD_LINES = 340
EXPECTED_SECTION_MODULES = (
    Path("services/classhub/hub/services/teacher_dashboard_sections/roster.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/facilitator_support.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/facilitator_support_builders.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes_rollup.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes_snapshot.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/shared.py"),
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _require_snippets(text: str, *, path: Path, snippets: list[str], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing snippet {snippet!r}")


def main() -> int:
    failures: list[str] = []
    try:
        roster_facade_text = _read(ROSTER_FACADE)
        roster_dashboard_text = _read(ROSTER_DASHBOARD)
    except RuntimeError as exc:
        print(f"[teacher-roster-service-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    facade_lines = _line_count(ROSTER_FACADE)
    dashboard_lines = _line_count(ROSTER_DASHBOARD)
    if facade_lines > MAX_ROSTER_FACADE_LINES:
        failures.append(
            f"{ROSTER_FACADE}: expected <= {MAX_ROSTER_FACADE_LINES} lines, found {facade_lines}"
        )
    if dashboard_lines > MAX_ROSTER_DASHBOARD_LINES:
        failures.append(
            f"{ROSTER_DASHBOARD}: expected <= {MAX_ROSTER_DASHBOARD_LINES} lines, found {dashboard_lines}"
        )

    _require_snippets(
        roster_facade_text,
        path=ROSTER_FACADE,
        snippets=[
            "from .teacher_roster_class_dashboard import (",
            "build_dashboard_context_impl,",
            "build_certificate_eligibility_rows,",
            "def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:",
            "return build_dashboard_context_impl(",
            "from .teacher_roster_class_exports import (",
        ],
        failures=failures,
    )
    _require_snippets(
        roster_dashboard_text,
        path=ROSTER_DASHBOARD,
        snippets=[
            "from .teacher_dashboard_sections.facilitator_support import (",
            "from .teacher_dashboard_sections.outcomes import (",
            "from .teacher_dashboard_sections.roster import (",
            "def _build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:",
            "return _facilitator_support_snapshot_impl(",
            "def _build_outcome_snapshot(*, classroom, students: list[StudentIdentity]) -> dict:",
            "return _outcome_snapshot_impl(classroom=classroom, students=students)",
            "def _material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:",
            "return _material_submission_counts_impl(upload_material_ids)",
            "def build_dashboard_context_impl(",
        ],
        failures=failures,
    )

    for path in EXPECTED_SECTION_MODULES:
        if not path.exists():
            failures.append(f"missing section module: {path}")

    if failures:
        print("[teacher-roster-service-guard] FAIL: roster service contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[teacher-roster-service-guard] keep section builders in teacher_dashboard_sections/* and orchestration in teacher_roster_class_dashboard.py",
            file=sys.stderr,
        )
        return 1

    print(
        "[teacher-roster-service-guard] OK "
        f"(facade={ROSTER_FACADE.as_posix()} lines={facade_lines}; "
        f"dashboard={ROSTER_DASHBOARD.as_posix()} lines={dashboard_lines}; "
        f"sections={len(EXPECTED_SECTION_MODULES)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
