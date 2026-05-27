#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/compose/.env}"
BASE_URL="${JETSON_B_BASE_URL:-}"
API_KEY="${JETSON_B_API_KEY:-}"
MODEL="${JETSON_B_MODEL:-}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-15}"
PROBE_CHAT=0

usage() {
  cat <<'EOF'
Usage: bash scripts/check_jetson_b_route.sh [options]

Checks the private ClassHub -> lab_mind Jetson-B model route from the
machine where the command runs. Run it on the LMS host after Headscale
enrollment and Jetson Tailscale Serve setup.

Options:
  --env-file <path>         Env file to read (default: compose/.env)
  --base-url <url>          Override LLM_BASE_URL from env
  --api-key <token>         Override LLM_API_KEY from env
  --model <model>           Override LLM_MODEL from env
  --probe-chat              Also POST a small /v1/chat/completions probe
  --timeout-seconds <sec>   Curl timeout (default: 15)
  -h, --help                Show this help
EOF
}

env_file_value() {
  local key="$1"
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
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --probe-chat)
      PROBE_CHAT=1
      shift
      ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[jetson-route] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

BASE_URL="${BASE_URL:-$(env_file_value LLM_BASE_URL)}"
API_KEY="${API_KEY:-$(env_file_value LLM_API_KEY)}"
MODEL="${MODEL:-$(env_file_value LLM_MODEL)}"
BACKEND="$(env_file_value LLM_BACKEND)"

if [[ -z "${BASE_URL}" ]]; then
  echo "[jetson-route] missing LLM_BASE_URL (or --base-url)" >&2
  exit 1
fi

if [[ "${BASE_URL}" != https://* ]]; then
  echo "[jetson-route] expected tailnet HTTPS base URL, got: ${BASE_URL}" >&2
  exit 1
fi

if [[ "${BACKEND}" != "" && "${BACKEND}" != "openai_compatible" ]]; then
  echo "[jetson-route] warning: LLM_BACKEND is '${BACKEND}', expected openai_compatible for lab_mind llama.cpp" >&2
fi

if command -v tailscale >/dev/null 2>&1; then
  if ! tailscale status >/dev/null 2>&1; then
    echo "[jetson-route] warning: tailscale status failed on this host" >&2
  fi
else
  echo "[jetson-route] warning: tailscale CLI not found; continuing with HTTPS probe only" >&2
fi

AUTH_ARGS=()
if [[ -n "${API_KEY}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${API_KEY}")
fi

echo "[jetson-route] probing ${BASE_URL}/v1/models"
curl -fsS --max-time "${TIMEOUT_SECONDS}" "${AUTH_ARGS[@]}" "${BASE_URL%/}/v1/models" >/dev/null
echo "[jetson-route] models endpoint reachable"

if [[ "${PROBE_CHAT}" == "1" ]]; then
  if [[ -z "${MODEL}" ]]; then
    echo "[jetson-route] missing LLM_MODEL (or --model) for --probe-chat" >&2
    exit 1
  fi
  echo "[jetson-route] probing ${BASE_URL}/v1/chat/completions model=${MODEL}"
  curl -fsS --max-time "${TIMEOUT_SECONDS}" \
    "${AUTH_ARGS[@]}" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with one short sentence confirming readiness.\"}],\"max_tokens\":32,\"temperature\":0.2}" \
    "${BASE_URL%/}/v1/chat/completions" >/dev/null
  echo "[jetson-route] chat probe reachable"
fi

echo "[jetson-route] OK"
