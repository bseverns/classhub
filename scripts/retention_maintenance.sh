#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod|dev

RETENTION_SUBMISSION_DAYS="${RETENTION_SUBMISSION_DAYS:-90}"
RETENTION_EVENT_DAYS="${RETENTION_EVENT_DAYS:-180}"
RETENTION_EVENT_EXPORT_DIR="${RETENTION_EVENT_EXPORT_DIR:-/uploads/retention_exports}"
RETENTION_HELPER_EXPORT_DAYS="${RETENTION_HELPER_EXPORT_DAYS:-180}"
RETENTION_HELPER_EXPORT_DIR="${RETENTION_HELPER_EXPORT_DIR:-}"
RETENTION_SCAVENGE_MODE="${RETENTION_SCAVENGE_MODE:-report}" # report|delete|off
RETENTION_ALERT_WEBHOOK_URL="${RETENTION_ALERT_WEBHOOK_URL:-}"
RETENTION_ALERT_ON_SUCCESS="${RETENTION_ALERT_ON_SUCCESS:-0}"

CURRENT_STEP=""

usage() {
  cat <<'EOF'
Usage: bash scripts/retention_maintenance.sh [options]

Runs Class Hub data hygiene tasks:
1) prune old submissions
2) prune old student events (optional CSV export-before-delete)
3) scavenge orphan upload files (report or delete)

Options:
  --compose-mode <prod|dev>       Compose files (default: prod)
  --submission-days <N>           Retention window for submissions (default: 90; 0 skips)
  --event-days <N>                Retention window for student events (default: 180; 0 skips)
  --event-export-dir <path>       In-container export dir for student event CSV snapshots
                                  (default: /uploads/retention_exports; empty disables export)
  --helper-export-days <N>        Retention window for helper reset JSON exports
                                  (default: 180; 0 skips)
  --helper-export-dir <path>      In-container helper export dir override
                                  (default: HELPER_CLASS_RESET_ARCHIVE_DIR or /uploads/helper_reset_exports)
  --scavenge <report|delete|off>  Orphan upload cleanup mode (default: report)
  --alert-webhook-url <url>       Optional webhook for failure/success alerts
  --alert-on-success              Send success alert in addition to failures
  -h, --help                      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --submission-days)
      RETENTION_SUBMISSION_DAYS="$2"
      shift 2
      ;;
    --event-days)
      RETENTION_EVENT_DAYS="$2"
      shift 2
      ;;
    --event-export-dir)
      RETENTION_EVENT_EXPORT_DIR="$2"
      shift 2
      ;;
    --helper-export-days)
      RETENTION_HELPER_EXPORT_DAYS="$2"
      shift 2
      ;;
    --helper-export-dir)
      RETENTION_HELPER_EXPORT_DIR="$2"
      shift 2
      ;;
    --scavenge)
      RETENTION_SCAVENGE_MODE="$2"
      shift 2
      ;;
    --alert-webhook-url)
      RETENTION_ALERT_WEBHOOK_URL="$2"
      shift 2
      ;;
    --alert-on-success)
      RETENTION_ALERT_ON_SUCCESS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[retention] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ROOT_DIR}/compose/.env" ]]; then
  echo "[retention] missing compose/.env (copy from compose/.env.example first)" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[retention] docker is required" >&2
  exit 1
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[retention] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

