#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"

RELEASE_DATE="$(date +%F)"
COMPOSE_MODE="prod"
WINDOW_DAYS="7"
SMOKE_TIMEOUT_SECONDS="20"
HELPER_MESSAGE="Help me with AP calculus limits."
FAIL_IMPACT="serious"
A11Y_TIMEOUT_MS="30000"
INSTALL_BROWSERS=0
BASE_URL=""
SKIP_STABILITY_EVIDENCE=0
SKIP_TELEMETRY_EVIDENCE=0
SKIP_KIOSK=0
STUDENT_HOME_P95_MS="${STUDENT_HOME_P95_MS:-}"
STUDENT_HOME_P95_BASELINE_MS="${STUDENT_HOME_P95_BASELINE_MS:-}"
STUDENT_UPLOAD_SUCCESS_RATE_PCT="${STUDENT_UPLOAD_SUCCESS_RATE_PCT:-}"
STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT="${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT:-}"
HELPER_CHAT_5XX_RATE_PCT="${HELPER_CHAT_5XX_RATE_PCT:-}"
HELPER_CHAT_5XX_RATE_BASELINE_PCT="${HELPER_CHAT_5XX_RATE_BASELINE_PCT:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/stability_phase1_closeout.sh [options]

Runs one full closeout cycle for:
- 30-day stability plan Phase 1 (Tracks A/B/C evidence pack)
- telemetry DB split Phase 1 Slice 7 evidence packet

Options:
  --release-date <YYYY-MM-DD>       Evidence folder date (default: today)
  --compose-mode <prod|dev>         Compose mode for evidence scripts (default: prod)
  --window-days <n>                 Telemetry parity window days (default: 7)
  --timeout-seconds <seconds>       Smoke timeout seconds (default: 20)
  --helper-message <text>           Helper message for smoke checks
  --fail-impact <impact>            a11y fail impact threshold (default: serious)
  --a11y-timeout-ms <ms>            a11y timeout in milliseconds (default: 30000)
  --install-browsers                Install Playwright browsers in a11y check
  --base-url <url>                  Optional base URL override for smoke/a11y/telemetry smoke
  --student-home-p95-ms <ms>        Observed student home p95 for the release window
  --student-home-p95-baseline-ms <ms>
                                     Pre-cutover student home p95 baseline
  --student-upload-success-rate-pct <pct>
                                     Observed student upload success rate for the release window
  --student-upload-success-rate-baseline-pct <pct>
                                     Pre-cutover upload success baseline
  --helper-chat-5xx-rate-pct <pct>  Observed helper chat 5xx rate for the release window
  --helper-chat-5xx-rate-baseline-pct <pct>
                                     Pre-cutover helper chat 5xx baseline
  --skip-stability-evidence         Reuse existing release evidence artifacts
  --skip-telemetry-evidence         Reuse existing telemetry evidence artifacts
  --skip-kiosk                      Skip kiosk resilience inside stability evidence
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
    --window-days)
      WINDOW_DAYS="$2"
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
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --student-home-p95-ms)
      STUDENT_HOME_P95_MS="$2"
      shift 2
      ;;
    --student-home-p95-baseline-ms)
      STUDENT_HOME_P95_BASELINE_MS="$2"
      shift 2
      ;;
    --student-upload-success-rate-pct)
      STUDENT_UPLOAD_SUCCESS_RATE_PCT="$2"
      shift 2
      ;;
    --student-upload-success-rate-baseline-pct)
      STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT="$2"
      shift 2
      ;;
    --helper-chat-5xx-rate-pct)
      HELPER_CHAT_5XX_RATE_PCT="$2"
      shift 2
      ;;
    --helper-chat-5xx-rate-baseline-pct)
      HELPER_CHAT_5XX_RATE_BASELINE_PCT="$2"
      shift 2
      ;;
    --skip-stability-evidence)
      SKIP_STABILITY_EVIDENCE=1
      shift
      ;;
    --skip-telemetry-evidence)
      SKIP_TELEMETRY_EVIDENCE=1
      shift
      ;;
    --skip-kiosk)
      SKIP_KIOSK=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[cycle-closeout] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "${COMPOSE_MODE}" in
  prod|dev)
    ;;
  *)
    echo "[cycle-closeout] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
    exit 1
    ;;
