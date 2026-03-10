#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"

COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod|dev
WINDOW_DAYS="${WINDOW_DAYS:-7}"
OUT_DIR="${OUT_DIR:-/tmp/classhub_telemetry_stabilization_$(date +%Y%m%d_%H%M%S)}"
RUN_SMOKE=1
RUN_ROLLBACK_DRILL=0
ALLOW_PARITY_DRIFT=0
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-30}"
SMOKE_BASE_URL="${SMOKE_BASE_URL:-}"
SMOKE_INSECURE_TLS=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/telemetry_stabilization_evidence.sh [options]

Captures Slice 7 telemetry stabilization evidence artifacts:
- parity snapshot output,
- smoke validation output,
- optional rollback drill output (switch read-mode -> core, smoke, restore).

Options:
  --compose-mode <prod|dev>     Compose mode (default: prod)
  --window-days <n>             Parity window in days (default: 7)
  --out-dir <path>              Evidence output directory (default: /tmp/classhub_telemetry_stabilization_<ts>)
  --skip-smoke                  Skip smoke validation step
  --allow-parity-drift          Pass --allow-drift to check_telemetry_parity
  --perform-rollback-drill      Run opt-in rollback drill (modifies compose/.env, then restores it)
  --smoke-timeout-seconds <n>   Timeout passed to smoke_check.sh (default: 30)
  --base-url <url>              Override smoke base URL
  --insecure-tls                Use -k for HTTPS smoke checks
  -h, --help                    Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --window-days)
      WINDOW_DAYS="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --skip-smoke)
      RUN_SMOKE=0
      shift
      ;;
    --allow-parity-drift)
      ALLOW_PARITY_DRIFT=1
      shift
      ;;
    --perform-rollback-drill)
      RUN_ROLLBACK_DRILL=1
      shift
      ;;
    --smoke-timeout-seconds)
      SMOKE_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --base-url)
      SMOKE_BASE_URL="$2"
      shift 2
      ;;
    --insecure-tls)
      SMOKE_INSECURE_TLS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[telemetry-evidence] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[telemetry-evidence] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 2
fi

if [[ ! "${WINDOW_DAYS}" =~ ^[0-9]+$ ]] || (( WINDOW_DAYS <= 0 )); then
  echo "[telemetry-evidence] --window-days must be a positive integer" >&2
  exit 2
