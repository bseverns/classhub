#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose/docker-compose.yml"
COMPOSE_OVERRIDE="${ROOT_DIR}/compose/docker-compose.override.yml"
ENV_FILE="${ROOT_DIR}/compose/.env"

BACKUP_POSTGRES_SCRIPT="${ROOT_DIR}/scripts/backup_postgres.sh"
BACKUP_TELEMETRY_POSTGRES_SCRIPT="${ROOT_DIR}/scripts/backup_telemetry_postgres.sh"
BACKUP_UPLOADS_SCRIPT="${ROOT_DIR}/scripts/backup_uploads.sh"
BACKUP_MINIO_SCRIPT="${ROOT_DIR}/scripts/backup_minio.sh"

COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod or dev
BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups}"
TEMP_ROOT="${TEMP_ROOT:-/tmp/classhub_restore_rehearsal}"
SKIP_BACKUP=0
KEEP_TEMP=0
UP_TIMEOUT_SECONDS="${UP_TIMEOUT_SECONDS:-180}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
INCLUDE_TELEMETRY_DB="${INCLUDE_TELEMETRY_DB:-auto}" # auto|0|1
TELEMETRY_REHEARSAL_PARITY_WINDOW_DAYS="${TELEMETRY_REHEARSAL_PARITY_WINDOW_DAYS:-3650}"

POSTGRES_BACKUP_PATH="${POSTGRES_BACKUP_PATH:-}"
TELEMETRY_POSTGRES_BACKUP_PATH="${TELEMETRY_POSTGRES_BACKUP_PATH:-}"
UPLOADS_BACKUP_PATH="${UPLOADS_BACKUP_PATH:-}"
MINIO_BACKUP_PATH="${MINIO_BACKUP_PATH:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/backup_restore_rehearsal.sh [options]

Creates fresh backups and immediately runs a non-destructive restore rehearsal:
1) backup Postgres + uploads + MinIO
2) restore Postgres backup into a temporary database
3) extract uploads/MinIO backups into a temporary directory
4) run ClassHub/Helper migrate+check against the temporary restored DB

Options:
  --compose-mode <prod|dev>       Compose files (default: prod)
  --backup-root <dir>             Backup root (default: ./backups)
  --temp-root <dir>               Rehearsal extract root (default: /tmp/classhub_restore_rehearsal)
  --skip-backup                   Reuse existing backups (requires explicit files or latest files under backup-root)
  --postgres-backup <file>        Path to Postgres .sql backup (used with --skip-backup)
  --telemetry-postgres-backup <file>
                                  Path to telemetry Postgres .sql backup (used with --skip-backup)
  --uploads-backup <file>         Path to uploads .tgz backup (used with --skip-backup)
  --minio-backup <file>           Path to MinIO .tgz backup (used with --skip-backup)
  --include-telemetry-db          Backup + restore telemetry DB when CLASSHUB_TELEMETRY_DATABASE_URL is configured
  --skip-telemetry-db             Force rehearsal to ignore telemetry DB even when configured
  --keep-temp                     Keep extracted rehearsal temp directory for inspection
  --up-timeout-seconds <seconds>  Wait timeout for Postgres health (default: 180)
  -h, --help                      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --backup-root)
      BACKUP_ROOT="$2"
      shift 2
      ;;
    --temp-root)
      TEMP_ROOT="$2"
      shift 2
      ;;
    --skip-backup)
      SKIP_BACKUP=1
      shift
      ;;
    --postgres-backup)
      POSTGRES_BACKUP_PATH="$2"
      shift 2
      ;;
    --telemetry-postgres-backup)
      TELEMETRY_POSTGRES_BACKUP_PATH="$2"
      shift 2
      ;;
    --uploads-backup)
      UPLOADS_BACKUP_PATH="$2"
      shift 2
      ;;
    --minio-backup)
      MINIO_BACKUP_PATH="$2"
      shift 2
      ;;
    --keep-temp)
      KEEP_TEMP=1
      shift
      ;;
    --include-telemetry-db)
      INCLUDE_TELEMETRY_DB=1
      shift
      ;;
    --skip-telemetry-db)
      INCLUDE_TELEMETRY_DB=0
      shift
      ;;
    --up-timeout-seconds)
      UP_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[rehearsal] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "[rehearsal] docker is required" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[rehearsal] missing compose/.env (copy from compose/.env.example first)" >&2
  exit 1
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_FILE}")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}")
else
  echo "[rehearsal] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi
