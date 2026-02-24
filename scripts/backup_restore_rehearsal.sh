#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose/docker-compose.yml"
COMPOSE_OVERRIDE="${ROOT_DIR}/compose/docker-compose.override.yml"
ENV_FILE="${ROOT_DIR}/compose/.env"

BACKUP_POSTGRES_SCRIPT="${ROOT_DIR}/scripts/backup_postgres.sh"
BACKUP_UPLOADS_SCRIPT="${ROOT_DIR}/scripts/backup_uploads.sh"
BACKUP_MINIO_SCRIPT="${ROOT_DIR}/scripts/backup_minio.sh"

COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod or dev
BACKUP_ROOT="${BACKUP_ROOT:-${ROOT_DIR}/backups}"
TEMP_ROOT="${TEMP_ROOT:-/tmp/classhub_restore_rehearsal}"
SKIP_BACKUP=0
KEEP_TEMP=0
UP_TIMEOUT_SECONDS="${UP_TIMEOUT_SECONDS:-180}"

POSTGRES_BACKUP_PATH="${POSTGRES_BACKUP_PATH:-}"
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
  --uploads-backup <file>         Path to uploads .tgz backup (used with --skip-backup)
  --minio-backup <file>           Path to MinIO .tgz backup (used with --skip-backup)
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
  local container_name="$1"
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_name}" 2>/dev/null || true
}

wait_for_container_state() {
  local container_name="$1"
  local expected_state="$2"
  local deadline
  deadline=$((SECONDS + UP_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    local state
    state="$(health_state "${container_name}")"
    if [[ "${state}" == "${expected_state}" ]]; then
      echo "[rehearsal] ${container_name} ${state}"
      return 0
    fi
    sleep 2
  done
  echo "[rehearsal] timeout waiting for ${container_name} to become ${expected_state}" >&2
  echo "[rehearsal] last state: $(health_state "${container_name}")" >&2
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

if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  echo "[rehearsal] POSTGRES_PASSWORD is required in compose/.env" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ "${SKIP_BACKUP}" == "0" ]]; then
  echo "[rehearsal] 1/5 creating fresh backups (stamp ${STAMP})"
  mkdir -p "${BACKUP_ROOT}/postgres" "${BACKUP_ROOT}/uploads" "${BACKUP_ROOT}/minio"

  OUT_DIR="${BACKUP_ROOT}/postgres" STAMP="${STAMP}" POSTGRES_USER="${POSTGRES_USER}" POSTGRES_DB="${POSTGRES_DB}" \
    bash "${BACKUP_POSTGRES_SCRIPT}"
  OUT_DIR="${BACKUP_ROOT}/uploads" STAMP="${STAMP}" bash "${BACKUP_UPLOADS_SCRIPT}"
  OUT_DIR="${BACKUP_ROOT}/minio" STAMP="${STAMP}" bash "${BACKUP_MINIO_SCRIPT}"

  POSTGRES_BACKUP_PATH="${BACKUP_ROOT}/postgres/classhub_${STAMP}.sql"
  UPLOADS_BACKUP_PATH="${BACKUP_ROOT}/uploads/classhub_uploads_${STAMP}.tgz"
  MINIO_BACKUP_PATH="${BACKUP_ROOT}/minio/minio_${STAMP}.tgz"
else
  echo "[rehearsal] 1/5 skipping backup creation (--skip-backup)"
fi

if [[ -z "${POSTGRES_BACKUP_PATH}" ]]; then
  POSTGRES_BACKUP_PATH="$(latest_matching_file "${BACKUP_ROOT}/postgres/classhub_*.sql")"
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

echo "[rehearsal] using artifacts:"
echo "  postgres: ${POSTGRES_BACKUP_PATH}"
echo "  uploads:  ${UPLOADS_BACKUP_PATH}"
echo "  minio:    ${MINIO_BACKUP_PATH}"

DB_SUFFIX="$(date -u +%Y%m%d%H%M%S)"
REHEARSAL_DB="classhub_restore_${DB_SUFFIX}"
REHEARSAL_TMP_DIR="${TEMP_ROOT%/}/${REHEARSAL_DB}"
DB_CREATED=0

cleanup() {
  local code=$?
  if [[ "${DB_CREATED}" == "1" ]]; then
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" classhub_postgres \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres \
      -c "DROP DATABASE IF EXISTS \"${REHEARSAL_DB}\";" >/dev/null 2>&1 || true
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
run_compose up -d classhub_postgres >/dev/null
wait_for_container_state classhub_postgres healthy

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" classhub_postgres \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d postgres \
  -c "DROP DATABASE IF EXISTS \"${REHEARSAL_DB}\";" \
  -c "CREATE DATABASE \"${REHEARSAL_DB}\";" >/dev/null
DB_CREATED=1

docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD}" classhub_postgres \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${REHEARSAL_DB}" < "${POSTGRES_BACKUP_PATH}" >/dev/null

POSTGRES_USER_ESCAPED="$(urlencode "${POSTGRES_USER}")"
POSTGRES_PASSWORD_ESCAPED="$(urlencode "${POSTGRES_PASSWORD}")"
REHEARSAL_DATABASE_URL="postgres://${POSTGRES_USER_ESCAPED}:${POSTGRES_PASSWORD_ESCAPED}@postgres:5432/${REHEARSAL_DB}"

echo "[rehearsal] 4/5 validating ClassHub + Helper migrations against restored database"
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" classhub_web python manage.py migrate --noinput >/dev/null
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" helper_web python manage.py migrate --noinput >/dev/null

echo "[rehearsal] 5/5 running Django checks against restored database"
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" classhub_web python manage.py check >/dev/null
run_compose run --rm --no-deps -e DATABASE_URL="${REHEARSAL_DATABASE_URL}" helper_web python manage.py check >/dev/null

echo "[rehearsal] PASS"
echo "[rehearsal] restore rehearsal verified using temporary database ${REHEARSAL_DB}"
