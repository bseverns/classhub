#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RELEASE_DATE="$(date +%F)"
COMPOSE_MODE="prod"
BASE_URL=""
SMOKE_TIMEOUT_SECONDS="20"
HELPER_MESSAGE="Help me with AP calculus limits."
FAIL_IMPACT="critical"
A11Y_TIMEOUT_MS="30000"
INSTALL_BROWSERS=0
RELEASE_ZIP_PATH=""
SKIP_RELEASE_ARTIFACT=0
SKIP_SYSTEM_DOCTOR=0
SKIP_A11Y=0
SKIP_RESTORE=0
SKIP_KIOSK=0
SKIP_DOCKER_CHECKS=0

usage() {
  cat <<'EOF'
Usage: bash scripts/stability_release_evidence.sh [options]

Runs the Day 0-30 Track B command checklist and writes logs under:
  artifacts/stability/<release-date>/

Options:
  --release-date <YYYY-MM-DD>       Evidence folder date (default: today)
  --compose-mode <prod|dev>         Compose mode for smoke/a11y/restore/kiosk (default: prod)
  --base-url <url>                  Optional base URL override for smoke + a11y
  --timeout-seconds <seconds>       Smoke timeout seconds (default: 20)
  --helper-message <text>           Helper message for smoke checks
  --fail-impact <impact>            a11y fail impact threshold (default: critical)
  --a11y-timeout-ms <ms>            a11y timeout in milliseconds (default: 30000)
  --install-browsers                Install Playwright browsers in a11y check
  --release-zip <path>              Existing release zip to lint (default: generate one)
  --skip-release-artifact           Skip release artifact lint step
  --skip-system-doctor              Skip system_doctor check
  --skip-a11y                       Skip accessibility smoke check
  --skip-restore                    Skip restore rehearsal check
  --skip-kiosk                      Skip kiosk resilience check
  --skip-docker-checks              Skip system_doctor, a11y, restore, and kiosk checks
  -h, --help                        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-date)
      RELEASE_DATE="$2"
      shift 2
      ;;
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --timeout-seconds)
      SMOKE_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --helper-message)
      HELPER_MESSAGE="$2"
      shift 2
      ;;
    --fail-impact)
      FAIL_IMPACT="$2"
      shift 2
      ;;
    --a11y-timeout-ms)
      A11Y_TIMEOUT_MS="$2"
      shift 2
      ;;
    --install-browsers)
      INSTALL_BROWSERS=1
      shift
      ;;
    --release-zip)
      RELEASE_ZIP_PATH="$2"
      shift 2
      ;;
    --skip-release-artifact)
      SKIP_RELEASE_ARTIFACT=1
      shift
      ;;
    --skip-system-doctor)
      SKIP_SYSTEM_DOCTOR=1
      shift
      ;;
    --skip-a11y)
      SKIP_A11Y=1
      shift
      ;;
    --skip-restore)
      SKIP_RESTORE=1
      shift
      ;;
    --skip-kiosk)
      SKIP_KIOSK=1
      shift
      ;;
    --skip-docker-checks)
      SKIP_DOCKER_CHECKS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[stability-evidence] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
esac
done

if [[ "${SKIP_DOCKER_CHECKS}" == "1" ]]; then
  SKIP_SYSTEM_DOCTOR=1
  SKIP_A11Y=1
  SKIP_RESTORE=1
  SKIP_KIOSK=1
fi

case "${COMPOSE_MODE}" in
  prod|dev)
    ;;
  *)
    echo "[stability-evidence] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
    exit 1
    ;;
esac

EVIDENCE_DIR="${ROOT_DIR}/artifacts/stability/${RELEASE_DATE}"
mkdir -p "${EVIDENCE_DIR}"
RESTORE_METRICS_PATH="${EVIDENCE_DIR}/restore_rehearsal_metrics.json"
RESTORE_SUMMARY_PATH="${EVIDENCE_DIR}/restore_rehearsal_summary.md"
EVIDENCE_INDEX_PATH="${EVIDENCE_DIR}/EVIDENCE_INDEX.md"

