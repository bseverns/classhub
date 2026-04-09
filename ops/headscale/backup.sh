#!/usr/bin/env bash
set -euo pipefail

HEADSCALE_ROOT="${HEADSCALE_ROOT:-/srv/headscale}"
OUT_DIR=""
LABEL=""

usage() {
  cat <<'EOF'
Usage: bash ops/headscale/backup.sh [options]

Create one archive containing the Headscale control-plane state needed for restore.

Options:
  --headscale-root <dir>   Runtime root (default: /srv/headscale)
  --out-dir <dir>          Backup output dir (default: <headscale-root>/backups)
  --label <name>           Optional label prefix, e.g. pre_restore
  -h, --help               Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headscale-root)
      HEADSCALE_ROOT="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --label)
      LABEL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[headscale-backup] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

OUT_DIR="${OUT_DIR:-${HEADSCALE_ROOT}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PREFIX="headscale"
if [[ -n "${LABEL}" ]]; then
  PREFIX="${PREFIX}_${LABEL}"
fi
ARCHIVE_PATH="${OUT_DIR}/${PREFIX}_${STAMP}.tgz"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"

if [[ ! -d "${HEADSCALE_ROOT}" ]]; then
  echo "[headscale-backup] missing root directory: ${HEADSCALE_ROOT}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

REQUIRED_FILES=(
  ".env"
  "docker-compose.yml"
  "Caddyfile"
  "config/config.yaml"
  "config/policy.hujson"
)

for rel in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "${HEADSCALE_ROOT}/${rel}" ]]; then
    echo "[headscale-backup] missing required file: ${HEADSCALE_ROOT}/${rel}" >&2
    exit 1
  fi
done

INCLUDE_PATHS=(
  ".env"
  "docker-compose.yml"
  "Caddyfile"
  "config/config.yaml"
  "config/policy.hujson"
)

OPTIONAL_DIRS=(
  "data/lib"
  "data/caddy_data"
  "data/caddy_config"
)

for rel in "${OPTIONAL_DIRS[@]}"; do
  if [[ -d "${HEADSCALE_ROOT}/${rel}" ]]; then
    INCLUDE_PATHS+=("${rel}")
  fi
done

(
  cd "${HEADSCALE_ROOT}"
  tar czf "${ARCHIVE_PATH}" "${INCLUDE_PATHS[@]}"
)

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${ARCHIVE_PATH}" > "${CHECKSUM_PATH}"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${ARCHIVE_PATH}" > "${CHECKSUM_PATH}"
else
  echo "[headscale-backup] missing checksum tool (sha256sum/shasum)" >&2
  exit 1
fi

echo "[headscale-backup] wrote ${ARCHIVE_PATH}"
echo "[headscale-backup] checksum ${CHECKSUM_PATH}"