esac

if [[ ! "${WINDOW_DAYS}" =~ ^[0-9]+$ ]] || (( WINDOW_DAYS <= 0 )); then
  echo "[cycle-closeout] --window-days must be a positive integer" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[cycle-closeout] missing compose/.env" >&2
  exit 1
fi

validate_optional_decimal() {
  local label="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    return 0
  fi
  if [[ ! "${value}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "[cycle-closeout] ${label} must be numeric when provided" >&2
    exit 1
  fi
}

validate_optional_decimal "--student-home-p95-ms" "${STUDENT_HOME_P95_MS}"
validate_optional_decimal "--student-home-p95-baseline-ms" "${STUDENT_HOME_P95_BASELINE_MS}"
validate_optional_decimal "--student-upload-success-rate-pct" "${STUDENT_UPLOAD_SUCCESS_RATE_PCT}"
validate_optional_decimal "--student-upload-success-rate-baseline-pct" "${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT}"
validate_optional_decimal "--helper-chat-5xx-rate-pct" "${HELPER_CHAT_5XX_RATE_PCT}"
validate_optional_decimal "--helper-chat-5xx-rate-baseline-pct" "${HELPER_CHAT_5XX_RATE_BASELINE_PCT}"

EVIDENCE_DIR="${ROOT_DIR}/artifacts/stability/${RELEASE_DATE}"
TELEMETRY_DIR="${EVIDENCE_DIR}/telemetry"
RUNTIME_LOCK_LOG="${EVIDENCE_DIR}/runtime_lock_check.log"
SLO_SUMMARY_PATH="${TELEMETRY_DIR}/slo_summary.md"
CYCLE_SUMMARY_PATH="${EVIDENCE_DIR}/cycle_closeout_summary.md"
mkdir -p "${TELEMETRY_DIR}"

assert_runtime_lock() {
  if ! python3 "${ROOT_DIR}/scripts/check_runtime_policy_lock.py" \
    --profile release \
    --env-file "${ENV_FILE}" \
    --markdown > "${RUNTIME_LOCK_LOG}" 2>&1; then
    echo "[cycle-closeout] runtime lock check failed; see artifacts/stability/${RELEASE_DATE}/runtime_lock_check.log" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"
  if [[ ! -f "${file_path}" ]]; then
    echo "[cycle-closeout] missing required artifact: ${file_path}" >&2
    exit 1
  fi
}

assert_runtime_lock

if (( SKIP_STABILITY_EVIDENCE == 0 )); then
  stable_cmd=(
    bash scripts/stability_release_evidence.sh
    --release-date "${RELEASE_DATE}"
    --compose-mode "${COMPOSE_MODE}"
    --timeout-seconds "${SMOKE_TIMEOUT_SECONDS}"
    --helper-message "${HELPER_MESSAGE}"
    --fail-impact "${FAIL_IMPACT}"
    --a11y-timeout-ms "${A11Y_TIMEOUT_MS}"
  )
  if (( INSTALL_BROWSERS == 1 )); then
    stable_cmd+=(--install-browsers)
  fi
  if (( SKIP_KIOSK == 1 )); then
    stable_cmd+=(--skip-kiosk)
  fi
  if [[ -n "${BASE_URL}" ]]; then
    stable_cmd+=(--base-url "${BASE_URL}")
  fi
  "${stable_cmd[@]}"
fi

if (( SKIP_TELEMETRY_EVIDENCE == 0 )); then
  telemetry_cmd=(
    bash scripts/telemetry_stabilization_evidence.sh
    --compose-mode "${COMPOSE_MODE}"
    --window-days "${WINDOW_DAYS}"
    --out-dir "${TELEMETRY_DIR}"
    --smoke-timeout-seconds "${SMOKE_TIMEOUT_SECONDS}"
    --perform-rollback-drill
  )
  if [[ -n "${BASE_URL}" ]]; then
    telemetry_cmd+=(--base-url "${BASE_URL}")
  fi
  if [[ -n "${STUDENT_HOME_P95_MS}" ]]; then
    telemetry_cmd+=(--student-home-p95-ms "${STUDENT_HOME_P95_MS}")
  fi
  if [[ -n "${STUDENT_HOME_P95_BASELINE_MS}" ]]; then
    telemetry_cmd+=(--student-home-p95-baseline-ms "${STUDENT_HOME_P95_BASELINE_MS}")
  fi
  if [[ -n "${STUDENT_UPLOAD_SUCCESS_RATE_PCT}" ]]; then
    telemetry_cmd+=(--student-upload-success-rate-pct "${STUDENT_UPLOAD_SUCCESS_RATE_PCT}")
  fi
  if [[ -n "${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT}" ]]; then
    telemetry_cmd+=(--student-upload-success-rate-baseline-pct "${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT}")
  fi
  if [[ -n "${HELPER_CHAT_5XX_RATE_PCT}" ]]; then
    telemetry_cmd+=(--helper-chat-5xx-rate-pct "${HELPER_CHAT_5XX_RATE_PCT}")
  fi
  if [[ -n "${HELPER_CHAT_5XX_RATE_BASELINE_PCT}" ]]; then
    telemetry_cmd+=(--helper-chat-5xx-rate-baseline-pct "${HELPER_CHAT_5XX_RATE_BASELINE_PCT}")
  fi
  "${telemetry_cmd[@]}"
fi

render_slo_cmd=(
  python3 "${ROOT_DIR}/scripts/render_telemetry_slo_summary.py"
  --out "${SLO_SUMMARY_PATH}"
  --release-date "${RELEASE_DATE}"
  --window-days "${WINDOW_DAYS}"
  --parity-threshold-label "strict zero drift"
  --steady-write-mode-label "remain \`dual\`"
  --gate-d-label "deferred to next cycle"
  --require-complete
  --require-pass
)
if [[ -n "${STUDENT_HOME_P95_MS}" ]]; then
  render_slo_cmd+=(--student-home-p95-ms "${STUDENT_HOME_P95_MS}")
fi
if [[ -n "${STUDENT_HOME_P95_BASELINE_MS}" ]]; then
  render_slo_cmd+=(--student-home-p95-baseline-ms "${STUDENT_HOME_P95_BASELINE_MS}")
fi
if [[ -n "${STUDENT_UPLOAD_SUCCESS_RATE_PCT}" ]]; then
  render_slo_cmd+=(--student-upload-success-rate-pct "${STUDENT_UPLOAD_SUCCESS_RATE_PCT}")
fi
if [[ -n "${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT}" ]]; then
  render_slo_cmd+=(--student-upload-success-rate-baseline-pct "${STUDENT_UPLOAD_SUCCESS_RATE_BASELINE_PCT}")
fi
if [[ -n "${HELPER_CHAT_5XX_RATE_PCT}" ]]; then
  render_slo_cmd+=(--helper-chat-5xx-rate-pct "${HELPER_CHAT_5XX_RATE_PCT}")
fi
if [[ -n "${HELPER_CHAT_5XX_RATE_BASELINE_PCT}" ]]; then
  render_slo_cmd+=(--helper-chat-5xx-rate-baseline-pct "${HELPER_CHAT_5XX_RATE_BASELINE_PCT}")
fi
"${render_slo_cmd[@]}"

required_release_files=(
  "${EVIDENCE_DIR}/system_doctor.log"
  "${EVIDENCE_DIR}/a11y_smoke.log"
  "${EVIDENCE_DIR}/restore_rehearsal.log"
  "${EVIDENCE_DIR}/restore_rehearsal_metrics.json"
  "${EVIDENCE_DIR}/restore_rehearsal_summary.md"
  "${EVIDENCE_DIR}/guardrails.log"
  "${EVIDENCE_DIR}/release_artifact_lint.log"
  "${EVIDENCE_DIR}/operator_scorecard.md"
  "${EVIDENCE_DIR}/EVIDENCE_INDEX.md"
  "${EVIDENCE_DIR}/runtime_lock_check.log"
)

required_telemetry_files=(
  "${TELEMETRY_DIR}/metadata.env"
  "${TELEMETRY_DIR}/parity_check.log"
  "${TELEMETRY_DIR}/smoke_strict.log"
  "${TELEMETRY_DIR}/rollback_drill.log"
  "${TELEMETRY_DIR}/summary.md"
  "${TELEMETRY_DIR}/slo_summary.md"
)

for f in "${required_release_files[@]}"; do
  require_file "${f}"
done
for f in "${required_telemetry_files[@]}"; do
  require_file "${f}"
done

if ! grep -Fq -- "- Parity: pass" "${TELEMETRY_DIR}/summary.md"; then
  echo "[cycle-closeout] telemetry parity did not pass with strict zero drift; see ${TELEMETRY_DIR}/parity_check.log" >&2
  exit 1
fi
if ! grep -Fq -- "- Smoke: pass" "${TELEMETRY_DIR}/summary.md"; then
  echo "[cycle-closeout] telemetry smoke did not pass; see ${TELEMETRY_DIR}/smoke_strict.log" >&2
  exit 1
fi
if ! grep -Fq -- "- Rollback drill: pass" "${TELEMETRY_DIR}/summary.md"; then
  echo "[cycle-closeout] telemetry rollback drill did not pass; see ${TELEMETRY_DIR}/rollback_drill.log" >&2
  exit 1
fi

cat > "${CYCLE_SUMMARY_PATH}" <<EOF
# Stability + Telemetry Cycle Closeout Summary

- Release date: ${RELEASE_DATE}
- Generated at (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Phase 1 scope: Track A/B/C evidence + telemetry Slice 7 evidence

## Artifact Packet

- Release evidence root: \`artifacts/stability/${RELEASE_DATE}/\`
- Evidence index: \`artifacts/stability/${RELEASE_DATE}/EVIDENCE_INDEX.md\`
- Telemetry evidence root: \`artifacts/stability/${RELEASE_DATE}/telemetry/\`
- Runtime lock check: \`artifacts/stability/${RELEASE_DATE}/runtime_lock_check.log\`

## Gate policy for this cycle

- Strict org-boundary mode: \`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1\`
- Telemetry modes: \`CLASSHUB_TELEMETRY_WRITE_MODE=dual\`, \`CLASSHUB_TELEMETRY_READ_MODE=telemetry\`
- Parity threshold: strict zero drift
- Gate D (\`telemetry_only\`) decision: deferred

## Required doc updates before sign-off

- Add review row in \`docs/STABILITY_OWNER_CADENCE.md\` (R1-R5 coverage)
- Add drill row in \`docs/TURNOVER_DRILL_LOG.md\`
- Confirm org-boundary row in \`docs/ORG_BOUNDARY_POLICY_AUDIT.md\`
- Add decision note in \`docs/DECISIONS.md\` for Gate C closeout (\`dual\` retained)
EOF

echo "[cycle-closeout] PASS: artifacts ready at artifacts/stability/${RELEASE_DATE}/"
echo "[cycle-closeout] next: update docs/STABILITY_OWNER_CADENCE.md, docs/TURNOVER_DRILL_LOG.md, docs/DECISIONS.md"