FAILED=0
CHECK_ROWS=()

add_row() {
  local name="$1"
  local status="$2"
  local log_rel="$3"
  local notes="$4"
  CHECK_ROWS+=("${name}|${status}|${log_rel}|${notes}")
}

run_check() {
  local name="$1"
  local log_name="$2"
  shift 2

  local log_abs="${EVIDENCE_DIR}/${log_name}"
  local log_rel="artifacts/stability/${RELEASE_DATE}/${log_name}"
  : > "${log_abs}"

  echo "[stability-evidence] ${name}" | tee -a "${log_abs}"
  if "$@" 2>&1 | tee -a "${log_abs}"; then
    add_row "${name}" "PASS" "${log_rel}" "n/a"
  else
    add_row "${name}" "FAIL" "${log_rel}" "inspect log"
    FAILED=1
  fi
}

run_guardrails() {
  local failed=0
  python3 scripts/check_lesson_course_slug_consistency.py || failed=1
  python3 scripts/check_view_size_budgets.py || failed=1
  python3 scripts/check_view_function_budgets.py || failed=1
  python3 scripts/check_teacher_endpoint_capability_map.py || failed=1
  python3 scripts/check_teacher_top_tasks_contract.py || failed=1
  python3 scripts/check_teach_class_template_contract.py || failed=1
  python3 scripts/check_teach_class_section_budgets.py || failed=1
  python3 scripts/check_teacher_roster_service_contract.py || failed=1
  python3 scripts/check_teacher_policy_mode_contract.py || failed=1
  python3 scripts/check_press_capture_backlog_contract.py || failed=1
  python3 scripts/check_rbac_endpoint_guards.py || failed=1
  python3 scripts/check_runtime_policy_lock.py --profile release || failed=1
  python3 scripts/check_docs_truth.py || failed=1
  python3 scripts/check_frontend_static_refs.py || failed=1
  python3 scripts/check_no_inline_template_js.py || failed=1
  python3 scripts/check_no_inline_template_css.py || failed=1
  return "${failed}"
}

run_test_inventory() {
  python3 scripts/check_test_inventory_coverage.py
}

run_system_doctor() {
  local cmd=(
    bash scripts/system_doctor.sh
    --compose-mode "${COMPOSE_MODE}"
    --smoke-mode golden
    --timeout-seconds "${SMOKE_TIMEOUT_SECONDS}"
    --helper-message "${HELPER_MESSAGE}"
  )
  if [[ -n "${BASE_URL}" ]]; then
    cmd+=(--base-url "${BASE_URL}")
  fi
  "${cmd[@]}"
}

run_a11y() {
  local cmd=(
    bash scripts/a11y_smoke.sh
    --compose-mode "${COMPOSE_MODE}"
    --fail-impact "${FAIL_IMPACT}"
    --timeout-ms "${A11Y_TIMEOUT_MS}"
  )
  if [[ "${INSTALL_BROWSERS}" == "1" ]]; then
    cmd+=(--install-browsers)
  fi
  if [[ -n "${BASE_URL}" ]]; then
    cmd+=(--base-url "${BASE_URL}")
  fi
  "${cmd[@]}"
}

run_restore_rehearsal() {
  bash scripts/restore_rehearsal_evidence.sh \
    --compose-mode "${COMPOSE_MODE}" \
    --out-dir "${EVIDENCE_DIR}"
}

write_restore_skipped_placeholders() {
  cat > "${RESTORE_METRICS_PATH}" <<EOF
{
  "workflow": "restore-rehearsal",
  "status": "skipped",
  "release_date": "${RELEASE_DATE}",
  "compose_mode": "${COMPOSE_MODE}"
}
EOF

  cat > "${RESTORE_SUMMARY_PATH}" <<EOF
### Restore Rehearsal Evidence
- Status: SKIPPED
- Release date: ${RELEASE_DATE}
- Reason: --skip-restore or --skip-docker-checks was used for this evidence run.
- Follow-up: run bash scripts/restore_rehearsal_evidence.sh --compose-mode ${COMPOSE_MODE} --out-dir artifacts/stability/${RELEASE_DATE} before release sign-off.
EOF
}

