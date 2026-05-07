#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/compose/.env}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/backups/telemetry_postgres}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
POSTGRES_CLIENT_IMAGE="${POSTGRES_CLIENT_IMAGE:-postgres:16.8}"
TELEMETRY_DATABASE_URL="${TELEMETRY_DATABASE_URL:-}"

mkdir -p "${OUT_DIR}"

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

if [[ -z "${TELEMETRY_DATABASE_URL}" ]]; then
  TELEMETRY_DATABASE_URL="$(env_file_value CLASSHUB_TELEMETRY_DATABASE_URL)"
fi
if [[ -z "${TELEMETRY_DATABASE_URL}" ]]; then
  echo "[backup-telemetry] CLASSHUB_TELEMETRY_DATABASE_URL is required" >&2
  exit 1
fi

dump_path="${OUT_DIR}/classhub_telemetry_${STAMP}.sql"

run_pg_dump() {
  if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "${TELEMETRY_DATABASE_URL}"
    return 0
  fi
  docker run --rm \
    -e TELEMETRY_DATABASE_URL="${TELEMETRY_DATABASE_URL}" \
    "${POSTGRES_CLIENT_IMAGE}" \
    bash -lc 'pg_dump "${TELEMETRY_DATABASE_URL}"'
}

run_pg_dump > "${dump_path}"
echo "Wrote ${dump_path}"
