#!/usr/bin/env bash
set -euo pipefail

HEADSCALE_ROOT="${HEADSCALE_ROOT:-/srv/headscale}"
BACKUP_PATH=""
START_STACK=0
STOP_STACK=1
KEEP_TEMP=0

usage() {
  cat <<'EOF'
Usage: bash ops/headscale/restore.sh --backup <archive.tgz> [options]

Restore the Headscale control-plane bundle onto a host prepared by install.sh.

Options:
  --headscale-root <dir>   Runtime root (default: /srv/headscale)
  --backup <archive.tgz>   Backup archive produced by backup.sh
  --start-stack            Start docker compose after restore
  --no-stop-stack          Do not stop docker compose before restore
  --keep-temp              Keep extracted temp directory for inspection
  -h, --help               Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headscale-root)
      HEADSCALE_ROOT="$2"
      shift 2
      ;;
    --backup)
      BACKUP_PATH="$2"
      shift 2
      ;;
    --start-stack)
      START_STACK=1
      shift
      ;;
    --no-stop-stack)
      STOP_STACK=0
      shift
      ;;
    --keep-temp)
      KEEP_TEMP=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[headscale-restore] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${BACKUP_PATH}" ]]; then
  echo "[headscale-restore] --backup is required" >&2
  exit 1
fi

if [[ ! -f "${BACKUP_PATH}" ]]; then
  echo "[headscale-restore] missing backup archive: ${BACKUP_PATH}" >&2
  exit 1
fi

mkdir -p \
  "${HEADSCALE_ROOT}" \
  "${HEADSCALE_ROOT}/config" \
  "${HEADSCALE_ROOT}/data/lib" \
  "${HEADSCALE_ROOT}/data/caddy_data" \
  "${HEADSCALE_ROOT}/data/caddy_config" \
  "${HEADSCALE_ROOT}/backups"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_DIR="$(mktemp -d "/tmp/classhub_headscale_restore_${STAMP}.XXXXXX")"

cleanup() {
  if [[ "${KEEP_TEMP}" == "1" ]]; then
    echo "[headscale-restore] kept temp dir: ${TMP_DIR}"
  else
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

PRE_RESTORE_ARCHIVE="${HEADSCALE_ROOT}/backups/headscale_pre_restore_${STAMP}.tgz"
PRE_RESTORE_CHECKSUM="${PRE_RESTORE_ARCHIVE}.sha256"

EXISTING_PATHS=(
  "${HEADSCALE_ROOT}/.env"
  "${HEADSCALE_ROOT}/docker-compose.yml"
  "${HEADSCALE_ROOT}/Caddyfile"
  "${HEADSCALE_ROOT}/config/config.yaml"
  "${HEADSCALE_ROOT}/config/policy.hujson"
)

if [[ -d "${HEADSCALE_ROOT}/data/lib" ]] || [[ -f "${HEADSCALE_ROOT}/.env" ]]; then
  INCLUDE_PATHS=()
  for abs in "${EXISTING_PATHS[@]}"; do
    if [[ -e "${abs}" ]]; then
      INCLUDE_PATHS+=("${abs#${HEADSCALE_ROOT}/}")
    fi
  done
  for rel in data/lib data/caddy_data data/caddy_config; do
    if [[ -d "${HEADSCALE_ROOT}/${rel}" ]]; then
      INCLUDE_PATHS+=("${rel}")
    fi
  done
  if [[ "${#INCLUDE_PATHS[@]}" -gt 0 ]]; then
    (
      cd "${HEADSCALE_ROOT}"
      tar czf "${PRE_RESTORE_ARCHIVE}" "${INCLUDE_PATHS[@]}"
    )
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum "${PRE_RESTORE_ARCHIVE}" > "${PRE_RESTORE_CHECKSUM}"
    elif command -v shasum >/dev/null 2>&1; then
      shasum -a 256 "${PRE_RESTORE_ARCHIVE}" > "${PRE_RESTORE_CHECKSUM}"
    fi
    echo "[headscale-restore] wrote safety backup ${PRE_RESTORE_ARCHIVE}"
  fi
fi

if [[ "${STOP_STACK}" == "1" ]] && command -v docker >/dev/null 2>&1 && [[ -f "${HEADSCALE_ROOT}/docker-compose.yml" ]]; then
  (
    cd "${HEADSCALE_ROOT}"
    docker compose down || true
  )
fi

tar xzf "${BACKUP_PATH}" -C "${TMP_DIR}"

for rel in .env docker-compose.yml Caddyfile; do
  if [[ -f "${TMP_DIR}/${rel}" ]]; then
    cp -f "${TMP_DIR}/${rel}" "${HEADSCALE_ROOT}/${rel}"
  fi
done

for rel in config/config.yaml config/policy.hujson; do
  if [[ -f "${TMP_DIR}/${rel}" ]]; then
    mkdir -p "$(dirname "${HEADSCALE_ROOT}/${rel}")"
    cp -f "${TMP_DIR}/${rel}" "${HEADSCALE_ROOT}/${rel}"
  fi
done

for rel in data/lib data/caddy_data data/caddy_config; do
  if [[ -d "${TMP_DIR}/${rel}" ]]; then
    mkdir -p "${HEADSCALE_ROOT}/${rel}"
    cp -a "${TMP_DIR}/${rel}/." "${HEADSCALE_ROOT}/${rel}/"
  fi
done

if [[ "${START_STACK}" == "1" ]]; then
  (
    cd "${HEADSCALE_ROOT}"
    docker compose up -d --remove-orphans
  )
fi

echo "[headscale-restore] restored ${BACKUP_PATH} into ${HEADSCALE_ROOT}"