verify_restore_artifacts_present() {
  local missing=0
  if [[ ! -f "${RESTORE_METRICS_PATH}" ]]; then
    echo "[stability-evidence] missing restore artifact: artifacts/stability/${RELEASE_DATE}/restore_rehearsal_metrics.json" >&2
    missing=1
  fi
  if [[ ! -f "${RESTORE_SUMMARY_PATH}" ]]; then
    echo "[stability-evidence] missing restore artifact: artifacts/stability/${RELEASE_DATE}/restore_rehearsal_summary.md" >&2
    missing=1
  fi
  if [[ "${missing}" == "1" ]]; then
    FAILED=1
  fi
}

run_kiosk_resilience() {
  bash scripts/kiosk_resilience_check.sh --non-interactive
}

run_release_artifact_lint() {
  if [[ -n "${RELEASE_ZIP_PATH}" ]]; then
    python3 scripts/lint_release_artifact.py "${RELEASE_ZIP_PATH}"
  else
    bash scripts/make_release_zip.sh
  fi
}

write_evidence_index() {
  local overall_status="PASS"
  if [[ "${FAILED}" == "1" ]]; then
    overall_status="FAIL"
  fi

  {
    echo "# Stability Evidence Index"
    echo ""
    echo "- Release date: ${RELEASE_DATE}"
    echo "- Generated at (UTC): $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "- Git SHA: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
    echo "- Overall status: ${overall_status}"
    echo ""
    echo "## Check Logs"
    echo ""
    echo "| Check | Status | Log | Notes |"
    echo "| --- | --- | --- | --- |"
    for row in "${CHECK_ROWS[@]}"; do
      IFS='|' read -r name status log_path notes <<< "${row}"
      echo "| ${name} | ${status} | \`${log_path}\` | ${notes} |"
    done
    echo ""
    echo "## Key Artifacts"
    echo ""

    local key_artifacts=(
      "guardrails.log"
      "test_inventory_coverage.log"
      "system_doctor.log"
      "a11y_smoke.log"
      "restore_rehearsal.log"
      "restore_rehearsal_metrics.json"
      "restore_rehearsal_summary.md"
      "kiosk_resilience.log"
      "release_artifact_lint.log"
      "operator_scorecard.md"
    )
    local filename
    for filename in "${key_artifacts[@]}"; do
      if [[ -f "${EVIDENCE_DIR}/${filename}" ]]; then
        echo "- \`artifacts/stability/${RELEASE_DATE}/${filename}\`"
      fi
    done

    echo ""
    echo "## Full File Listing"
    echo ""
    while IFS= read -r file_path; do
      file_path="${file_path#${ROOT_DIR}/}"
      echo "- \`${file_path}\`"
    done < <(find "${EVIDENCE_DIR}" -maxdepth 2 -type f | sort)
  } > "${EVIDENCE_INDEX_PATH}"
}

run_check "Guardrails" "guardrails.log" run_guardrails
run_check "Test inventory coverage" "test_inventory_coverage.log" run_test_inventory
if [[ "${SKIP_SYSTEM_DOCTOR}" == "1" ]]; then
  log_rel="artifacts/stability/${RELEASE_DATE}/system_doctor.log"
  log_abs="${EVIDENCE_DIR}/system_doctor.log"
  : > "${log_abs}"
  echo "[stability-evidence] System doctor skipped by flag" | tee -a "${log_abs}"
  add_row "System doctor (golden smoke)" "SKIPPED" "${log_rel}" "skipped by flag"
else
  run_check "System doctor (golden smoke)" "system_doctor.log" run_system_doctor
fi

