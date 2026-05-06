#!/usr/bin/env bash
set -euo pipefail

# Backup Postgres from the docker-compose stack.
# Run from the host with access to docker.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/compose/docker-compose.yml}"
COMPOSE_OVERRIDE="${COMPOSE_OVERRIDE:-${ROOT_DIR}/compose/docker-compose.override.yml}"
COMPOSE_MODE="${COMPOSE_MODE:-prod}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/compose/.env}"

OUT_DIR="${OUT_DIR:-${ROOT_DIR}/backups/postgres}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT_DIR"

env_file_value() {
  local key="$1"
  local raw
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo ""
    return 0
  fi
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_FILE}")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}")
else
  echo "Invalid COMPOSE_MODE '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

POSTGRES_USER="${POSTGRES_USER:-$(env_file_value POSTGRES_USER)}"
POSTGRES_USER="${POSTGRES_USER:-classhub}"
POSTGRES_DB="${POSTGRES_DB:-$(env_file_value POSTGRES_DB)}"
POSTGRES_DB="${POSTGRES_DB:-classhub}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(env_file_value POSTGRES_PASSWORD)}"

run_compose exec -T -e PGPASSWORD="${POSTGRES_PASSWORD}" "${POSTGRES_SERVICE}" \
  pg_dump -h 127.0.0.1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  > "$OUT_DIR/classhub_${STAMP}.sql"

echo "Wrote $OUT_DIR/classhub_${STAMP}.sql"
