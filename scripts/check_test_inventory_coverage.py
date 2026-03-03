#!/usr/bin/env python3
"""Guardrail: maintain minimum automated test inventory across subsystems."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TEST_DEF_RE = re.compile(r"^\s*def\s+test_[A-Za-z0-9_]*\s*\(", re.MULTILINE)


def _count_tests(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(TEST_DEF_RE.findall(text))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


FILE_CONTRACTS: dict[str, dict] = {
    "test_student_view.py": {
        "min_tests": 1,
        "tokens": ("StudentHomeSmokeTests",),
    },
    "services/classhub/hub/tests/test_student_ops.py": {
        "min_tests": 60,
        "tokens": ("JoinClassTests", "StudentDataControlsTests", "/student/portfolio"),
    },
    "services/classhub/hub/tests/test_teacher_admin_portal.py": {
        "min_tests": 70,
        "tokens": ("TeacherPortalTests", "/teach/material/", "/teach/module/"),
    },
    "services/classhub/hub/tests/test_teacher_admin_auth.py": {
        "min_tests": 12,
        "tokens": ("Teacher2FASetupTests", "TeacherOTPEnforcementTests"),
    },
    "services/classhub/hub/tests/test_teacher_admin_release.py": {
        "min_tests": 15,
        "tokens": ("LessonReleaseTests",),
    },
    "services/classhub/hub/tests/test_privacy_flow.py": {
        "min_tests": 10,
        "tokens": ("StudentDeleteWorkTests", "trust"),
    },
    "services/classhub/hub/tests/test_security_integration.py": {
        "min_tests": 12,
        "tokens": ("ClassHubSecurityHeaderTests", "InternalHelperEventEndpointTests"),
    },
    "services/classhub/hub/tests/test_api_student.py": {
        "min_tests": 10,
        "tokens": ("StudentSessionEndpointTests", "StudentModulesEndpointTests"),
    },
    "services/classhub/hub/tests/test_api_teacher.py": {
        "min_tests": 20,
        "tokens": ("TeacherClassesEndpointTests", "TeacherClassSubmissionsEndpointTests"),
    },
    "services/homework_helper/tutor/tests/test_chat_endpoint.py": {
        "min_tests": 30,
        "tokens": ("HelperChatAuthTests", "/helper/chat"),
    },
    "services/homework_helper/tutor/tests/test_engine.py": {
        "min_tests": 15,
        "tokens": ("BackendEngineTests", "RuntimeConfigEngineTests"),
    },
    "services/homework_helper/tutor/tests/test_view_modules.py": {
        "min_tests": 10,
        "tokens": ("HelperChatRequestModuleTests", "HelperChatRuntimeModuleTests"),
    },
    "services/homework_helper/tutor/tests/test_access.py": {
        "min_tests": 8,
        "tokens": ("HelperAdminAccessTests", "HelperSecurityHeaderTests"),
    },
    "services/homework_helper/tutor/tests/test_events.py": {
        "min_tests": 4,
        "tokens": ("ClassHubEventForwardingTests",),
    },
    "services/homework_helper/tutor/tests/test_internal_reset.py": {
        "min_tests": 4,
        "tokens": ("HelperInternalResetTests",),
    },
}

MIN_DIR_TEST_TOTALS: dict[str, int] = {
    "services/classhub/hub/tests": 300,
    "services/homework_helper/tutor/tests": 80,
}

REQUIRED_SMOKE_SCRIPTS: tuple[str, ...] = (
    "scripts/system_doctor.sh",
    "scripts/golden_path_smoke.sh",
    "scripts/a11y_smoke.sh",
    "scripts/smoke_check.sh",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON report.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    failures: list[str] = []
    file_test_counts: dict[str, int] = {}
    dir_test_totals: dict[str, int] = {}
    checked_files = 0

    for rel_path, contract in FILE_CONTRACTS.items():
        path = Path(rel_path)
        if not path.exists():
            failures.append(f"missing required test file: {rel_path}")
            continue
        checked_files += 1
        count = _count_tests(path)
        file_test_counts[rel_path] = count
        min_tests = int(contract.get("min_tests") or 0)
        if count < min_tests:
            failures.append(f"{rel_path}: {count} tests; expected at least {min_tests}")
        text = _read(path)
        for token in contract.get("tokens") or ():
            if token not in text:
                failures.append(f"{rel_path}: missing required token {token!r}")

    for rel_dir, min_total in MIN_DIR_TEST_TOTALS.items():
        root = Path(rel_dir)
        if not root.exists():
            failures.append(f"missing required test directory: {rel_dir}")
            continue
        total = sum(_count_tests(path) for path in sorted(root.glob("test_*.py")))
        dir_test_totals[rel_dir] = total
        if total < min_total:
            failures.append(f"{rel_dir}: {total} tests; expected at least {min_total}")

    for rel_script in REQUIRED_SMOKE_SCRIPTS:
        if not Path(rel_script).exists():
            failures.append(f"missing required smoke script: {rel_script}")

    report = {
        "guard": "test-inventory-coverage",
        "ok": not failures,
        "file_contracts": len(FILE_CONTRACTS),
        "checked_files": checked_files,
        "directory_contracts": len(MIN_DIR_TEST_TOTALS),
        "smoke_script_contracts": len(REQUIRED_SMOKE_SCRIPTS),
        "file_test_counts": file_test_counts,
        "directory_test_totals": dir_test_totals,
        "failures": failures,
    }

    if args.json_output:
        print(json.dumps(report, sort_keys=True))
        return 1 if failures else 0

    if failures:
        print("[test-inventory-guard] FAIL: test coverage inventory drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[test-inventory-guard] update script thresholds/contracts only with intentional review.", file=sys.stderr)
        return 1

    print(
        "[test-inventory-guard] OK "
        f"({len(FILE_CONTRACTS)} file contracts, {len(MIN_DIR_TEST_TOTALS)} directories, {len(REQUIRED_SMOKE_SCRIPTS)} smoke scripts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