if [[ "${INCLUDE_TELEMETRY_DB}" != "auto" && "${INCLUDE_TELEMETRY_DB}" != "0" && "${INCLUDE_TELEMETRY_DB}" != "1" ]]; then
  echo "[rehearsal] invalid telemetry mode '${INCLUDE_TELEMETRY_DB}' (expected auto|0|1)" >&2
  exit 1
fi
if [[ ! "${TELEMETRY_REHEARSAL_PARITY_WINDOW_DAYS}" =~ ^[0-9]+$ ]] || (( TELEMETRY_REHEARSAL_PARITY_WINDOW_DAYS <= 0 )); then
  echo "[rehearsal] --telemetry parity window must be a positive integer" >&2
  exit 1
fi

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

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

latest_matching_file() {
  local pattern="$1"
  # shellcheck disable=SC2086
  ls -1t ${pattern} 2>/dev/null | head -n1 || true
}

health_state() {
  local container_ref="$1"
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_ref}" 2>/dev/null || true
}

service_container_id() {
  local service_name="$1"
  run_compose ps -q "${service_name}" | head -n1
}

wait_for_service_state() {
  local service_name="$1"
  local expected_state="$2"
  local deadline
  deadline=$((SECONDS + UP_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    local container_id
    local state
    container_id="$(service_container_id "${service_name}")"
    if [[ -z "${container_id}" ]]; then
      sleep 2
      continue
    fi
    state="$(health_state "${container_id}")"
    if [[ "${state}" == "${expected_state}" ]]; then
      echo "[rehearsal] ${service_name} ${state}"
      return 0
    fi
    sleep 2
  done
  echo "[rehearsal] timeout waiting for ${service_name} to become ${expected_state}" >&2
  local last_container
  last_container="$(service_container_id "${service_name}")"
  if [[ -n "${last_container}" ]]; then
    echo "[rehearsal] last state: $(health_state "${last_container}")" >&2
  else
    echo "[rehearsal] last state: container missing for service ${service_name}" >&2
  fi
  return 1
}

urlencode() {
  local raw="$1"
  python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "${raw}"
}

POSTGRES_USER="$(env_file_value POSTGRES_USER)"
POSTGRES_USER="${POSTGRES_USER:-classhub}"
POSTGRES_PASSWORD="$(env_file_value POSTGRES_PASSWORD)"
POSTGRES_DB="$(env_file_value POSTGRES_DB)"
POSTGRES_DB="${POSTGRES_DB:-classhub}"
POSTGRES_HOST="${POSTGRES_HOST:-${POSTGRES_SERVICE}}"
POSTGRES_CLIENT_IMAGE="${POSTGRES_CLIENT_IMAGE:-$(env_file_value POSTGRES_IMAGE)}"
POSTGRES_CLIENT_IMAGE="${POSTGRES_CLIENT_IMAGE:-postgres:16.8}"
TELEMETRY_DATABASE_URL="${TELEMETRY_DATABASE_URL:-$(env_file_value CLASSHUB_TELEMETRY_DATABASE_URL)}"

if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  echo "[rehearsal] POSTGRES_PASSWORD is required in compose/.env" >&2
  exit 1
fi

TELEMETRY_ENABLED=0
if [[ "${INCLUDE_TELEMETRY_DB}" == "1" ]]; then
  TELEMETRY_ENABLED=1
elif [[ "${INCLUDE_TELEMETRY_DB}" == "auto" && -n "${TELEMETRY_DATABASE_URL}" ]]; then
  TELEMETRY_ENABLED=1
fi
if (( TELEMETRY_ENABLED == 1 )) && [[ -z "${TELEMETRY_DATABASE_URL}" ]]; then
  echo "[rehearsal] CLASSHUB_TELEMETRY_DATABASE_URL is required when telemetry rehearsal is enabled" >&2
  exit 1
fi

run_telemetry_pg_dump() {
  local database_url="$1"
  if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "${database_url}"
    return 0
  fi
  docker run --rm \
    -e PGTARGET_URL="${database_url}" \
    "${POSTGRES_CLIENT_IMAGE}" \
    bash -lc 'pg_dump "${PGTARGET_URL}"'
}

run_telemetry_psql() {
  local database_url="$1"
  shift
  if command -v psql >/dev/null 2>&1; then
    psql "${database_url}" "$@"
    return 0
  fi
  docker run --rm -i \
    -e PGTARGET_URL="${database_url}" \
    "${POSTGRES_CLIENT_IMAGE}" \
    bash -lc 'psql "${PGTARGET_URL}" "$@"' -- "$@"
}

telemetry_url_parts() {
  local database_url="$1"
  local rehearsal_db="$2"
  python3 - "${database_url}" "${rehearsal_db}" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

database_url = sys.argv[1]
rehearsal_db = sys.argv[2]
parts = urlsplit(database_url)
path = parts.path or ""
db_name = path.rsplit("/", 1)[-1].split(";", 1)[0]
if not db_name:
    raise SystemExit("telemetry database URL must include a database name")

admin_path = path[: -(len(db_name))] + "postgres"
rehearsal_path = path[: -(len(db_name))] + rehearsal_db

print(db_name)
print(urlunsplit((parts.scheme, parts.netloc, admin_path, parts.query, parts.fragment)))
print(urlunsplit((parts.scheme, parts.netloc, rehearsal_path, parts.query, parts.fragment)))
PY
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ "${SKIP_BACKUP}" == "0" ]]; then
  echo "[rehearsal] 1/5 creating fresh backups (stamp ${STAMP})"
  mkdir -p "${BACKUP_ROOT}/postgres" "${BACKUP_ROOT}/uploads" "${BACKUP_ROOT}/minio"
  if (( TELEMETRY_ENABLED == 1 )); then
    mkdir -p "${BACKUP_ROOT}/telemetry_postgres"
  fi

  run_compose up -d "${POSTGRES_SERVICE}" >/dev/null
  wait_for_service_state "${POSTGRES_SERVICE}" healthy

  OUT_DIR="${BACKUP_ROOT}/postgres" STAMP="${STAMP}" COMPOSE_MODE="${COMPOSE_MODE}" \
    POSTGRES_SERVICE="${POSTGRES_SERVICE}" POSTGRES_USER="${POSTGRES_USER}" POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
    POSTGRES_DB="${POSTGRES_DB}" \
    bash "${BACKUP_POSTGRES_SCRIPT}"
  if (( TELEMETRY_ENABLED == 1 )); then
    OUT_DIR="${BACKUP_ROOT}/telemetry_postgres" STAMP="${STAMP}" \
      TELEMETRY_DATABASE_URL="${TELEMETRY_DATABASE_URL}" POSTGRES_CLIENT_IMAGE="${POSTGRES_CLIENT_IMAGE}" \
      bash "${BACKUP_TELEMETRY_POSTGRES_SCRIPT}"
  fi
  OUT_DIR="${BACKUP_ROOT}/uploads" STAMP="${STAMP}" bash "${BACKUP_UPLOADS_SCRIPT}"
  OUT_DIR="${BACKUP_ROOT}/minio" STAMP="${STAMP}" bash "${BACKUP_MINIO_SCRIPT}"

  POSTGRES_BACKUP_PATH="${BACKUP_ROOT}/postgres/classhub_${STAMP}.sql"
  if (( TELEMETRY_ENABLED == 1 )); then
    TELEMETRY_POSTGRES_BACKUP_PATH="${BACKUP_ROOT}/telemetry_postgres/classhub_telemetry_${STAMP}.sql"
  fi
  UPLOADS_BACKUP_PATH="${BACKUP_ROOT}/uploads/classhub_uploads_${STAMP}.tgz"
  MINIO_BACKUP_PATH="${BACKUP_ROOT}/minio/minio_${STAMP}.tgz"
else
  echo "[rehearsal] 1/5 skipping backup creation (--skip-backup)"
fi

if [[ -z "${POSTGRES_BACKUP_PATH}" ]]; then
  POSTGRES_BACKUP_PATH="$(latest_matching_file "${BACKUP_ROOT}/postgres/classhub_*.sql")"
fi
if (( TELEMETRY_ENABLED == 1 )) && [[ -z "${TELEMETRY_POSTGRES_BACKUP_PATH}" ]]; then
  TELEMETRY_POSTGRES_BACKUP_PATH="$(latest_matching_file "${BACKUP_ROOT}/telemetry_postgres/classhub_telemetry_*.sql")"
fi
if [[ -z "${UPLOADS_BACKUP_PATH}" ]]; then
  UPLOADS_BACKUP_PATH="$(latest_matching_file "${BACKUP_ROOT}/uploads/classhub_uploads_*.tgz")"
fi
if [[ -z "${MINIO_BACKUP_PATH}" ]]; then
  MINIO_BACKUP_PATH="$(latest_matching_file "${BACKUP_ROOT}/minio/minio_*.tgz")"
fi

for required_file in "${POSTGRES_BACKUP_PATH}" "${UPLOADS_BACKUP_PATH}" "${MINIO_BACKUP_PATH}"; do
  if [[ -z "${required_file}" || ! -f "${required_file}" ]]; then
    echo "[rehearsal] missing backup artifact: ${required_file:-<empty>}" >&2
    exit 1
  fi
done
if (( TELEMETRY_ENABLED == 1 )) && [[ -z "${TELEMETRY_POSTGRES_BACKUP_PATH}" || ! -f "${TELEMETRY_POSTGRES_BACKUP_PATH}" ]]; then
  echo "[rehearsal] missing telemetry backup artifact: ${TELEMETRY_POSTGRES_BACKUP_PATH:-<empty>}" >&2
  exit 1
fi

echo "[rehearsal] using artifacts:"
echo "  postgres: ${POSTGRES_BACKUP_PATH}"
if (( TELEMETRY_ENABLED == 1 )); then
  echo "  telemetry: ${TELEMETRY_POSTGRES_BACKUP_PATH}"
fi
echo "  uploads:  ${UPLOADS_BACKUP_PATH}"
echo "  minio:    ${MINIO_BACKUP_PATH}"

DB_SUFFIX="$(date -u +%Y%m%d%H%M%S)"
REHEARSAL_DB="classhub_restore_${DB_SUFFIX}"
REHEARSAL_TMP_DIR="${TEMP_ROOT%/}/${REHEARSAL_DB}"
DB_CREATED=0
TELEMETRY_REHEARSAL_DB="classhub_telemetry_restore_${DB_SUFFIX}"
TELEMETRY_REHEARSAL_ADMIN_URL=""
REHEARSAL_TELEMETRY_DATABASE_URL=""
TELEMETRY_DB_CREATED=0
if (( TELEMETRY_ENABLED == 1 )); then
  mapfile -t TELEMETRY_URL_PARTS < <(telemetry_url_parts "${TELEMETRY_DATABASE_URL}" "${TELEMETRY_REHEARSAL_DB}")
  TELEMETRY_REHEARSAL_ADMIN_URL="${TELEMETRY_URL_PARTS[1]}"
  REHEARSAL_TELEMETRY_DATABASE_URL="${TELEMETRY_URL_PARTS[2]}"
fi

cleanup() {
  local code=$?
  if [[ "${DB_CREATED}" == "1" ]]; then
    run_compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_SERVICE}" \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres \
      -c "DROP DATABASE IF EXISTS \"${REHEARSAL_DB}\";" >/dev/null 2>&1 || true
  fi
  if [[ "${TELEMETRY_DB_CREATED}" == "1" && -n "${TELEMETRY_REHEARSAL_ADMIN_URL}" ]]; then
    run_telemetry_psql "${TELEMETRY_REHEARSAL_ADMIN_URL}" \
      -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS \"${TELEMETRY_REHEARSAL_DB}\";" >/dev/null 2>&1 || true
  fi

  if [[ "${KEEP_TEMP}" == "1" ]]; then
    echo "[rehearsal] kept temp restore dir: ${REHEARSAL_TMP_DIR}"
  else
    rm -rf "${REHEARSAL_TMP_DIR}" || true
  fi
  exit "${code}"
}
trap cleanup EXIT

