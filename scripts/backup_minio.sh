#!/usr/bin/env bash
set -euo pipefail

# Day-1 MinIO backup (simple filesystem copy from bind-mounted data directory).
# If MinIO grows, switch to bucket replication or S3 sync tools.

SRC="${SRC:-/srv/classhub/data/minio}"
OUT_DIR="${OUT_DIR:-/srv/classhub/backups/minio}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$OUT_DIR"

tar -czf "$OUT_DIR/minio_${STAMP}.tgz" -C "$SRC" .

echo "Wrote $OUT_DIR/minio_${STAMP}.tgz"
