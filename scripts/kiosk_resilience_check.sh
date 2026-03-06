#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"

BASE_URL=""
REPORT_FILE="/tmp/classhub_kiosk_resilience_$(date +%Y%m%d_%H%M%S).md"
TIMEOUT_SECONDS=20
INSECURE_TLS=0
INTERACTIVE=1
DRY_RUN=0
CLASS_CODE=""
DISPLAY_NAME="Kiosk Smoke Student"

usage() {
  cat <<'USAGE'
Usage: bash scripts/kiosk_resilience_check.sh [options]

Runs kiosk/PWA resilience validation in two parts:
1) deterministic HTTP checks (manifest, service worker, kiosk route guard),
2) unstable-network queue drill checklist with optional interactive pass/fail prompts.

Options:
  --base-url <url>          Base URL (default: derive from compose/.env)
  --report <path>           Markdown report output path (default: /tmp/classhub_kiosk_resilience_<ts>.md)
  --timeout-seconds <n>     Curl timeout in seconds (default: 20)
  --insecure                Allow insecure TLS (-k)
  --class-code <code>       Optional class code for session-aware route guard checks
  --display-name <name>     Display name used with --class-code join (default: Kiosk Smoke Student)
  --non-interactive         Do not prompt; emit manual checklist as TODO items
  --dry-run                 Print/report checklist without running HTTP calls
  -h, --help                Show this help
USAGE
}

env_file_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo ""
    return 0
  fi
  local raw
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

derive_base_url() {
  local caddyfile_template
  local env_base
  local domain
  caddyfile_template="$(env_file_value CADDYFILE_TEMPLATE)"
  env_base="$(env_file_value SMOKE_BASE_URL)"
  domain="$(env_file_value DOMAIN)"

  if [[ "${caddyfile_template}" == "Caddyfile.local" ]]; then
    echo "http://localhost"
  elif [[ -n "${env_base}" ]]; then
    echo "${env_base}"
  elif [[ -n "${domain}" ]]; then
    echo "https://${domain}"
  else
    echo "http://localhost"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --report)
      REPORT_FILE="$2"
      shift 2
      ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --insecure)
      INSECURE_TLS=1
      shift
      ;;
    --class-code)
      CLASS_CODE="$2"
      shift 2
      ;;
    --display-name)
      DISPLAY_NAME="$2"
      shift 2
      ;;
    --non-interactive)
      INTERACTIVE=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      INTERACTIVE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[kiosk-resilience] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BASE_URL}" ]]; then
  BASE_URL="$(derive_base_url)"
fi
if [[ -z "${CLASS_CODE}" ]]; then
  CLASS_CODE="${KIOSK_SMOKE_CLASS_CODE:-$(env_file_value SMOKE_CLASS_CODE)}"
fi

CURL_FLAGS=(-sS --max-time "${TIMEOUT_SECONDS}")
if [[ "${INSECURE_TLS}" == "1" ]]; then
  CURL_FLAGS+=(-k)
fi

mkdir -p "$(dirname "${REPORT_FILE}")"
: > "${REPORT_FILE}"

TMP_HEADERS="$(mktemp)"
TMP_BODY="$(mktemp)"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "${TMP_HEADERS}" "${TMP_BODY}" "${COOKIE_JAR}"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

report_line() {
  local text="$1"
  echo "${text}" | tee -a "${REPORT_FILE}" >/dev/null
}

mark_pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  report_line "- PASS: $1"
}

mark_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  report_line "- FAIL: $1"
}

mark_skip() {
  SKIP_COUNT=$((SKIP_COUNT + 1))
  report_line "- SKIP: $1"
}

http_check() {
  local label="$1"
  local url="$2"
  local expected_code="$3"

  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "${label} (dry-run): expected HTTP ${expected_code} at ${url}"
    return 0
  fi

  local code
  code="$(curl "${CURL_FLAGS[@]}" -o "${TMP_BODY}" -D "${TMP_HEADERS}" -w "%{http_code}" "${url}" || true)"
  if [[ "${code}" == "${expected_code}" ]]; then
    mark_pass "${label}: HTTP ${code}"
    return 0
  fi
  mark_fail "${label}: expected HTTP ${expected_code}, got ${code} (${url})"
  return 1
}

