#!/usr/bin/env python3
"""Guardrail: keep teacher roster dashboard service decomposition stable."""

from __future__ import annotations

import sys
from pathlib import Path


ROSTER_SERVICE = Path("services/classhub/hub/services/teacher_roster_class.py")
MAX_ROSTER_SERVICE_LINES = 700
EXPECTED_SECTION_MODULES = (
    Path("services/classhub/hub/services/teacher_dashboard_sections/roster.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/facilitator_support.py"),
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes.py"),
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
        roster_text = _read(ROSTER_SERVICE)
    except RuntimeError as exc:
        print(f"[teacher-roster-service-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    roster_lines = _line_count(ROSTER_SERVICE)
    if roster_lines > MAX_ROSTER_SERVICE_LINES:
        failures.append(
            f"{ROSTER_SERVICE}: expected <= {MAX_ROSTER_SERVICE_LINES} lines, found {roster_lines}"
        )

    _require_snippets(
        roster_text,
        path=ROSTER_SERVICE,
        snippets=[
            "from .teacher_dashboard_sections.facilitator_support import (",
            "from .teacher_dashboard_sections.outcomes import (",
            "from .teacher_dashboard_sections.roster import (",
            "int_setting as _int_setting_impl",
            "def _build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:",
            "return _facilitator_support_snapshot_impl(",
            "def _build_outcome_snapshot(*, classroom, students: list[StudentIdentity]) -> dict:",
            "return _outcome_snapshot_impl(classroom=classroom, students=students)",
            "def _material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:",
            "return _material_submission_counts_impl(upload_material_ids)",
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
            "[teacher-roster-service-guard] keep section builders in teacher_dashboard_sections/* and orchestration in teacher_roster_class.py",
            file=sys.stderr,
        )
        return 1

    print(
        "[teacher-roster-service-guard] OK "
        f"(service={ROSTER_SERVICE.as_posix()} lines={roster_lines}; sections={len(EXPECTED_SECTION_MODULES)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
