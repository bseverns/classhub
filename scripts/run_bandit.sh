#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

TARGETS=(services/classhub services/homework_helper)
EXCLUDES="*/tests.py,*/tests_services.py,*/views/_legacy.py"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/run_bandit.sh [all [report.json]]
  bash scripts/run_bandit.sh report [report.json]
  bash scripts/run_bandit.sh gate

Modes:
  all     Generate a non-blocking JSON report, then run blocking high/high gate.
  report  Generate only non-blocking JSON report.
  gate    Run only blocking high-confidence/high-severity gate.
USAGE
}

mode="${1:-all}"
report_path="${2:-bandit-report.json}"

run_report() {
  if ! command -v bandit >/dev/null 2>&1; then
    echo "bandit is not installed. Install with: pip install bandit==1.8.3" >&2
    exit 1
  fi
  bandit -c bandit.yaml -r "${TARGETS[@]}" \
    -x "${EXCLUDES}" \
    --exit-zero -f json -o "${report_path}"
  echo "Bandit report written to ${report_path}"
}

run_gate() {
  if ! command -v bandit >/dev/null 2>&1; then
    echo "bandit is not installed. Install with: pip install bandit==1.8.3" >&2
    exit 1
  fi
  bandit -c bandit.yaml -r "${TARGETS[@]}" \
    -x "${EXCLUDES}" \
    -lll -iii
}

case "${mode}" in
  all)
    run_report
    run_gate
    ;;
  report)
    run_report
    ;;
  gate)
    run_gate
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown mode: ${mode}" >&2
    usage >&2
    exit 2
    ;;
esac
