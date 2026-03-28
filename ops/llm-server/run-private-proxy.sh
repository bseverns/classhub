#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/classhub/llm-server.env}"
CONFIG_FILE="${PRIVATE_PROXY_CADDYFILE:-/opt/classhub-llm/Caddyfile.private}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if ! command -v caddy >/dev/null 2>&1; then
  echo "[private-proxy] caddy binary not found" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[private-proxy] missing config file: ${CONFIG_FILE}" >&2
  exit 1
fi

if [[ -z "${LLM_SHARED_API_KEY:-}" || "${#LLM_SHARED_API_KEY}" -lt 20 ]]; then
  echo "[private-proxy] LLM_SHARED_API_KEY must be set to a strong shared secret" >&2
  exit 1
fi

if [[ -z "${PRIVATE_PROXY_LISTEN:-}" ]]; then
  echo "[private-proxy] PRIVATE_PROXY_LISTEN must be set" >&2
  exit 1
fi

if [[ -z "${UPSTREAM_OLLAMA:-}" && -z "${UPSTREAM_VLLM:-}" ]]; then
  echo "[private-proxy] set UPSTREAM_OLLAMA or UPSTREAM_VLLM in ${ENV_FILE}" >&2
  exit 1
fi

exec caddy run --config "${CONFIG_FILE}" --adapter caddyfile