echo "[rehearsal] 2/5 preparing temporary restore workspace"
mkdir -p "${REHEARSAL_TMP_DIR}/uploads" "${REHEARSAL_TMP_DIR}/minio"
tar -xzf "${UPLOADS_BACKUP_PATH}" -C "${REHEARSAL_TMP_DIR}/uploads"
tar -xzf "${MINIO_BACKUP_PATH}" -C "${REHEARSAL_TMP_DIR}/minio"

UPLOADS_FILE_COUNT="$(find "${REHEARSAL_TMP_DIR}/uploads" -type f | wc -l | tr -d ' ')"
MINIO_FILE_COUNT="$(find "${REHEARSAL_TMP_DIR}/minio" -type f | wc -l | tr -d ' ')"
echo "[rehearsal] extracted uploads files: ${UPLOADS_FILE_COUNT}"
echo "[rehearsal] extracted minio files:   ${MINIO_FILE_COUNT}"

echo "[rehearsal] 3/5 restoring Postgres backup into temporary database (${REHEARSAL_DB})"
run_compose up -d "${POSTGRES_SERVICE}" >/dev/null
wait_for_service_state "${POSTGRES_SERVICE}" healthy

run_compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_SERVICE}" \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres \
  -c "DROP DATABASE IF EXISTS \"${REHEARSAL_DB}\";" \
  -c "CREATE DATABASE \"${REHEARSAL_DB}\";" >/dev/null
