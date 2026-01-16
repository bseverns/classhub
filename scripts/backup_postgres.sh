#!/usr/bin/env bash
set -euo pipefail

# Backup Postgres from the docker-compose stack.
# Run from the host with access to docker.

OUT_DIR="${OUT_DIR:-/srv/classhub/backups/postgres}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT_DIR"

# Adjust service name if you rename compose services.
docker exec classhub_postgres pg_dump -U "${POSTGRES_USER:-classhub}" "${POSTGRES_DB:-classhub}" > "$OUT_DIR/classhub_${STAMP}.sql"

echo "Wrote $OUT_DIR/classhub_${STAMP}.sql"
