#!/usr/bin/env python3
"""Guardrail: keep /teach/class section partials and section services within budgets."""

from __future__ import annotations

import sys
from pathlib import Path


SECTION_BUDGETS: dict[Path, int] = {
    Path("services/classhub/templates/includes/teach_class/class_setup_and_roster_card.html"): 80,
    Path("services/classhub/templates/includes/teach_class/class_setup_landing_section.html"): 70,
    Path("services/classhub/templates/includes/teach_class/class_setup_invites_section.html"): 130,
    Path("services/classhub/templates/includes/teach_class/class_setup_staff_assignments_section.html"): 95,
    Path("services/classhub/templates/includes/teach_class/class_setup_roster_section.html"): 210,
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_card.html"): 90,
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_row_lesson_cell.html"): 40,
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_dropbox_cell.html"): 40,
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_release_controls.html"): 90,
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_helper_tuning.html"): 90,
    Path("services/classhub/templates/includes/teach_class/support_board_card.html"): 140,
    Path("services/classhub/templates/includes/teach_class/module_editor_card.html"): 120,
    Path("services/classhub/templates/includes/teach_class/helper_signals_card.html"): 80,
    Path("services/classhub/templates/includes/teach_class/outcomes_snapshot_card.html"): 80,
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes.py"): 40,
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes_rollup.py"): 140,
    Path("services/classhub/hub/services/teacher_dashboard_sections/outcomes_snapshot.py"): 170,
    Path("services/classhub/hub/services/teacher_dashboard_sections/facilitator_support.py"): 100,
    Path("services/classhub/hub/services/teacher_dashboard_sections/facilitator_support_builders.py"): 240,
    Path("services/classhub/hub/services/teacher_dashboard_sections/roster.py"): 120,
    Path("services/classhub/hub/services/teacher_dashboard_sections/shared.py"): 60,
}


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def main() -> int:
    failures: list[str] = []
    measured = 0
    for path, budget in SECTION_BUDGETS.items():
        if not path.exists():
            failures.append(f"missing expected section file: {path.as_posix()}")
            continue
        measured += 1
        lines = _line_count(path)
        if lines > budget:
            failures.append(f"{path.as_posix()}: {lines} lines (budget {budget})")

    if failures:
        print("[teach-class-section-budgets] FAIL: section budget drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[teach-class-section-budgets] split or prune heavy sections before merging", file=sys.stderr)
        return 1

    print(
        "[teach-class-section-budgets] OK "
        f"({measured} section files checked; all within budget)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