DB_CREATED=1

run_compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_SERVICE}" \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${REHEARSAL_DB}" < "${POSTGRES_BACKUP_PATH}" >/dev/null

if (( TELEMETRY_ENABLED == 1 )); then
  echo "[rehearsal] restoring telemetry backup into temporary database (${TELEMETRY_REHEARSAL_DB})"
  run_telemetry_psql "${TELEMETRY_REHEARSAL_ADMIN_URL}" \
    -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"${TELEMETRY_REHEARSAL_DB}\";" \
    -c "CREATE DATABASE \"${TELEMETRY_REHEARSAL_DB}\";" >/dev/null
  TELEMETRY_DB_CREATED=1
  run_telemetry_psql "${REHEARSAL_TELEMETRY_DATABASE_URL}" \
    -v ON_ERROR_STOP=1 < "${TELEMETRY_POSTGRES_BACKUP_PATH}" >/dev/null
fi

POSTGRES_USER_ESCAPED="$(urlencode "${POSTGRES_USER}")"
POSTGRES_PASSWORD_ESCAPED="$(urlencode "${POSTGRES_PASSWORD}")"
REHEARSAL_DATABASE_URL="postgres://${POSTGRES_USER_ESCAPED}:${POSTGRES_PASSWORD_ESCAPED}@${POSTGRES_HOST}:5432/${REHEARSAL_DB}"