fi
if [[ ! "${SMOKE_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] || (( SMOKE_TIMEOUT_SECONDS <= 0 )); then
  echo "[telemetry-evidence] --smoke-timeout-seconds must be a positive integer" >&2
  exit 2
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[telemetry-evidence] missing compose/.env" >&2
  exit 2
fi

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

DRILL_ENV_RESTORE_NEEDED=0
DRILL_ENV_BACKUP_PATH=""
rollback_drill_cleanup() {
  if (( DRILL_ENV_RESTORE_NEEDED != 1 )); then
    return
  fi
  if [[ -n "${DRILL_ENV_BACKUP_PATH}" && -f "${DRILL_ENV_BACKUP_PATH}" ]]; then
    cp "${DRILL_ENV_BACKUP_PATH}" "${ENV_FILE}"
    run_compose up -d classhub_web caddy >/dev/null 2>&1 || true
  fi
}
trap rollback_drill_cleanup EXIT

env_file_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

replace_env_key() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    printf '\n%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
  rm -f "${ENV_FILE}.bak"
}

mkdir -p "${OUT_DIR}"
SUMMARY_FILE="${OUT_DIR}/summary.md"
META_FILE="${OUT_DIR}/metadata.env"

STATUS_PARITY="pending"
STATUS_SMOKE="skipped"
STATUS_ROLLBACK="skipped"
RUNTIME_SMOKE_CLASS_CODE=""
RUNTIME_SMOKE_TEACHER_USERNAME=""
RUNTIME_SMOKE_TEACHER_PASSWORD=""

prepare_runtime_smoke_inputs() {
  local class_name teacher_username teacher_password teacher_email course_slug class_code_raw class_code

  class_name="$(env_file_value SMOKE_CLASS_NAME)"
  class_name="${class_name:-Smoke Validation Class}"
  teacher_username="$(env_file_value SMOKE_TEACHER_USERNAME)"
  teacher_username="${teacher_username:-smoke_teacher}"
  teacher_password="$(env_file_value SMOKE_TEACHER_PASSWORD)"
  teacher_password="${teacher_password:-Sm0keTeacherPass123!}"
  teacher_email="$(env_file_value SMOKE_TEACHER_EMAIL)"
  teacher_email="${teacher_email:-${teacher_username}@example.org}"
  course_slug="$(env_file_value SMOKE_COURSE_SLUG)"
  course_slug="${course_slug:-piper_scratch_12_session}"

  run_compose exec -T classhub_web \
    python manage.py create_teacher \
    --username "${teacher_username}" \
    --email "${teacher_email}" \
    --password "${teacher_password}" \
    --active \
    --update \
    >/dev/null

  class_code_raw="$(
    set +e
    run_compose exec -T \
      -e SMOKE_CLASS_NAME="${class_name}" \
      classhub_web \
      python manage.py shell -c \
      "import os; from hub.models import Class; cls = Class.objects.get(name=os.environ['SMOKE_CLASS_NAME']); cls.enrollment_mode = Class.ENROLLMENT_OPEN; cls.save(update_fields=['enrollment_mode']); print(cls.join_code)" \
      2>/dev/null
    echo ".__exit:$?"
  )"
  if [[ "${class_code_raw}" == *".__exit:0" ]]; then
    class_code="${class_code_raw%.__exit:0}"
  else
    class_code=""
  fi
  class_code="$(echo "${class_code}" | tr -d '\r' | tail -n1)"

  if [[ -z "${class_code}" ]]; then
    run_compose exec -T classhub_web \
      python manage.py import_coursepack \
      --course-slug "${course_slug}" \
      --class-name "${class_name}" \
      --create-class \
      --replace \
      >/dev/null
    class_code="$(
      run_compose exec -T \
        -e SMOKE_CLASS_NAME="${class_name}" \
        classhub_web \
        python manage.py shell -c \
        "import os; from hub.models import Class; cls = Class.objects.get(name=os.environ['SMOKE_CLASS_NAME']); cls.enrollment_mode = Class.ENROLLMENT_OPEN; cls.save(update_fields=['enrollment_mode']); print(cls.join_code)" \
        | tr -d '\r' | tail -n1
    )"
  fi

  if [[ -z "${class_code}" ]]; then
    echo "[telemetry-evidence] unable to resolve runtime smoke class code for '${class_name}'" >&2
    exit 1
  fi

  RUNTIME_SMOKE_CLASS_CODE="${class_code}"
  RUNTIME_SMOKE_TEACHER_USERNAME="${teacher_username}"
  RUNTIME_SMOKE_TEACHER_PASSWORD="${teacher_password}"
}

run_strict_smoke_command() {
  local smoke_cmd=(
    bash "${ROOT_DIR}/scripts/smoke_check.sh"
    --strict
    --timeout-seconds "${SMOKE_TIMEOUT_SECONDS}"
  )
  if [[ -n "${SMOKE_BASE_URL}" ]]; then
    smoke_cmd+=(--base-url "${SMOKE_BASE_URL}")
  fi
  if (( SMOKE_INSECURE_TLS == 1 )); then
    smoke_cmd+=(--insecure-tls)
  fi
  env \
    "SMOKE_CLASS_CODE=${RUNTIME_SMOKE_CLASS_CODE}" \
    "SMOKE_TEACHER_USERNAME=${RUNTIME_SMOKE_TEACHER_USERNAME}" \
    "SMOKE_TEACHER_PASSWORD=${RUNTIME_SMOKE_TEACHER_PASSWORD}" \
    "${smoke_cmd[@]}"
}

{
  echo "captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "compose_mode=${COMPOSE_MODE}"
  echo "window_days=${WINDOW_DAYS}"
  echo "smoke_timeout_seconds=${SMOKE_TIMEOUT_SECONDS}"
  echo "telemetry_database_url_set=$([[ -n "$(env_file_value CLASSHUB_TELEMETRY_DATABASE_URL)" ]] && echo 1 || echo 0)"
  echo "telemetry_write_mode=$(env_file_value CLASSHUB_TELEMETRY_WRITE_MODE)"
  echo "telemetry_read_mode=$(env_file_value CLASSHUB_TELEMETRY_READ_MODE)"
} > "${META_FILE}"

echo "[telemetry-evidence] output dir: ${OUT_DIR}"
echo "[telemetry-evidence] metadata: ${META_FILE}"

if (( RUN_SMOKE == 1 || RUN_ROLLBACK_DRILL == 1 )); then
  prepare_runtime_smoke_inputs
fi

PARITY_LOG="${OUT_DIR}/parity_check.log"
set +e
if (( ALLOW_PARITY_DRIFT == 1 )); then
  run_compose exec -T classhub_web \
    python manage.py check_telemetry_parity --window-days "${WINDOW_DAYS}" --allow-drift \
    > "${PARITY_LOG}" 2>&1