if ! [[ "${RETENTION_SUBMISSION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "[retention] --submission-days must be a non-negative integer" >&2
  exit 1
fi
if ! [[ "${RETENTION_EVENT_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "[retention] --event-days must be a non-negative integer" >&2
  exit 1
fi
if ! [[ "${RETENTION_HELPER_EXPORT_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "[retention] --helper-export-days must be a non-negative integer" >&2
  exit 1
fi
case "${RETENTION_SCAVENGE_MODE}" in
  report|delete|off) ;;
  *)
    echo "[retention] --scavenge must be report, delete, or off" >&2
    exit 1
    ;;
esac

notify_webhook() {
  local status="$1"
  local message="$2"
  if [[ -z "${RETENTION_ALERT_WEBHOOK_URL}" ]]; then
    return 0
  fi
  local escaped="${message//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  local payload
  payload="{\"status\":\"${status}\",\"text\":\"${escaped}\"}"
  curl -fsS -X POST \
    -H "Content-Type: application/json" \
    -d "${payload}" \
    "${RETENTION_ALERT_WEBHOOK_URL}" >/dev/null || true
}

on_error() {
  local code="$1"
  local msg="[retention] FAIL at step '${CURRENT_STEP:-unknown}' (exit ${code})"
  echo "${msg}" >&2
  notify_webhook "failure" "${msg}"
  exit "${code}"
}

trap 'on_error $?' ERR

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

if (( RETENTION_SUBMISSION_DAYS > 0 )); then
  CURRENT_STEP="prune_submissions"
  echo "[retention] pruning submissions older than ${RETENTION_SUBMISSION_DAYS} days"
  run_compose exec -T classhub_web python manage.py prune_submissions --older-than-days "${RETENTION_SUBMISSION_DAYS}"
else
  echo "[retention] skipping prune_submissions (submission-days=0)"
fi

if (( RETENTION_EVENT_DAYS > 0 )); then
  CURRENT_STEP="prune_student_events"
  echo "[retention] pruning student events older than ${RETENTION_EVENT_DAYS} days"
  event_cmd=(
    run_compose exec -T classhub_web
    python manage.py prune_student_events
    --older-than-days "${RETENTION_EVENT_DAYS}"
  )
  if [[ -n "${RETENTION_EVENT_EXPORT_DIR}" ]]; then
    export_path="${RETENTION_EVENT_EXPORT_DIR%/}/student_events_before_prune_${timestamp}.csv"
    echo "[retention] exporting matching student events to ${export_path} before delete"
    run_compose exec -T classhub_web sh -lc "mkdir -p '${RETENTION_EVENT_EXPORT_DIR}'"
    event_cmd+=(--export-csv "${export_path}")
  fi
  "${event_cmd[@]}"
else
  echo "[retention] skipping prune_student_events (event-days=0)"
fi

if (( RETENTION_HELPER_EXPORT_DAYS > 0 )); then
  CURRENT_STEP="prune_helper_reset_exports"
  echo "[retention] pruning helper reset exports older than ${RETENTION_HELPER_EXPORT_DAYS} days"
  run_compose exec -T \
    -e RETENTION_HELPER_EXPORT_DAYS="${RETENTION_HELPER_EXPORT_DAYS}" \
    -e RETENTION_HELPER_EXPORT_DIR="${RETENTION_HELPER_EXPORT_DIR}" \
    classhub_web sh -lc '
      set -eu
      days="${RETENTION_HELPER_EXPORT_DAYS:-180}"
      dir="${RETENTION_HELPER_EXPORT_DIR:-${HELPER_CLASS_RESET_ARCHIVE_DIR:-/uploads/helper_reset_exports}}"
      if [ ! -d "${dir}" ]; then
        echo "[retention] helper export dir not found: ${dir} (skip)"
        exit 0
      fi
      if [ "${days}" -le 0 ]; then
        echo "[retention] skipping helper export prune (helper-export-days=0)"
        exit 0
      fi
      cutoff=$((days - 1))
      if [ "${cutoff}" -lt 0 ]; then
        cutoff=0
      fi
      count="$(find "${dir}" -type f -name "class_*_helper_reset_*.json" -mtime +"${cutoff}" | wc -l | tr -d "[:space:]")"
      if [ "${count}" = "0" ]; then
        echo "[retention] no helper reset exports older than ${days} days in ${dir}"
        exit 0
      fi
      echo "[retention] deleting ${count} helper reset export(s) older than ${days} days from ${dir}"
      find "${dir}" -type f -name "class_*_helper_reset_*.json" -mtime +"${cutoff}" -delete
    '
else
  echo "[retention] skipping helper reset export prune (helper-export-days=0)"
fi

case "${RETENTION_SCAVENGE_MODE}" in
  off)
    echo "[retention] skipping orphan upload scavenger (--scavenge off)"
    ;;
  report)
    CURRENT_STEP="scavenge_orphan_uploads_report"
    echo "[retention] reporting orphan upload files"
    run_compose exec -T classhub_web python manage.py scavenge_orphan_uploads
    ;;
  delete)
    CURRENT_STEP="scavenge_orphan_uploads_delete"
    echo "[retention] deleting orphan upload files"
    run_compose exec -T classhub_web python manage.py scavenge_orphan_uploads --delete
    ;;
esac

success_msg="[retention] complete (submission-days=${RETENTION_SUBMISSION_DAYS}, event-days=${RETENTION_EVENT_DAYS}, helper-export-days=${RETENTION_HELPER_EXPORT_DAYS}, scavenge=${RETENTION_SCAVENGE_MODE})"
echo "${success_msg}"
if [[ "${RETENTION_ALERT_ON_SUCCESS}" == "1" ]]; then
  notify_webhook "success" "${success_msg}"
fi
