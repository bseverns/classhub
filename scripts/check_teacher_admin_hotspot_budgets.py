#!/usr/bin/env python3
"""Guardrail: cap growth in teacher/admin/RBAC hotspot files."""

from __future__ import annotations

import sys
from pathlib import Path


HOTSPOT_BUDGETS: dict[Path, int] = {
    Path("services/classhub/hub/tests/test_teacher_admin_portal.py"): 4100,
    Path("services/classhub/hub/services/org_access.py"): 730,
    Path("services/classhub/hub/services/rbac_policy_bundle.py"): 710,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_endpoints.py"): 650,
    Path("services/classhub/templates/includes/teach_home/setup_sections_rbac_panel.html"): 600,
}


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def main() -> int:
    failures: list[str] = []
    measured = 0
    for path, budget in HOTSPOT_BUDGETS.items():
        if not path.exists():
            failures.append(f"missing expected hotspot file: {path.as_posix()}")
            continue
        measured += 1
        lines = _line_count(path)
        if lines > budget:
            failures.append(f"{path.as_posix()}: {lines} lines (budget {budget})")

    if failures:
        print("[teacher-admin-hotspot-budgets] FAIL: hotspot budget drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[teacher-admin-hotspot-budgets] split or prune governance-heavy modules before merging",
            file=sys.stderr,
        )
        return 1

    print(
        "[teacher-admin-hotspot-budgets] OK "
        f"({measured} hotspot files checked; all within budget)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
