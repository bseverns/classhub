#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROFILE="${1:-baseline}"
ENV_FILE="${2:-compose/.env}"
if [[ "${PROFILE}" != "baseline" && "${PROFILE}" != "release" ]]; then
  echo "[ops-readiness] invalid profile '${PROFILE}' (expected baseline|release)" >&2
  exit 1
fi

echo "[ops-readiness] runtime policy lock (${PROFILE}) env=${ENV_FILE}"
python3 scripts/check_runtime_policy_lock.py --profile "${PROFILE}" --env-file "${ENV_FILE}"
python3 scripts/check_csp_runtime_contract.py --env-file "${ENV_FILE}"

echo "[ops-readiness] teach-class decomposition contracts"
python3 scripts/check_teach_class_template_contract.py
python3 scripts/check_teach_class_section_budgets.py
python3 scripts/check_teacher_roster_service_contract.py
python3 scripts/check_teacher_admin_hotspot_budgets.py

echo "[ops-readiness] policy/RBAC advanced-mode contract"
python3 scripts/check_teacher_policy_mode_contract.py

echo "[ops-readiness] docs and inventory truth"
python3 scripts/check_docs_truth.py
python3 scripts/check_test_inventory_coverage.py
python3 scripts/check_lesson_course_slug_consistency.py
python3 scripts/check_i18n_family_visible_contract.py

echo "[ops-readiness] press backlog governance"
python3 scripts/check_press_capture_backlog_contract.py

echo "[ops-readiness] operator posture snapshot"
python3 scripts/security_posture_snapshot.py --env-file "${ENV_FILE}"

echo "[ops-readiness] PASS"
