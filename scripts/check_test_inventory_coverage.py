#!/usr/bin/env python3
"""Guardrail: enforce key automated test flow coverage contracts.

This guard intentionally checks for anchor suites/tests/endpoints rather than
raw test counts so normal refactors do not trigger noisy CI failures.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TEST_NAME_RE = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(", re.MULTILINE)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _discover_test_names(path: Path) -> set[str]:
    return set(TEST_NAME_RE.findall(_read(path)))


FILE_CONTRACTS: dict[str, dict] = {
    "test_student_view.py": {
        "required_tests": ("test_student_join_then_student_home_returns_200",),
        "tokens": ("StudentHomeSmokeTests",),
    },
    "services/classhub/hub/tests/test_student_ops.py": {
        "required_tests": (
            "test_join_prefers_device_hint_cookie_with_dedicated_key",
            "test_student_can_publish_later_and_wait_for_teacher_approval",
            "test_student_delete_work_now_clears_submissions_and_upload_events",
        ),
        "tokens": ("JoinClassTests", "StudentDataControlsTests", "/student/portfolio"),
    },
    "services/classhub/hub/tests/test_teacher_admin_portal.py": {
        "required_tests": (
            "test_teach_class_shows_facilitator_support_board",
            "test_teacher_can_moderate_gallery_submission",
            "test_teacher_can_resolve_delete_request",
        ),
        "tokens": ("TeacherPortalTests", "/teach/material/", "/teach/module/"),
    },
    "services/classhub/hub/tests/test_teacher_admin_auth.py": {
        "required_tests": (
            "test_unverified_staff_redirects_to_teacher_2fa_setup",
            "test_teacher_2fa_setup_post_is_rate_limited",
        ),
        "tokens": ("Teacher2FASetupTests", "TeacherOTPEnforcementTests"),
    },
    "services/classhub/hub/tests/test_teacher_admin_release.py": {
        "required_tests": (
            "test_teacher_can_set_release_date_from_interface",
            "test_student_home_shows_preview_link_for_locked_lesson",
        ),
        "tokens": ("LessonReleaseTests",),
    },
    "services/classhub/hub/tests/test_privacy_flow.py": {
        "required_tests": (
            "test_delete_work_removes_submissions",
            "test_trust_page_renders_for_anonymous_visitor",
        ),
        "tokens": ("StudentDeleteWorkTests", "trust"),
    },
    "services/classhub/hub/tests/test_security_integration.py": {
        "required_tests": (
            "test_healthz_sets_security_headers",
            "test_internal_event_endpoint_appends_student_event",
        ),
        "tokens": ("ClassHubSecurityHeaderTests", "InternalHelperEventEndpointTests"),
    },
    "services/classhub/hub/tests/test_api_student.py": {
        "required_tests": (
            "test_authenticated_returns_200_with_correct_shape",
            "test_returns_modules_with_materials",
        ),
        "tokens": ("StudentSessionEndpointTests", "StudentModulesEndpointTests"),
    },
    "services/classhub/hub/tests/test_api_teacher.py": {
        "required_tests": (
            "test_authenticated_staff_returns_classes",
            "test_returns_submissions_with_student_and_material_fields",
        ),
        "tokens": ("TeacherClassesEndpointTests", "TeacherClassSubmissionsEndpointTests"),
    },
    "services/classhub/hub/tests/test_rbac_endpoints.py": {
        "required_tests": (
            "test_viewer_can_view_submissions_but_cannot_manage_policy_or_roster",
            "test_scoped_submission_view_grant_limits_submission_endpoints",
        ),
        "tokens": (
            "EndpointRBACGuardTests",
            "/teach/material/",
            "/api/v1/teacher/class/",
            "/submission/",
        ),
    },
    "services/homework_helper/tutor/tests/test_chat_endpoint.py": {
        "required_tests": (
            "test_chat_requires_class_or_staff_session",
            "test_chat_supports_mock_backend",
        ),
        "tokens": ("HelperChatAuthTests", "/helper/chat"),
    },
    "services/homework_helper/tutor/tests/test_engine.py": {
        "required_tests": (
            "test_invoke_backend_dispatches_to_registry_interface",
            "test_resolve_execution_config_applies_bounds_and_defaults",
        ),
        "tokens": ("BackendEngineTests", "RuntimeConfigEngineTests"),
    },
    "services/homework_helper/tutor/tests/test_view_modules.py": {
        "required_tests": (
            "test_parse_chat_payload_accepts_dict",
            "test_invoke_backend_uses_ollama_registry_entry",
        ),
        "tokens": ("HelperChatRequestModuleTests", "HelperChatRuntimeModuleTests"),
    },
    "services/homework_helper/tutor/tests/test_access.py": {
        "required_tests": (
            "test_helper_admin_requires_superuser",
            "test_healthz_sets_security_headers",
        ),
        "tokens": ("HelperAdminAccessTests", "HelperSecurityHeaderTests"),
    },
    "services/homework_helper/tutor/tests/test_events.py": {
        "required_tests": (
            "test_emit_helper_chat_access_event_posts_to_internal_endpoint",
            "test_emit_helper_chat_access_event_logs_request_id_without_payload",
        ),
        "tokens": ("ClassHubEventForwardingTests",),
    },
    "services/homework_helper/tutor/tests/test_internal_reset.py": {
        "required_tests": (
            "test_internal_reset_clears_class_conversation_keys",
            "test_internal_reset_exports_archive_before_clear",
        ),
        "tokens": ("HelperInternalResetTests",),
    },
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
    checked_files = 0

    for rel_path, contract in FILE_CONTRACTS.items():
        path = Path(rel_path)
        if not path.exists():
            failures.append(f"missing required test file: {rel_path}")
            continue
        checked_files += 1
        text = _read(path)
        discovered = _discover_test_names(path)
        file_test_counts[rel_path] = len(discovered)
        if not discovered:
            failures.append(f"{rel_path}: no test functions discovered")

        for test_name in contract.get("required_tests") or ():
            if test_name not in discovered:
                failures.append(f"{rel_path}: missing required test {test_name!r}")

        for token in contract.get("tokens") or ():
            if token not in text:
                failures.append(f"{rel_path}: missing required token {token!r}")

    for rel_script in REQUIRED_SMOKE_SCRIPTS:
        if not Path(rel_script).exists():
            failures.append(f"missing required smoke script: {rel_script}")

    report = {
        "guard": "test-inventory-coverage",
        "ok": not failures,
        "file_contracts": len(FILE_CONTRACTS),
        "checked_files": checked_files,
        "smoke_script_contracts": len(REQUIRED_SMOKE_SCRIPTS),
        "file_test_counts": file_test_counts,
        "failures": failures,
    }

    if args.json_output:
        print(json.dumps(report, sort_keys=True))
        return 1 if failures else 0

    if failures:
        print("[test-inventory-guard] FAIL: key test flow coverage drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[test-inventory-guard] update explicit flow contracts only with intentional review.", file=sys.stderr)
        return 1

    print(
        "[test-inventory-guard] OK "
        f"({len(FILE_CONTRACTS)} file flow contracts, {len(REQUIRED_SMOKE_SCRIPTS)} smoke scripts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
