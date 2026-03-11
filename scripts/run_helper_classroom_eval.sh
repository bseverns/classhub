#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

URL="http://localhost/helper/chat"
PROMPTS="services/homework_helper/tutor/fixtures/eval_prompts_classroom_realistic.jsonl"
OUT_DIR="/tmp/classhub_helper_eval_$(date -u +%Y%m%dT%H%M%SZ)"
SLEEP_SECONDS="3.2"
TIMEOUT_SECONDS="30"
LIMIT="0"
MIN_PASS_RATE="0.80"
ENFORCE_THRESHOLD="0"
STUDENT_AUTH="0"
CLASS_CODE="${SMOKE_CLASS_CODE:-}"
DISPLAY_NAME="eval_student_$(date +%s)"
COOKIE_HEADER=""
CSRF_TOKEN=""
SCOPE_TOKEN=""
BASE_URL_OVERRIDE=""
DEFAULT_CONTEXT="eval"
DEFAULT_TOPICS="scratch"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_helper_classroom_eval.sh [options]

Runs classroom-realistic helper eval prompts with scoring and writes:
  - results.jsonl
  - summary.json
  - summary.md

Options:
  --url <url>                  Helper endpoint (default: http://localhost/helper/chat)
  --prompts <path>             Prompt JSONL file
  --out-dir <dir>              Output directory
  --sleep <seconds>            Delay between prompts (default: 3.2)
  --timeout <seconds>          HTTP timeout (default: 30)
  --limit <n>                  Prompt limit (0 = all)
  --min-pass-rate <0..1>       Reporting threshold (default: 0.80)
  --enforce-threshold          Exit non-zero when pass rate < min-pass-rate
  --student-auth               Bootstrap a student session (join + cookie + csrf + scope token)
  --class-code <code>          Class code for --student-auth (default: SMOKE_CLASS_CODE or compose/.env)
  --display-name <name>        Display name used for --student-auth
  --base-url <url>             Base ClassHub URL (default: derived from --url)
  -h, --help                   Show this help
EOF
}

infer_base_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit
raw = sys.argv[1]
parts = urlsplit(raw)
if not parts.scheme or not parts.netloc:
    print(raw.rsplit("/helper/chat", 1)[0])
    raise SystemExit(0)
print(urlunsplit((parts.scheme, parts.netloc, "", "", "")))
PY
}

load_class_code_from_env_file() {
  if [[ -f "compose/.env" ]]; then
    awk -F= '
      $1=="SMOKE_CLASS_CODE" {
        value=$2
        sub(/^[ \t]+/, "", value)
        sub(/[ \t]+$/, "", value)
        print value
        exit
      }
    ' compose/.env
  fi
}

build_cookie_header_from_jar() {
  python3 - "$1" <<'PY'
import sys
from pathlib import Path

jar_path = Path(sys.argv[1])
pairs = []
for raw_line in jar_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line:
        continue
    if line.startswith("#HttpOnly_"):
        line = line.replace("#HttpOnly_", "", 1)
    elif line.startswith("#"):
        continue
    parts = line.split("\t")
    if len(parts) < 7:
        continue
    name = parts[5].strip()
    value = parts[6].strip()
    if not name:
        continue
    pairs.append(f"{name}={value}")

print("; ".join(pairs))
PY
}

extract_csrf_from_jar() {
  python3 - "$1" <<'PY'
import sys
from pathlib import Path

jar_path = Path(sys.argv[1])
token = ""
for raw_line in jar_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line:
        continue
    if line.startswith("#HttpOnly_"):
        line = line.replace("#HttpOnly_", "", 1)
    elif line.startswith("#"):
        continue
    parts = line.split("\t")
    if len(parts) < 7:
        continue
    if parts[5].strip() == "csrftoken":
        token = parts[6].strip()

print(token)
PY
}

