#!/usr/bin/env bash
set -euo pipefail

# Day-1 MinIO backup (simple filesystem copy from bind-mounted data directory).
# If MinIO grows, switch to bucket replication or S3 sync tools.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SRC="${SRC:-${ROOT_DIR}/data/minio}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/backups/minio}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"

mkdir -p "$OUT_DIR"

if [[ ! -d "$SRC" ]]; then
  echo "MinIO source does not exist: $SRC" >&2
  exit 1
fi

tar -czf "$OUT_DIR/minio_${STAMP}.tgz" -C "$SRC" .

echo "Wrote $OUT_DIR/minio_${STAMP}.tgz"