kiosk_cookie_check() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "kiosk toggle cookie check (dry-run)"
    return 0
  fi

  local code
  code="$(curl "${CURL_FLAGS[@]}" -c "${COOKIE_JAR}" -b "${COOKIE_JAR}" -o "${TMP_BODY}" -w "%{http_code}" "${BASE_URL}/?kiosk=1" || true)"
  if [[ "${code}" != "200" ]]; then
    mark_fail "kiosk toggle request expected 200, got ${code}"
    return 1
  fi
  if grep -q "classhub_student_kiosk_mode" "${COOKIE_JAR}"; then
    mark_pass "kiosk toggle sets classhub_student_kiosk_mode cookie"
    return 0
  fi
  mark_fail "kiosk toggle did not set classhub_student_kiosk_mode cookie"
  return 1
}

manifest_payload_check() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "manifest payload check (dry-run)"
    return 0
  fi

  if ! python3 - <<'PY' "${TMP_BODY}"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert payload.get('start_url') == '/?kiosk=1'
assert payload.get('display') == 'standalone'
icons = payload.get('icons') or []
assert any('student-kiosk-192.svg' in str(icon.get('src', '')) for icon in icons)
assert any('student-kiosk-512.svg' in str(icon.get('src', '')) for icon in icons)
PY
  then
    mark_fail "manifest payload missing expected kiosk properties"
    return 1
  fi

  mark_pass "manifest payload includes kiosk start_url/display/icons"
  return 0
}

service_worker_header_check() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "service worker header check (dry-run)"
    return 0
  fi

  if grep -Eqi '^Service-Worker-Allowed:[[:space:]]*/' "${TMP_HEADERS}"; then
    mark_pass "service worker endpoint sets Service-Worker-Allowed: /"
    return 0
  fi
  mark_fail "service worker endpoint missing Service-Worker-Allowed: /"
  return 1
}

kiosk_route_guard_check() {
  local expected_location="$1"

  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "kiosk route guard redirect check (dry-run)"
    return 0
  fi

  local code
  code="$(curl "${CURL_FLAGS[@]}" -c "${COOKIE_JAR}" -b "${COOKIE_JAR}" -o "${TMP_BODY}" -D "${TMP_HEADERS}" -w "%{http_code}" "${BASE_URL}/student/portfolio" || true)"
  if [[ "${code}" != "302" ]]; then
    mark_fail "kiosk route guard expected HTTP 302 for /student/portfolio, got ${code}"
    return 1
  fi

  local location
  location="$(grep -Ei '^Location:' "${TMP_HEADERS}" | tail -n1 | sed -E 's/^Location:[[:space:]]*//I' | tr -d '\r')"
  if [[ "${location}" == "${expected_location}" ]]; then
    mark_pass "kiosk route guard redirects /student/portfolio to ${location}"
    return 0
  fi

  mark_fail "kiosk route guard expected Location ${expected_location}, got ${location:-<none>}"
  return 1
}

