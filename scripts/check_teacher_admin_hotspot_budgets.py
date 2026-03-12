#!/usr/bin/env python3
"""Guardrail: cap growth in teacher/admin/RBAC hotspot files."""

from __future__ import annotations

import sys
from pathlib import Path


HOTSPOT_BUDGETS: dict[Path, int] = {
    Path("services/classhub/hub/tests/test_teacher_admin_portal.py"): 600,
    Path("services/classhub/hub/tests/test_teacher_admin_portal_class_ops.py"): 1500,
    Path("services/classhub/hub/tests/test_teacher_admin_portal_class_content_admin_ops.py"): 800,
    Path("services/classhub/hub/tests/test_teacher_admin_portal_teacher_accounts.py"): 500,
    Path("services/classhub/hub/tests/_teacher_admin_portal_base.py"): 120,
    Path("services/classhub/hub/tests/test_teacher_admin_portal_org_access.py"): 1700,
    Path("services/classhub/hub/services/org_access.py"): 260,
    Path("services/classhub/hub/services/org_access_capabilities.py"): 90,
    Path("services/classhub/hub/services/org_access_capabilities_shared.py"): 130,
    Path("services/classhub/hub/services/org_access_capabilities_roles.py"): 230,
    Path("services/classhub/hub/services/org_access_capabilities_scope.py"): 100,
    Path("services/classhub/hub/services/org_access_capabilities_policy.py"): 380,
    Path("services/classhub/hub/services/rbac_policy_bundle.py"): 180,
    Path("services/classhub/hub/services/rbac_policy_bundle_normalize.py"): 60,
    Path("services/classhub/hub/services/rbac_policy_bundle_schema.py"): 120,
    Path("services/classhub/hub/services/rbac_policy_bundle_export.py"): 190,
    Path("services/classhub/hub/services/rbac_policy_bundle_import.py"): 360,
    Path("services/classhub/hub/services/rbac_policy_bundle_apply.py"): 180,
    Path("services/classhub/hub/services/teacher_tracker.py"): 90,
    Path("services/classhub/hub/services/teacher_tracker_digest.py"): 220,
    Path("services/classhub/hub/services/teacher_tracker_helper_signals.py"): 180,
    Path("services/classhub/hub/services/teacher_tracker_lessons.py"): 340,
    Path("services/classhub/hub/services/teacher_roster_class.py"): 80,
    Path("services/classhub/hub/services/teacher_roster_class_dashboard.py"): 220,
    Path("services/classhub/hub/services/teacher_roster_class_exports.py"): 60,
    Path("services/classhub/hub/services/teacher_roster_class_exports_archive.py"): 120,
    Path("services/classhub/hub/services/teacher_roster_class_exports_summary.py"): 280,
    Path("services/classhub/hub/services/teacher_roster_class_exports_outcomes.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/roster_class.py"): 90,
    Path("services/classhub/hub/views/teacher_parts/roster_class_dashboard.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/roster_class_controls.py"): 330,
    Path("services/classhub/hub/views/teacher_parts/roster_materials.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/roster_materials_module_ops.py"): 280,
    Path("services/classhub/hub/views/teacher_parts/roster_materials_submissions.py"): 200,
    Path("services/classhub/hub/views/teacher_parts/roster_students.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/roster_students_identity.py"): 170,
    Path("services/classhub/hub/views/teacher_parts/roster_students_lifecycle.py"): 240,
    Path("services/classhub/hub/views/teacher_parts/roster_invites.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/roster_invites_links.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/roster_invites_exports.py"): 210,
    Path("services/classhub/hub/views/teacher_parts/roster_orgs.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/roster_orgs_shared.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/roster_orgs_organizations.py"): 170,
    Path("services/classhub/hub/views/teacher_parts/roster_orgs_membership_policy.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/roster_support.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/roster_support_signals.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/roster_support_tags.py"): 190,
    Path("services/classhub/hub/views/teacher_parts/auth_teacher_accounts.py"): 60,
    Path("services/classhub/hub/views/teacher_parts/auth_teacher_accounts_shared.py"): 120,
    Path("services/classhub/hub/views/teacher_parts/auth_teacher_accounts_onboarding.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/auth_teacher_accounts_controls.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/auth_sso.py"): 240,
    Path("services/classhub/hub/views/teacher_parts/auth_sso_core.py"): 80,
    Path("services/classhub/hub/views/teacher_parts/auth_sso_core_providers.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/auth_sso_core_state.py"): 120,
    Path("services/classhub/hub/views/teacher_parts/auth_sso_core_callback.py"): 120,
    Path("services/classhub/hub/views/teacher_parts/auth_sso_google_flow.py"): 140,
    Path("services/classhub/hub/views/teacher_parts/content_home_context.py"): 100,
    Path("services/classhub/hub/views/teacher_parts/content_home_context_state.py"): 140,
    Path("services/classhub/hub/views/teacher_parts/content_home_context_portal.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/content_home_context_payloads.py"): 220,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_access.py"): 40,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_endpoints.py"): 90,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_context.py"): 180,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_helpers.py"): 80,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_state.py"): 120,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_change_requests.py"): 190,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_mutations.py"): 280,
    Path("services/classhub/hub/views/teacher_parts/content_rbac_view_review.py"): 190,
    Path("services/classhub/templates/includes/teach_home/setup_sections_rbac_panel.html"): 80,
    Path("services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_scope_and_simulation.html"): 230,
    Path("services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_custom_roles.html"): 210,
    Path("services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_policy_and_audit.html"): 210,
    Path("services/classhub/templates/includes/teach_home/setup_sections_org_admin_panel.html"): 60,
    Path("services/classhub/templates/includes/teach_home/org_admin/org_admin_organizations_and_memberships.html"): 220,
    Path("services/classhub/templates/includes/teach_home/org_admin/org_admin_class_assignments_and_moves.html"): 190,
    Path("services/classhub/templates/includes/teach_home/org_admin/org_admin_role_capability_templates.html"): 120,
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
