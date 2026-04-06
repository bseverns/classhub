#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"
LIB_FILE="${ROOT_DIR}/scripts/lib/compose_env.sh"

if [[ ! -f "${LIB_FILE}" ]]; then
  echo "[ollama-ensure] missing helper library: ${LIB_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${LIB_FILE}"

COMPOSE_MODE="prod"

usage() {
  cat <<'EOF'
Usage: bash scripts/ensure_local_ollama_model.sh [--compose-mode prod|dev]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ollama-ensure] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ollama-ensure] missing compose/.env" >&2
  exit 1
fi

if ! llm_uses_local_ollama_compose "${ENV_FILE}"; then
  echo "[ollama-ensure] skipped: backend is not compose-local ollama"
  exit 0
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[ollama-ensure] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

COMPOSE_ARGS+=(--profile local-ollama)

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

if ! run_compose ps --services --filter status=running | grep -qx "ollama"; then
  echo "[ollama-ensure] local ollama profile is expected, but service is not running" >&2
  exit 1
fi

MODEL_NAME="$(llm_backend_model "${ENV_FILE}")"
if [[ -z "${MODEL_NAME}" ]]; then
  echo "[ollama-ensure] resolved model is empty" >&2
  exit 1
fi

MODEL_LIST=""
for _attempt in $(seq 1 15); do
  if MODEL_LIST="$(run_compose exec -T ollama ollama list 2>/dev/null)"; then
    break
  fi
  sleep 2
done

if [[ -z "${MODEL_LIST}" ]]; then
  echo "[ollama-ensure] unable to query local ollama after startup wait" >&2
  exit 1
fi

if printf '%s\n' "${MODEL_LIST}" | awk 'NR > 1 {print $1}' | grep -Fxq "${MODEL_NAME}"; then
  echo "[ollama-ensure] model already present: ${MODEL_NAME}"
  exit 0
fi

echo "[ollama-ensure] pulling model into local ollama: ${MODEL_NAME}"
run_compose exec -T ollama ollama pull "${MODEL_NAME}"
echo "[ollama-ensure] model ready: ${MODEL_NAME}"