session_join_check() {
  if [[ -z "${CLASS_CODE}" ]]; then
    mark_skip "session-aware kiosk redirect check (no class code provided)"
    return 0
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    mark_skip "session join + kiosk redirect check (dry-run)"
    return 0
  fi

  curl "${CURL_FLAGS[@]}" -c "${COOKIE_JAR}" -b "${COOKIE_JAR}" -o /dev/null "${BASE_URL}/"
  local csrf
  csrf="$(awk '$6=="csrftoken"{print $7}' "${COOKIE_JAR}" | tail -n1)"
  if [[ -z "${csrf}" ]]; then
    mark_fail "could not resolve csrf token before /join"
    return 1
  fi

  local payload
  payload="$(printf '{"class_code":"%s","display_name":"%s"}' "${CLASS_CODE}" "${DISPLAY_NAME}")"
  local code
  code="$(curl "${CURL_FLAGS[@]}" -c "${COOKIE_JAR}" -b "${COOKIE_JAR}" -o "${TMP_BODY}" -D "${TMP_HEADERS}" -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: ${csrf}" \
    -H "Referer: ${BASE_URL}/" \
    --data "${payload}" \
    "${BASE_URL}/join" || true)"
  if [[ "${code}" != "200" ]]; then
    mark_fail "session join check failed: /join returned HTTP ${code} for class_code=${CLASS_CODE}"
    return 1
  fi

  curl "${CURL_FLAGS[@]}" -c "${COOKIE_JAR}" -b "${COOKIE_JAR}" -o /dev/null "${BASE_URL}/student?kiosk=1"
  if kiosk_route_guard_check "/student?kiosk=1"; then
    return 0
  fi
  return 1
}

run_manual_checklist() {
  report_line ""
  report_line "## Manual unstable-network drill"
  report_line ""

  local steps=(
    "Open ${BASE_URL}/?kiosk=1 on a tablet (or tablet emulator) and confirm install prompt/add-to-home-screen option appears."
    "Join a class and open /material/<id>/upload in kiosk mode."
    "In browser devtools, set network to Offline, choose a small file, then submit."
    "Confirm UI message indicates queued upload pending and the page remains usable."
    "Restore network (Online), wait up to 90 seconds or click 'Retry queued uploads now'."
    "Confirm queued upload syncs, appears in 'Your uploads', and no data loss occurred."
    "Close and relaunch the installed kiosk app, then verify class/join flow still works."
  )

  if [[ "${INTERACTIVE}" == "1" && -t 0 ]]; then
    local idx=1
    for step in "${steps[@]}"; do
      echo
      echo "[kiosk-resilience] Manual step ${idx}: ${step}"
      read -r -p "Result [p=pass, f=fail, s=skip]: " answer
      case "${answer}" in
        p|P)
          mark_pass "manual step ${idx}: ${step}"
          ;;
        f|F)
          mark_fail "manual step ${idx}: ${step}"
          ;;
        *)
          mark_skip "manual step ${idx}: ${step}"
          ;;
      esac
      idx=$((idx + 1))
    done
  else
    local idx=1
    for step in "${steps[@]}"; do
      mark_skip "manual step ${idx} (pending): ${step}"
      idx=$((idx + 1))
    done
  fi
}

report_line "# Kiosk Resilience Validation Report"
report_line ""
report_line "- Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
report_line "- Base URL: ${BASE_URL}"
report_line "- Dry run: ${DRY_RUN}"
report_line "- Interactive: ${INTERACTIVE}"
report_line "- Class code check: ${CLASS_CODE:-<not provided>}"
report_line ""
report_line "## Automated checks"

http_check "health" "${BASE_URL}/healthz" "200" || true
http_check "kiosk manifest endpoint" "${BASE_URL}/student-shell.webmanifest" "200" || true
manifest_payload_check || true
http_check "upload sync service worker endpoint" "${BASE_URL}/student-upload-sync-sw.js" "200" || true
service_worker_header_check || true
kiosk_cookie_check || true
kiosk_route_guard_check "/?kiosk=1" || true
session_join_check || true

run_manual_checklist

report_line ""
report_line "## Summary"
report_line ""
report_line "- Pass: ${PASS_COUNT}"
report_line "- Fail: ${FAIL_COUNT}"
report_line "- Skip: ${SKIP_COUNT}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  report_line "- Verdict: FAIL"
  echo "[kiosk-resilience] FAIL (${FAIL_COUNT} failures). Report: ${REPORT_FILE}" >&2
  exit 1
fi

report_line "- Verdict: PASS"
echo "[kiosk-resilience] PASS. Report: ${REPORT_FILE}"