if [[ "${SKIP_A11Y}" == "1" ]]; then
  log_rel="artifacts/stability/${RELEASE_DATE}/a11y_smoke.log"
  log_abs="${EVIDENCE_DIR}/a11y_smoke.log"
  : > "${log_abs}"
  echo "[stability-evidence] Accessibility smoke skipped by flag" | tee -a "${log_abs}"
  add_row "Accessibility smoke" "SKIPPED" "${log_rel}" "skipped by flag"
else
  run_check "Accessibility smoke" "a11y_smoke.log" run_a11y
fi

if [[ "${SKIP_RESTORE}" == "1" ]]; then
  log_rel="artifacts/stability/${RELEASE_DATE}/restore_rehearsal.log"
  log_abs="${EVIDENCE_DIR}/restore_rehearsal.log"
  : > "${log_abs}"
  echo "[stability-evidence] Restore rehearsal skipped by flag" | tee -a "${log_abs}"
  write_restore_skipped_placeholders
  add_row "Restore rehearsal" "SKIPPED" "${log_rel}" "skipped by flag"
else
  run_check "Restore rehearsal" "restore_rehearsal.log" run_restore_rehearsal
fi
verify_restore_artifacts_present

if [[ "${SKIP_KIOSK}" == "1" ]]; then
  log_rel="artifacts/stability/${RELEASE_DATE}/kiosk_resilience.log"
  log_abs="${EVIDENCE_DIR}/kiosk_resilience.log"
  : > "${log_abs}"
  echo "[stability-evidence] Kiosk resilience skipped by flag" | tee -a "${log_abs}"
  add_row "Kiosk resilience" "SKIPPED" "${log_rel}" "skipped by flag"
else
  run_check "Kiosk resilience" "kiosk_resilience.log" run_kiosk_resilience
fi

if [[ "${SKIP_RELEASE_ARTIFACT}" == "1" ]]; then
  log_rel="artifacts/stability/${RELEASE_DATE}/release_artifact_lint.log"
  log_abs="${EVIDENCE_DIR}/release_artifact_lint.log"
  : > "${log_abs}"
  echo "[stability-evidence] Release artifact lint skipped by flag" | tee -a "${log_abs}"
  add_row "Release artifact lint" "SKIPPED" "${log_rel}" "manual follow-up required"
else
  run_check "Release artifact lint" "release_artifact_lint.log" run_release_artifact_lint
fi

SCORECARD_PATH="${EVIDENCE_DIR}/operator_scorecard.md"
{
  echo "# Operator Scorecard"
  echo ""
  echo "- Release date: ${RELEASE_DATE}"
  echo "- Generated at (UTC): $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "- Git SHA: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
  echo "- Compose mode: ${COMPOSE_MODE}"
  if [[ -n "${BASE_URL}" ]]; then
    echo "- Base URL override: ${BASE_URL}"
  else
    echo "- Base URL override: (none)"
  fi
  echo ""
  echo "## Check Results"
  echo ""
  echo "| Check | Status | Log | Notes |"
  echo "| --- | --- | --- | --- |"
  for row in "${CHECK_ROWS[@]}"; do
    IFS='|' read -r name status log_path notes <<< "${row}"
    echo "| ${name} | ${status} | \`${log_path}\` | ${notes} |"
  done
  echo ""
  echo "## Manual Checks Remaining"
  echo ""
  echo "- Confirm runtime feature flags and rollout modes match release intent."
  echo "- Confirm known-risk register deltas are reflected in release notes."
  echo "- Attach or link artifacts from this folder in release sign-off notes."
} > "${SCORECARD_PATH}"

echo "[stability-evidence] scorecard written: artifacts/stability/${RELEASE_DATE}/operator_scorecard.md"
write_evidence_index
echo "[stability-evidence] evidence index written: artifacts/stability/${RELEASE_DATE}/EVIDENCE_INDEX.md"

if [[ "${FAILED}" == "1" ]]; then
  echo "[stability-evidence] FAIL: one or more checks failed" >&2
  exit 1
fi

echo "[stability-evidence] PASS: evidence pack ready at artifacts/stability/${RELEASE_DATE}/"
