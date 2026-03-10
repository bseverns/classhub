#!/usr/bin/env python3
"""Guardrail: teacher/API routes must declare capability intent contracts.

This script enforces:
- every `/teach*` and `/api/v1/teacher*` URL route is mapped to a capability,
- each mapped endpoint still contains expected capability guard tokens.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


URLCONF_PATH = Path("services/classhub/config/urls.py")
VIEW_ROOT = Path("services/classhub/hub/views")


@dataclass(frozen=True)
class RouteContract:
    capability: str
    view: str
    required_tokens: tuple[str, ...] = ()
    forbidden_tokens: tuple[str, ...] = ()


CAPABILITY_TOKEN_RULES: dict[str, tuple[str, ...]] = {
    "auth_or_public": (),
    "staff_only": ("@staff_member_required",),
    "org.superuser": ("request.user.is_superuser", "_require_superuser("),
    "class.view": ("staff_classroom_or_none(", "staff_accessible_classes_ranked(", "staff_can_access_classroom("),
    "class.create": ("staff_can_create_classes(",),
    "class.manage": ("staff_can_manage_classroom(", "_manage_or_403("),
    "roster.manage": ("staff_can_manage_roster(",),
    "policy.manage": ("staff_can_manage_policy(", "_policy_or_403("),
    "submission.view": ("staff_can_view_submissions(",),
    "submission.delete": ("staff_can_delete_submissions(",),
    "syllabus.export": ("staff_can_export_syllabi(",),
    "rbac.manage": ("staff_can_export_syllabi(", "rbac_tools_enabled_for_user(", "_require_rbac_tools_access("),
    "rbac.simulate": (
        "staff_can_export_syllabi(",
        "rbac_tools_enabled_for_user(",
        "_require_rbac_tools_access(",
        "evaluate_staff_capability(",
    ),
}


ROUTE_CAPABILITY_MAP: dict[str, RouteContract] = {
    "/api/v1/teacher/classes": RouteContract("class.view", "api_teacher_classes"),
    "/api/v1/teacher/class/<int:class_id>/roster": RouteContract("class.view", "api_teacher_class_roster"),
    "/api/v1/teacher/class/<int:class_id>/submissions": RouteContract("submission.view", "api_teacher_class_submissions"),
    "/api/v1/teacher/class/<int:class_id>/toggle-lock": RouteContract("policy.manage", "api_teacher_toggle_lock"),
    "/api/v1/teacher/class/<int:class_id>/rotate-code": RouteContract("policy.manage", "api_teacher_rotate_code"),
    "/api/v1/teacher/class/<int:class_id>/set-enrollment-mode": RouteContract(
        "policy.manage",
        "api_teacher_set_enrollment_mode",
    ),
    "/api/v1/teacher/rbac/simulate": RouteContract("rbac.simulate", "api_teacher_rbac_simulate"),
    "/teach": RouteContract(
        "class.view",
        "teach_home",
        required_tokens=("build_teacher_home_context_data(",),
    ),
    "/teach/data-lifespan": RouteContract("syllabus.export", "teach_data_lifespan"),
    "/teach/data-lifespan/export": RouteContract("syllabus.export", "teach_data_lifespan_export"),
    "/teach/login": RouteContract("auth_or_public", "teach_login"),
    "/teach/sso/start/<slug:provider>": RouteContract("auth_or_public", "teach_sso_start"),
    "/teach/sso/callback/<slug:provider>": RouteContract("auth_or_public", "teach_sso_callback"),
    "/teach/profile/update": RouteContract("staff_only", "teach_update_profile"),
    "/teach/profile/password": RouteContract("staff_only", "teach_change_password"),
    "/teach/2fa/setup": RouteContract("auth_or_public", "teach_teacher_2fa_setup"),
    "/teach/create-teacher": RouteContract("org.superuser", "teach_create_teacher"),
    "/teach/teacher-account/set-active": RouteContract("org.superuser", "teach_set_teacher_account_active"),
    "/teach/teacher-account/set-superuser": RouteContract("org.superuser", "teach_set_teacher_account_superuser"),
    "/teach/teacher-account/reset-password": RouteContract("org.superuser", "teach_reset_teacher_account_password"),
    "/teach/teacher-account/resend-invite": RouteContract("org.superuser", "teach_resend_teacher_invite"),
    "/teach/create-organization": RouteContract("org.superuser", "teach_create_organization"),
    "/teach/org-role-capability/upsert": RouteContract("org.superuser", "teach_upsert_org_role_capability"),
    "/teach/org-membership/upsert": RouteContract("org.superuser", "teach_upsert_organization_membership"),
    "/teach/class-staff-assignment/upsert": RouteContract("org.superuser", "teach_upsert_class_staff_assignment"),
    "/teach/class-staff-assignment/bulk-set": RouteContract("org.superuser", "teach_bulk_set_class_staff_assignments"),
    "/teach/class-organization/set": RouteContract("org.superuser", "teach_set_class_organization"),
    "/teach/org/<int:org_id>/rename": RouteContract("org.superuser", "teach_rename_organization"),
    "/teach/org/<int:org_id>/set-active": RouteContract("org.superuser", "teach_set_organization_active"),
    "/teach/generate-authoring-templates": RouteContract("staff_only", "teach_generate_authoring_templates"),
    "/teach/rbac/module-scope-grant/upsert": RouteContract("rbac.manage", "teach_upsert_module_scope_grant"),
    "/teach/rbac/module-scope-grant/set-active": RouteContract("rbac.manage", "teach_set_module_scope_grant_active"),
    "/teach/rbac/simulate": RouteContract("rbac.simulate", "teach_simulate_rbac_access"),
    "/teach/rbac/custom-role/upsert": RouteContract("rbac.manage", "teach_upsert_custom_role"),
    "/teach/rbac/custom-role/capability/upsert": RouteContract("rbac.manage", "teach_upsert_custom_role_capability"),
    "/teach/rbac/custom-role/assignment/upsert": RouteContract("rbac.manage", "teach_upsert_custom_role_assignment"),
    "/teach/rbac/change-request/review": RouteContract("rbac.manage", "teach_review_rbac_change_request"),
    "/teach/rbac/policy/export": RouteContract("rbac.manage", "teach_export_rbac_policy"),
    "/teach/rbac/policy/import": RouteContract("rbac.manage", "teach_import_rbac_policy"),
    "/teach/import-syllabus-source": RouteContract("class.create", "teach_import_syllabus_source"),
    "/teach/authoring-template/download": RouteContract("staff_only", "teach_download_authoring_template"),
    "/teach/syllabus-export": RouteContract("syllabus.export", "teach_export_syllabus"),
    "/teach/logout": RouteContract("auth_or_public", "teacher_logout"),
    "/teach/lessons": RouteContract("class.view", "teach_lessons"),
    "/teach/lessons/release": RouteContract("policy.manage", "teach_set_lesson_release"),
    "/teach/assets": RouteContract("staff_only", "teach_assets"),
    "/teach/create-class": RouteContract("class.create", "teach_create_class"),
    "/teach/class/<int:class_id>": RouteContract("class.view", "teach_class_dashboard"),
    "/teach/class/<int:class_id>/join-card": RouteContract("class.view", "teach_class_join_card"),
    "/teach/class/<int:class_id>/update-landing-page": RouteContract("policy.manage", "teach_update_class_landing"),
    "/teach/class/<int:class_id>/create-invite-link": RouteContract("policy.manage", "teach_create_invite_link"),
    "/teach/class/<int:class_id>/disable-invite-link": RouteContract("policy.manage", "teach_disable_invite_link"),
    "/teach/class/<int:class_id>/set-enrollment-mode": RouteContract("policy.manage", "teach_set_enrollment_mode"),
    "/teach/class/<int:class_id>/set-retention-preset": RouteContract("policy.manage", "teach_set_retention_preset"),
    "/teach/class/<int:class_id>/student/<int:student_id>/return-code": RouteContract(
        "roster.manage",
        "teach_student_return_code",
    ),
    "/teach/class/<int:class_id>/rename-student": RouteContract("roster.manage", "teach_rename_student"),
    "/teach/class/<int:class_id>/merge-students": RouteContract("roster.manage", "teach_merge_students"),
    "/teach/class/<int:class_id>/support-tag/add": RouteContract("roster.manage", "teach_add_support_tag"),
    "/teach/class/<int:class_id>/support-tag/remove": RouteContract("roster.manage", "teach_remove_support_tag"),
    "/teach/class/<int:class_id>/resolve-stuck": RouteContract("roster.manage", "teach_resolve_stuck_flag"),
    "/teach/class/<int:class_id>/resolve-delete-request": RouteContract(
        "roster.manage",
        "teach_resolve_delete_request",
    ),
    "/teach/class/<int:class_id>/delete-student-data": RouteContract("roster.manage", "teach_delete_student_data"),
    "/teach/class/<int:class_id>/reset-roster": RouteContract("roster.manage", "teach_reset_roster"),
    "/teach/class/<int:class_id>/reset-helper-conversations": RouteContract(
        "policy.manage",
        "teach_reset_helper_conversations",
    ),
    "/teach/class/<int:class_id>/toggle-lock": RouteContract("policy.manage", "teach_toggle_lock"),
    "/teach/class/<int:class_id>/lock": RouteContract("policy.manage", "teach_lock_class"),
    "/teach/class/<int:class_id>/export-submissions-today": RouteContract(
        "submission.view",
        "teach_export_class_submissions_today",
    ),
    "/teach/class/<int:class_id>/export-outcomes-csv": RouteContract("submission.view", "teach_export_class_outcomes_csv"),
    "/teach/class/<int:class_id>/export-summary-csv": RouteContract("submission.view", "teach_export_class_summary_csv"),
    "/teach/class/<int:class_id>/certificate-eligibility": RouteContract("class.view", "teach_certificate_eligibility"),
    "/teach/class/<int:class_id>/mark-session-completed": RouteContract("roster.manage", "teach_mark_session_completed"),
    "/teach/class/<int:class_id>/issue-certificate": RouteContract("roster.manage", "teach_issue_certificate"),
    "/teach/class/<int:class_id>/certificate/<int:student_id>/download": RouteContract(
        "roster.manage",
        "teach_download_certificate",
    ),
    "/teach/class/<int:class_id>/certificate/<int:student_id>/download.pdf": RouteContract(
        "roster.manage",
        "teach_download_certificate_pdf",
    ),
    "/teach/class/<int:class_id>/rotate-code": RouteContract("policy.manage", "teach_rotate_code"),
    "/teach/class/<int:class_id>/add-module": RouteContract("class.manage", "teach_add_module"),
    "/teach/class/<int:class_id>/move-module": RouteContract("class.manage", "teach_move_module"),
    "/teach/videos": RouteContract("staff_only", "teach_videos"),
    "/teach/module/<int:module_id>": RouteContract("class.view", "teach_module"),
    "/teach/module/<int:module_id>/add-material": RouteContract("class.manage", "teach_add_material"),
    "/teach/module/<int:module_id>/move-material": RouteContract("class.manage", "teach_move_material"),
    "/teach/module/<int:module_id>/set-gallery-enabled": RouteContract("policy.manage", "teach_set_module_gallery_enabled"),
    "/teach/material/<int:material_id>/submissions": RouteContract("submission.view", "teach_material_submissions"),
    "/teach/material/<int:material_id>/submission/<int:submission_id>/moderate": RouteContract(
        "submission.delete",
        "teach_moderate_gallery_submission",
    ),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON report.",
    )
    return parser.parse_args()


def _iter_teacher_routes(urlconf_path: Path) -> list[tuple[str, str]]:
    raw = urlconf_path.read_text(encoding="utf-8")
    tree = ast.parse(raw, filename=str(urlconf_path))
    routes: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.List):
            continue
        for call in node.value.elts:
            if not isinstance(call, ast.Call):
                continue
            if not isinstance(call.func, ast.Name) or call.func.id != "path":
                continue
            if len(call.args) < 2:
                continue
            route_node, view_node = call.args[0], call.args[1]
            if not isinstance(route_node, ast.Constant) or not isinstance(route_node.value, str):
                continue
            if not isinstance(view_node, ast.Attribute):
                continue
            if not isinstance(view_node.value, ast.Name) or view_node.value.id != "views":
                continue
            route = f"/{route_node.value}"
            if route.startswith("/teach") or route.startswith("/api/v1/teacher"):
                routes.append((route, view_node.attr))
    return routes


def _function_sources(view_root: Path) -> tuple[dict[str, list[tuple[str, str]]], list[str]]:
    mapping: dict[str, list[tuple[str, str]]] = {}
    failures: list[str] = []
    for path in sorted(view_root.rglob("*.py")):
        if path.name.startswith("__"):
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            tree = ast.parse(raw, filename=str(path))
        except Exception as exc:
            failures.append(f"{path}: parse failure: {exc}")
            continue
        lines = raw.splitlines()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.end_lineno is None:
                continue
            decorator_lines = [decorator.lineno for decorator in node.decorator_list]
            start_line = min(decorator_lines) if decorator_lines else node.lineno
            start = max(start_line - 1, 0)
            end = min(node.end_lineno, len(lines))
            source = "\n".join(lines[start:end])
            mapping.setdefault(node.name, []).append((str(path), source))
    return mapping, failures


def main() -> int:
    args = _parse_args()
    failures: list[str] = []

    if not URLCONF_PATH.exists():
        failures.append(f"missing urlconf file: {URLCONF_PATH}")
    if not VIEW_ROOT.exists():
        failures.append(f"missing view root: {VIEW_ROOT}")
    if failures:
        report = {
            "guard": "teacher-endpoint-capability-map",
            "ok": False,
            "routes_checked": 0,
            "contracts": len(ROUTE_CAPABILITY_MAP),
            "failures": failures,
        }
        if args.json_output:
            print(json.dumps(report, sort_keys=True))
        else:
            for row in failures:
                print(f"[teacher-endpoint-capability-map] FAIL: {row}", file=sys.stderr)
        return 1

    discovered_routes = _iter_teacher_routes(URLCONF_PATH)
    function_sources, parse_failures = _function_sources(VIEW_ROOT)
    failures.extend(parse_failures)

    discovered_route_map = {route: view for route, view in discovered_routes}
    for route, view_name in discovered_routes:
        contract = ROUTE_CAPABILITY_MAP.get(route)
        if contract is None:
            failures.append(f"{route}: missing capability contract entry")
            continue
        if contract.view != view_name:
            failures.append(f"{route}: expected view {contract.view!r}, found {view_name!r}")
            continue
        sources = function_sources.get(view_name)
        if not sources:
            failures.append(f"{route}: view function {view_name!r} not found under {VIEW_ROOT}")
            continue
        if contract.required_tokens:
            required_tokens = contract.required_tokens
        else:
            required_tokens = CAPABILITY_TOKEN_RULES.get(contract.capability, ())
        matching_sources = []
        for path, source in sources:
            missing_required = bool(required_tokens) and not any(token in source for token in required_tokens)
            has_forbidden = any(token in source for token in contract.forbidden_tokens)
            if not missing_required and not has_forbidden:
                matching_sources.append((path, source))
        if matching_sources:
            continue
        candidate_paths = ", ".join(path for path, _ in sources)
        if required_tokens:
            failures.append(
                f"{route}: view {view_name} missing capability tokens {required_tokens!r} ({candidate_paths})"
            )
        for token in contract.forbidden_tokens:
            if any(token in source for _path, source in sources):
                failures.append(f"{route}: view {view_name} contains forbidden token {token!r} ({candidate_paths})")

    for route, contract in ROUTE_CAPABILITY_MAP.items():
        if route not in discovered_route_map:
            failures.append(f"contract route missing in urlconf: {route} -> {contract.view}")

    report = {
        "guard": "teacher-endpoint-capability-map",
        "ok": not failures,
        "routes_checked": len(discovered_routes),
        "contracts": len(ROUTE_CAPABILITY_MAP),
        "failures": failures,
    }

    if args.json_output:
        print(json.dumps(report, sort_keys=True))
        return 1 if failures else 0

    if failures:
        print("[teacher-endpoint-capability-map] FAIL: capability route-map drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[teacher-endpoint-capability-map] update route contracts only with intentional capability review.",
            file=sys.stderr,
        )
        return 1

    print(
        "[teacher-endpoint-capability-map] OK "
        f"({len(discovered_routes)} teacher/api routes checked; {len(ROUTE_CAPABILITY_MAP)} contracts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