bootstrap_student_auth() {
  local base_url="$1"
  local cookie_jar="$2"
  local student_html="$3"

  if [[ -z "${CLASS_CODE}" ]]; then
    CLASS_CODE="$(load_class_code_from_env_file || true)"
  fi
  if [[ -z "${CLASS_CODE}" ]]; then
    echo "[helper-classroom-eval] missing class code for --student-auth; set --class-code or SMOKE_CLASS_CODE" >&2
    exit 1
  fi

  curl -sS -c "${cookie_jar}" -b "${cookie_jar}" "${base_url}/" >/dev/null
  CSRF_TOKEN="$(extract_csrf_from_jar "${cookie_jar}")"
  if [[ -z "${CSRF_TOKEN}" ]]; then
    echo "[helper-classroom-eval] unable to resolve csrftoken from ${base_url}/" >&2
    exit 1
  fi

  local join_payload
  join_payload="$(python3 - "${CLASS_CODE}" "${DISPLAY_NAME}" <<'PY'
import json
import sys
print(json.dumps({"class_code": sys.argv[1], "display_name": sys.argv[2]}))
PY
)"
  local join_body
  join_body="$(mktemp)"
  local join_code
  join_code="$(curl -sS -o "${join_body}" -w "%{http_code}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: ${CSRF_TOKEN}" \
    -H "Referer: ${base_url}/" \
    --data "${join_payload}" \
    "${base_url}/join")"
  if [[ "${join_code}" != "200" ]]; then
    echo "[helper-classroom-eval] /join failed (${join_code}): $(cat "${join_body}")" >&2
    exit 1
  fi

  CSRF_TOKEN="$(extract_csrf_from_jar "${cookie_jar}")"
  if [[ -z "${CSRF_TOKEN}" ]]; then
    echo "[helper-classroom-eval] unable to refresh csrftoken after /join" >&2
    exit 1
  fi

  local student_code
  student_code="$(curl -sS -o "${student_html}" -w "%{http_code}" \
    -c "${cookie_jar}" -b "${cookie_jar}" \
    "${base_url}/student")"
  if [[ "${student_code}" != "200" ]]; then
    echo "[helper-classroom-eval] /student failed (${student_code})" >&2
    exit 1
  fi

  SCOPE_TOKEN="$(grep -oE 'data-helper-scope-token="[^"]*"' "${student_html}" | head -n1 | sed -E 's/^data-helper-scope-token="(.*)"$/\1/' || true)"
  COOKIE_HEADER="$(build_cookie_header_from_jar "${cookie_jar}")"

  if [[ -z "${COOKIE_HEADER}" ]]; then
    echo "[helper-classroom-eval] failed to build Cookie header from session jar" >&2
    exit 1
  fi

  echo "[helper-classroom-eval] student auth bootstrapped (class_code=${CLASS_CODE}, display_name=${DISPLAY_NAME})"
  if [[ -n "${SCOPE_TOKEN}" ]]; then
    echo "[helper-classroom-eval] scope token captured from /student"
  else
    echo "[helper-classroom-eval] scope token not found on /student; falling back to context/topics payload"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      URL="$2"
      shift 2
      ;;
    --prompts)
      PROMPTS="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --sleep)
      SLEEP_SECONDS="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --min-pass-rate)
      MIN_PASS_RATE="$2"
      shift 2
      ;;
    --enforce-threshold)
      ENFORCE_THRESHOLD="1"
      shift
      ;;
    --student-auth)
      STUDENT_AUTH="1"
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
    --base-url)
      BASE_URL_OVERRIDE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

mkdir -p "${OUT_DIR}"
RAW_OUT="${OUT_DIR}/results.jsonl"
SUMMARY_JSON="${OUT_DIR}/summary.json"
SUMMARY_MD="${OUT_DIR}/summary.md"
COOKIE_JAR="${OUT_DIR}/session.cookies.txt"
STUDENT_HTML="${OUT_DIR}/student.html"

if [[ -n "${BASE_URL_OVERRIDE}" ]]; then
  BASE_URL="${BASE_URL_OVERRIDE}"
else
  BASE_URL="$(infer_base_url "${URL}")"
fi

if [[ "${STUDENT_AUTH}" == "1" ]]; then
  bootstrap_student_auth "${BASE_URL}" "${COOKIE_JAR}" "${STUDENT_HTML}"
fi

cmd=(
  python3 scripts/eval_helper.py
  --url "${URL}"
  --prompts "${PROMPTS}"
  --out "${RAW_OUT}"
  --sleep "${SLEEP_SECONDS}"
  --timeout "${TIMEOUT_SECONDS}"
  --limit "${LIMIT}"
  --score
  --summary-json "${SUMMARY_JSON}"
  --summary-md "${SUMMARY_MD}"
  --min-pass-rate "${MIN_PASS_RATE}"
  --default-context "${DEFAULT_CONTEXT}"
  --default-topics "${DEFAULT_TOPICS}"
)

if [[ "${ENFORCE_THRESHOLD}" == "1" ]]; then
  cmd+=(--fail-on-min-pass-rate)
fi
if [[ -n "${COOKIE_HEADER}" ]]; then
  cmd+=(--cookie-header "${COOKIE_HEADER}")
fi
if [[ -n "${CSRF_TOKEN}" ]]; then
  cmd+=(--csrf-token "${CSRF_TOKEN}")
  cmd+=(--referer "${BASE_URL}/")
fi
if [[ -n "${SCOPE_TOKEN}" ]]; then
  cmd+=(--scope-token "${SCOPE_TOKEN}")
fi

echo "[helper-classroom-eval] running prompt pack: ${PROMPTS}"
"${cmd[@]}"

echo "[helper-classroom-eval] results: ${RAW_OUT}"
echo "[helper-classroom-eval] summary json: ${SUMMARY_JSON}"
echo "[helper-classroom-eval] summary md: ${SUMMARY_MD}"
if [[ "${ENFORCE_THRESHOLD}" == "1" ]]; then
  echo "[helper-classroom-eval] threshold enforced: min pass rate ${MIN_PASS_RATE}"
else
  echo "[helper-classroom-eval] threshold report only: min pass rate ${MIN_PASS_RATE}"
fi