else
  run_compose exec -T classhub_web \
    python manage.py check_telemetry_parity --window-days "${WINDOW_DAYS}" \
    > "${PARITY_LOG}" 2>&1
fi
PARITY_EXIT=$?
set -e
if (( PARITY_EXIT == 0 )); then
  STATUS_PARITY="pass"
else
  STATUS_PARITY="fail(${PARITY_EXIT})"
fi
echo "[telemetry-evidence] parity status: ${STATUS_PARITY} (${PARITY_LOG})"

if (( RUN_SMOKE == 1 )); then
  SMOKE_LOG="${OUT_DIR}/smoke_strict.log"
  set +e
  run_strict_smoke_command > "${SMOKE_LOG}" 2>&1
  SMOKE_EXIT=$?
  set -e
  if (( SMOKE_EXIT == 0 )); then
    STATUS_SMOKE="pass"
  else
    STATUS_SMOKE="fail(${SMOKE_EXIT})"
  fi
  echo "[telemetry-evidence] smoke status: ${STATUS_SMOKE} (${SMOKE_LOG})"
fi

if (( RUN_ROLLBACK_DRILL == 1 )); then
  ROLLBACK_LOG="${OUT_DIR}/rollback_drill.log"
  ENV_BACKUP="${OUT_DIR}/compose.env.before_rollback"
  DRILL_ENV_BACKUP_PATH="${ENV_BACKUP}"
  cp "${ENV_FILE}" "${ENV_BACKUP}"
  DRILL_ENV_RESTORE_NEEDED=1
  ORIGINAL_READ_MODE="$(env_file_value CLASSHUB_TELEMETRY_READ_MODE)"
  {
    echo "rollback_drill_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "original_read_mode=${ORIGINAL_READ_MODE:-<unset>}"
    echo "step=set_read_mode_core"
    echo "runtime_smoke_teacher=${RUNTIME_SMOKE_TEACHER_USERNAME}"
  } > "${ROLLBACK_LOG}"

  set +e
  replace_env_key "CLASSHUB_TELEMETRY_READ_MODE" "core"
  run_compose up -d classhub_web caddy >> "${ROLLBACK_LOG}" 2>&1
  run_strict_smoke_command >> "${ROLLBACK_LOG}" 2>&1
  DRILL_EXIT=$?

  cp "${ENV_BACKUP}" "${ENV_FILE}"
  run_compose up -d classhub_web caddy >> "${ROLLBACK_LOG}" 2>&1
  DRILL_ENV_RESTORE_NEEDED=0
  set -e

  if (( DRILL_EXIT == 0 )); then
    STATUS_ROLLBACK="pass"
  else
    STATUS_ROLLBACK="fail(${DRILL_EXIT})"
  fi
  echo "[telemetry-evidence] rollback drill status: ${STATUS_ROLLBACK} (${ROLLBACK_LOG})"
fi

{
  echo "# Telemetry Stabilization Evidence"
  echo
  echo "- Captured at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Output directory: ${OUT_DIR}"
  echo "- Compose mode: ${COMPOSE_MODE}"
  echo "- Window days: ${WINDOW_DAYS}"
  echo
  echo "## Status"
  echo
  echo "- Parity: ${STATUS_PARITY}"
  echo "- Smoke: ${STATUS_SMOKE}"
  echo "- Rollback drill: ${STATUS_ROLLBACK}"
  echo
  echo "## Artifacts"
  echo
  echo "- Metadata: \`${META_FILE}\`"
  echo "- Parity log: \`${PARITY_LOG}\`"
  if (( RUN_SMOKE == 1 )); then
    echo "- Smoke log: \`${SMOKE_LOG}\`"
  fi
  if (( RUN_ROLLBACK_DRILL == 1 )); then
    echo "- Rollback log: \`${ROLLBACK_LOG}\`"
    echo "- Pre-rollback env backup: \`${ENV_BACKUP}\`"
  fi
  echo
  echo "## Notes"
  echo
  echo "- Slice 7 remains open until this evidence is captured across at least one full release cycle."
  echo "- If parity fails, inspect the delta sections in \`${PARITY_LOG}\` and keep READ_MODE at \`core\`."
} > "${SUMMARY_FILE}"

echo "[telemetry-evidence] summary: ${SUMMARY_FILE}"

if [[ "${STATUS_PARITY}" == pass && "${STATUS_SMOKE}" != fail* && "${STATUS_ROLLBACK}" != fail* ]]; then
  exit 0
fi
exit 1
