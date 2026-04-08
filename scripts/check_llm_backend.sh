#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"

COMPOSE_MODE="prod"
PROBE_CHAT=0

usage() {
  cat <<'EOF'
Usage: bash scripts/check_llm_backend.sh [options]

Checks helper LLM backend config + connectivity from inside helper_web.

Options:
  --compose-mode <prod|dev>   Compose file selection (default: prod)
  --probe-chat                Run a tiny completion after health probe
  -h, --help                  Show this help
EOF
}

env_file_value() {
  local key="$1"
  local explicit="${!key-}"
  if [[ -n "${explicit}" ]]; then
    echo "${explicit}"
    return 0
  fi
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo ""
    return 0
  fi
  local raw
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --probe-chat)
      PROBE_CHAT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[llm-check] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[llm-check] missing compose/.env" >&2
  exit 1
fi

LLM_ENABLED="${LLM_ENABLED:-$(env_file_value LLM_ENABLED)}"
LLM_ENABLED="${LLM_ENABLED:-1}"
BACKEND="${LLM_BACKEND:-$(env_file_value LLM_BACKEND)}"
if [[ -z "${BACKEND}" ]]; then
  BACKEND="${HELPER_LLM_BACKEND:-$(env_file_value HELPER_LLM_BACKEND)}"
fi
BACKEND="${BACKEND:-ollama}"

if [[ "${LLM_ENABLED}" == "0" ]]; then
  echo "[llm-check] skipped: LLM_ENABLED=0"
  exit 0
fi

if [[ "${BACKEND}" == "mock" || "${BACKEND}" == "openai" || "${BACKEND}" == "openai_responses" ]]; then
  echo "[llm-check] skipped: backend=${BACKEND}"
  exit 0
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[llm-check] invalid --compose-mode '${COMPOSE_MODE}'" >&2
  exit 1
fi

CMD=(python manage.py check_llm_backend --require-healthy)
if [[ "${PROBE_CHAT}" == "1" ]]; then
  CMD+=(--probe-chat)
fi

echo "[llm-check] backend=${BACKEND} compose_mode=${COMPOSE_MODE} probe_chat=${PROBE_CHAT}"
docker compose "${COMPOSE_ARGS[@]}" exec -T helper_web "${CMD[@]}"
