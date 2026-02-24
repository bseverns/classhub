#!/usr/bin/env bash
set -euo pipefail

# Backup Class Hub student uploads from the bind-mounted uploads directory.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SRC="${SRC:-${ROOT_DIR}/data/classhub_uploads}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/backups/uploads}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"

mkdir -p "$OUT_DIR"

if [[ ! -d "$SRC" ]]; then
  echo "Uploads source does not exist: $SRC" >&2
  exit 1
fi

tar -czf "$OUT_DIR/classhub_uploads_${STAMP}.tgz" -C "$SRC" .

echo "Wrote $OUT_DIR/classhub_uploads_${STAMP}.tgz"
