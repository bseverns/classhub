#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod|dev
JOURNAL_LINES="${JOURNAL_LINES:-120}"
OUT_PATH=""
SKIP_DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: bash scripts/retention_health_snapshot.sh [options]

Collect a retention health snapshot with:
1) systemd timer state (when available)
2) recent retention service logs (when available)
3) retention maintenance dry-run output

Options:
  --compose-mode <prod|dev>  Compose profile for retention dry-run (default: prod)
  --journal-lines <N>        Number of journal lines to include (default: 120)
  --out <path>               Optional output log file path
  --skip-dry-run             Skip retention_maintenance dry-run execution
  -h, --help                 Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --journal-lines)
      JOURNAL_LINES="$2"
      shift 2
      ;;
    --out)
      OUT_PATH="$2"
      shift 2
      ;;
    --skip-dry-run)
      SKIP_DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[retention-health] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${COMPOSE_MODE}" != "prod" && "${COMPOSE_MODE}" != "dev" ]]; then
  echo "[retention-health] --compose-mode must be prod or dev" >&2
  exit 1
fi
if ! [[ "${JOURNAL_LINES}" =~ ^[0-9]+$ ]]; then
  echo "[retention-health] --journal-lines must be a non-negative integer" >&2
  exit 1
fi

if [[ -n "${OUT_PATH}" ]]; then
  mkdir -p "$(dirname "${OUT_PATH}")"
  exec > >(tee "${OUT_PATH}") 2>&1
fi

section() {
  echo
  echo "=== $1 ==="
}

run_capture() {
  local label="$1"
  shift
  section "${label}"
  echo "+ $*"
  set +e
  "$@"
  local rc=$?
  set -e
  if [[ ${rc} -ne 0 ]]; then
    echo "[retention-health] command exited ${rc}"
  fi
}

echo "[retention-health] timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[retention-health] host=$(hostname 2>/dev/null || echo unknown)"
echo "[retention-health] compose_mode=${COMPOSE_MODE}"
echo "[retention-health] repo_root=${ROOT_DIR}"

if command -v systemctl >/dev/null 2>&1; then
  run_capture "Timer enabled state" systemctl is-enabled classhub-retention.timer
  run_capture "Timer active state" systemctl show classhub-retention.timer \
    -p ActiveState -p SubState -p UnitFileState -p NextElapseUSec -p LastTriggerUSec
  run_capture "Timer schedule" systemctl list-timers --all classhub-retention.timer --no-pager
  if command -v journalctl >/dev/null 2>&1; then
    run_capture "Recent retention service logs" journalctl -u classhub-retention.service -n "${JOURNAL_LINES}" --no-pager
  fi
else
  section "Timer checks"
  echo "[retention-health] systemctl not available on this host; skipping timer/log checks"
fi

if [[ "${SKIP_DRY_RUN}" == "1" ]]; then
  section "Retention dry-run"
  echo "[retention-health] skipped by --skip-dry-run"
else
  run_capture "Retention maintenance dry-run" \
    bash "${ROOT_DIR}/scripts/retention_maintenance.sh" --compose-mode "${COMPOSE_MODE}" --dry-run
fi

echo
echo "[retention-health] snapshot complete"
