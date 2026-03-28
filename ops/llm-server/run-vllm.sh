#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/classhub/llm-server.env}"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[run-vllm] missing ${ENV_FILE}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${ENV_FILE}"

if [[ -z "${VLLM_MODEL:-}" ]]; then
  echo "[run-vllm] VLLM_MODEL is required" >&2
  exit 1
fi

if [[ -z "${LLM_SHARED_API_KEY:-}" ]]; then
  echo "[run-vllm] LLM_SHARED_API_KEY is required" >&2
  exit 1
fi

VENV_BIN="${VENV_BIN:-/opt/classhub-llm/.venv/bin}"

exec "${VENV_BIN}/vllm" serve "${VLLM_MODEL}" \
  --host "${VLLM_HOST:-127.0.0.1}" \
  --port "${VLLM_PORT:-8000}" \
  --api-key "${LLM_SHARED_API_KEY}" \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}"
