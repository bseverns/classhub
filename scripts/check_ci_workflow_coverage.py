#!/usr/bin/env python3
"""Guardrail: critical CI workflow coverage must stay intact.

This is a lightweight contract check so key system surfaces remain covered as
workflows evolve quickly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


WORKFLOW_DIR = Path(".github/workflows")

# Per-workflow string tokens that must remain present.
# Keep tokens specific enough to avoid false positives and simple enough to keep
# this guard dependency-free.
REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    "test-suite.yml": (
        "release-artifact-check:",
        "classhub-tests:",
        "helper-tests:",
        "validate_coursepack.py --all",
        "python services/classhub/manage.py check",
        "services/classhub/manage.py test",
        "python services/homework_helper/manage.py check",
        "services/homework_helper/manage.py test",
    ),
    "stack-smoke.yml": (
        "doctor:",
        "scripts/system_doctor.sh",
        "scripts/a11y_smoke.sh",
    ),
    "migration-gate.yml": (
        "classhub:",
        "helper:",
        "services/classhub/manage.py makemigrations --check --dry-run",
        "services/homework_helper/manage.py makemigrations --check --dry-run",
    ),
    "deploy-check.yml": (
        "classhub-deploy-check:",
        "helper-deploy-check:",
        "services/classhub/manage.py check --deploy --fail-level WARNING",
        "services/homework_helper/manage.py check --deploy --fail-level WARNING",
    ),
    "lint.yml": (
        "ruff:",
        "ruff check services scripts --select E9,F63,F7,F82",
        "python scripts/check_frontend_static_refs.py",
        "python scripts/check_rbac_endpoint_guards.py",
        "python scripts/check_teacher_endpoint_capability_map.py",
        "python scripts/check_teacher_policy_mode_contract.py",
        "python scripts/check_lesson_course_slug_consistency.py",
        "python scripts/check_view_size_budgets.py",
        "python scripts/check_no_service_imports_from_views.py",
    ),
    "security.yml": (
        "secret-scan:",
        "dependency-audit:",
        "sast-bandit:",
        "gitleaks/gitleaks-action@v2",
        "pip-audit -r services/classhub/requirements.txt",
        "pip-audit -r services/homework_helper/requirements.txt",
        "scripts/run_bandit.sh all bandit-report.json",
    ),
    "codeql.yml": (
        "name: codeql",
        "github/codeql-action/init@v3",
        "github/codeql-action/analyze@v3",
    ),
    "workflow-lint.yml": (
        "parse-yaml:",
        "Validate workflow YAML",
        "rhysd/actionlint@",
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


def _load_workflow(path: Path) -> tuple[str, str]:
    try:
        return path.read_text(encoding="utf-8"), ""
    except Exception as exc:
        return "", f"could not read {path}: {exc}"


def main() -> int:
    args = _parse_args()
    if not WORKFLOW_DIR.exists():
        report = {
            "guard": "ci-workflow-coverage",
            "ok": False,
            "required_workflows": len(REQUIRED_TOKENS),
            "checked_workflows": 0,
            "failures": [f"missing workflow dir: {WORKFLOW_DIR}"],
        }
        if args.json_output:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"[ci-workflow-coverage] FAIL: missing workflow dir: {WORKFLOW_DIR}", file=sys.stderr)
        return 1

    failures: list[str] = []
    checked_workflows = 0
    for filename, tokens in REQUIRED_TOKENS.items():
        workflow_path = WORKFLOW_DIR / filename
        if not workflow_path.exists():
            failures.append(f"missing workflow file: {workflow_path}")
            continue
        checked_workflows += 1
        raw, load_error = _load_workflow(workflow_path)
        if load_error:
            failures.append(load_error)
            continue
        for token in tokens:
            if token not in raw:
                failures.append(f"{workflow_path}: missing required token: {token!r}")

    report = {
        "guard": "ci-workflow-coverage",
        "ok": not failures,
        "required_workflows": len(REQUIRED_TOKENS),
        "checked_workflows": checked_workflows,
        "failures": failures,
    }

    if args.json_output:
        print(json.dumps(report, sort_keys=True))
        return 1 if failures else 0

    if failures:
        print("[ci-workflow-coverage] FAIL: critical CI workflow coverage drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        return 1

    print(f"[ci-workflow-coverage] OK ({len(REQUIRED_TOKENS)} workflows checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