echo "[rehearsal] 4/5 validating ClassHub + Helper migrations against restored database"
CLASSHUB_REHEARSAL_ENV=(
  -e DATABASE_URL="${REHEARSAL_DATABASE_URL}"
)
if (( TELEMETRY_ENABLED == 1 )); then
  CLASSHUB_REHEARSAL_ENV+=(
    -e CLASSHUB_TELEMETRY_DATABASE_URL="${REHEARSAL_TELEMETRY_DATABASE_URL}"
    -e CLASSHUB_TELEMETRY_WRITE_MODE="dual"
    -e CLASSHUB_TELEMETRY_READ_MODE="telemetry"
  )
else
  CLASSHUB_REHEARSAL_ENV+=(
    -e CLASSHUB_TELEMETRY_DATABASE_URL=""
    -e CLASSHUB_TELEMETRY_WRITE_MODE="off"
    -e CLASSHUB_TELEMETRY_READ_MODE="core"
  )
fi

run_compose run --rm --no-deps "${CLASSHUB_REHEARSAL_ENV[@]}" classhub_web python manage.py migrate --noinput >/dev/null
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" helper_web python manage.py migrate --noinput >/dev/null
if (( TELEMETRY_ENABLED == 1 )); then
  run_compose run --rm --no-deps "${CLASSHUB_REHEARSAL_ENV[@]}" \
    classhub_web python manage.py migrate --database telemetry hub_telemetry --noinput >/dev/null
fi

echo "[rehearsal] 5/5 running Django checks against restored database"
run_compose run --rm --no-deps "${CLASSHUB_REHEARSAL_ENV[@]}" classhub_web python manage.py check >/dev/null
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" helper_web python manage.py check >/dev/null
if (( TELEMETRY_ENABLED == 1 )); then
  run_compose run --rm --no-deps "${CLASSHUB_REHEARSAL_ENV[@]}" \
    classhub_web python manage.py check_telemetry_parity \
    --window-days "${TELEMETRY_REHEARSAL_PARITY_WINDOW_DAYS}" --allow-drift >/dev/null
fi

echo "[rehearsal] PASS"
echo "[rehearsal] restore rehearsal verified using temporary database ${REHEARSAL_DB}"
if (( TELEMETRY_ENABLED == 1 )); then
  echo "[rehearsal] telemetry restore rehearsal verified using temporary database ${TELEMETRY_REHEARSAL_DB}"
fi
