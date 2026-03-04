#!/usr/bin/env python3
"""Guardrail: critical endpoint RBAC helpers must not drift.

This is a lightweight static contract check that verifies selected endpoint
functions use capability-specific guard helpers (and avoid coarse fallbacks).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EndpointContract:
    path: str
    function: str
    required_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...] = ()


CONTRACTS: tuple[EndpointContract, ...] = (
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_students.py",
        function="teach_student_return_code",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_students.py",
        function="teach_rename_student",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_students.py",
        function="teach_merge_students",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_students.py",
        function="teach_delete_student_data",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_support.py",
        function="teach_resolve_stuck_flag",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_support.py",
        function="teach_add_support_tag",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_policies.py",
        function="teach_set_retention_preset",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_invites.py",
        function="teach_export_class_summary_csv",
        required_tokens=("staff_can_view_submissions(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_invites.py",
        function="teach_export_class_outcomes_csv",
        required_tokens=("staff_can_view_submissions(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_invites.py",
        function="teach_set_enrollment_mode",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_landing.py",
        function="teach_update_class_landing",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/content_lessons.py",
        function="teach_set_lesson_release",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_materials.py",
        function="teach_material_submissions",
        required_tokens=("staff_can_view_submissions(", "module_id=material.module_id"),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_gallery.py",
        function="teach_moderate_gallery_submission",
        required_tokens=("staff_can_delete_submissions(", "module_id=material.module_id"),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_gallery.py",
        function="teach_set_module_gallery_enabled",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_reset_roster",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_reset_helper_conversations",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_toggle_lock",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_lock_class",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_export_class_submissions_today",
        required_tokens=("staff_can_view_submissions(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_class.py",
        function="teach_rotate_code",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_certificates.py",
        function="teach_download_certificate",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_access_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/roster_certificates.py",
        function="teach_download_certificate_pdf",
        required_tokens=("staff_can_manage_roster(",),
        forbidden_tokens=("staff_can_access_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher.py",
        function="_policy_or_403",
        required_tokens=("staff_can_manage_policy(",),
        forbidden_tokens=("staff_can_manage_classroom(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher.py",
        function="api_teacher_toggle_lock",
        required_tokens=("_policy_or_403(",),
        forbidden_tokens=("_manage_or_403(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher.py",
        function="api_teacher_rotate_code",
        required_tokens=("_policy_or_403(",),
        forbidden_tokens=("_manage_or_403(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher.py",
        function="api_teacher_set_enrollment_mode",
        required_tokens=("_policy_or_403(",),
        forbidden_tokens=("_manage_or_403(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/content_rbac_tools.py",
        function="teach_upsert_module_scope_grant",
        required_tokens=("_require_rbac_tools_access(", "_parse_scope_grant_payload(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/content_rbac_tools.py",
        function="teach_set_module_scope_grant_active",
        required_tokens=("_require_rbac_tools_access(", "staff_classroom_or_none(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/teacher_parts/content_rbac_tools.py",
        function="teach_simulate_rbac_access",
        required_tokens=("_require_rbac_tools_access(", "_parse_simulation_payload(", "evaluate_staff_capability("),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher_rbac.py",
        function="api_teacher_rbac_simulate",
        required_tokens=("_rbac_simulation_or_403(", "evaluate_staff_capability("),
    ),
    EndpointContract(
        path="services/classhub/hub/views/api_teacher.py",
        function="api_teacher_class_submissions",
        required_tokens=("staff_can_view_submissions(",),
    ),
    EndpointContract(
        path="services/classhub/hub/views/student.py",
        function="submission_download",
        required_tokens=("staff_can_view_submissions(", "module_id=s.material.module_id"),
    ),
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


def _function_source(path: Path, function_name: str) -> tuple[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:
        return "", f"could not read {path}: {exc}"
    try:
        tree = ast.parse(raw, filename=str(path))
    except SyntaxError as exc:
        return "", f"{path}: syntax error: {exc}"
    lines = raw.splitlines()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != function_name:
            continue
        if node.end_lineno is None:
            return "", f"{path}:{function_name}: missing end_lineno metadata"
        start = max(0, node.lineno - 1)
        end = min(len(lines), node.end_lineno)
        return "\n".join(lines[start:end]), ""
    return "", f"{path}: missing function {function_name!r}"


def main() -> int:
    args = _parse_args()
    failures: list[str] = []

    for contract in CONTRACTS:
        path = Path(contract.path)
        source, load_error = _function_source(path, contract.function)
        if load_error:
            failures.append(load_error)
            continue
        for token in contract.required_tokens:
            if token not in source:
                failures.append(
                    f"{contract.path}::{contract.function}: missing required token {token!r}"
                )
        for token in contract.forbidden_tokens:
            if token in source:
                failures.append(
                    f"{contract.path}::{contract.function}: contains forbidden token {token!r}"
                )

    report = {
        "guard": "rbac-endpoint-guard",
        "ok": not failures,
        "contracts": len(CONTRACTS),
        "failures": failures,
    }

    if args.json_output:
        print(json.dumps(report, sort_keys=True))
        return 1 if failures else 0

    if failures:
        print("[rbac-endpoint-guard] FAIL: endpoint RBAC guard drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[rbac-endpoint-guard] update contracts only with intentional review.", file=sys.stderr)
        return 1

    print(f"[rbac-endpoint-guard] OK ({len(CONTRACTS)} endpoint contracts checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
