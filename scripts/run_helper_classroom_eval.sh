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
  -h, --help                   Show this help
EOF
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
)

if [[ "${ENFORCE_THRESHOLD}" == "1" ]]; then
  cmd+=(--fail-on-min-pass-rate)
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
