#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose/docker-compose.yml"
MIGRATION_GATE="${ROOT_DIR}/scripts/migration_gate.sh"
SMOKE_CHECK="${ROOT_DIR}/scripts/smoke_check.sh"
GOLDEN_SMOKE="${ROOT_DIR}/scripts/golden_path_smoke.sh"
ENV_CHECK="${ROOT_DIR}/scripts/validate_env_secrets.sh"
OPERATOR_PREFLIGHT="${ROOT_DIR}/scripts/operator_preflight.py"
ENSURE_LOCAL_OLLAMA_MODEL="${ROOT_DIR}/scripts/ensure_local_ollama_model.sh"
COMPOSE_ENV_LIB="${ROOT_DIR}/scripts/lib/compose_env.sh"
LAST_GOOD_FILE="${ROOT_DIR}/.deploy/last_good_ref"
SMOKE_LOG_FILE="$(mktemp)"
trap 'rm -f "${SMOKE_LOG_FILE}"' EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] docker is required" >&2
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "[deploy] missing compose file: ${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/compose/.env" ]]; then
  echo "[deploy] missing compose/.env (copy from compose/.env.example first)" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/compose/Caddyfile" ]]; then
  echo "[deploy] note: compose/Caddyfile is optional when using CADDYFILE_TEMPLATE in compose/.env"
fi

if [[ ! -x "${ENV_CHECK}" ]]; then
  echo "[deploy] missing or non-executable env check script: ${ENV_CHECK}" >&2
  exit 1
fi

run_compose() {
  local compose_args=(-f "${COMPOSE_FILE}")
  if [[ -f "${COMPOSE_ENV_LIB}" ]]; then
    # shellcheck disable=SC1090
    source "${COMPOSE_ENV_LIB}"
    if llm_uses_local_ollama_compose "${ROOT_DIR}/compose/.env"; then
      compose_args+=(--profile local-ollama)
    fi
  fi
  docker compose "${compose_args[@]}" "$@"
}

env_file_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" "${ROOT_DIR}/compose/.env" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

rollback_if_configured() {
  if [[ -n "${ROLLBACK_CMD:-}" ]]; then
    echo "[deploy] smoke failed; running rollback command"
    echo "[deploy] ROLLBACK_CMD=${ROLLBACK_CMD}"
    bash -lc "${ROLLBACK_CMD}"
  else
    echo "[deploy] smoke failed; no ROLLBACK_CMD configured"
    echo "[deploy] last recorded good ref (if any): $(cat "${LAST_GOOD_FILE}" 2>/dev/null || echo '<none>')"
  fi
}

echo "[deploy] validating compose/.env secrets and routing settings"
"${ENV_CHECK}"

echo "[deploy] running operator preflight"
python3 "${OPERATOR_PREFLIGHT}" --env-file "${ROOT_DIR}/compose/.env"

echo "[deploy] running migration gate"
"${MIGRATION_GATE}"

extra_template_from_env="$(env_file_value CADDY_EXTRA_CONFIG_TEMPLATE)"
extra_template_from_env="${extra_template_from_env:-Caddyfile.extra.empty}"
static_site_root_from_env="$(env_file_value CADDY_STATIC_SITE_ROOT_HOST)"
static_site_root_from_env="${static_site_root_from_env:-./static-site.empty}"
if [[ "${static_site_root_from_env}" == /* ]]; then
  EXPECTED_STATIC_SITE_ROOT="${static_site_root_from_env}"
else
  EXPECTED_STATIC_SITE_ROOT="${ROOT_DIR}/compose/${static_site_root_from_env#./}"
fi
if [[ "${extra_template_from_env}" == "Caddyfile.extra.static-site" ]]; then
  if [[ ! -d "${EXPECTED_STATIC_SITE_ROOT}" ]]; then
    echo "[deploy] static site root not found: ${EXPECTED_STATIC_SITE_ROOT}" >&2
    exit 1
  fi
  EXPECTED_STATIC_SITE_ROOT="$(cd "${EXPECTED_STATIC_SITE_ROOT}" && pwd -P)"
  if [[ ! -f "${EXPECTED_STATIC_SITE_ROOT}/index.html" ]]; then
    echo "[deploy] static site index not found: ${EXPECTED_STATIC_SITE_ROOT}/index.html" >&2
    exit 1
  fi
fi

echo "[deploy] launching production compose (docker-compose.yml only)"
run_compose up -d --build

echo "[deploy] ensuring local ollama model is ready when compose-local ollama is enabled"
bash "${ENSURE_LOCAL_OLLAMA_MODEL}" --compose-mode prod

echo "[deploy] applying runtime migrations"
run_compose exec -T classhub_web python manage.py migrate --noinput
run_compose exec -T helper_web python manage.py migrate --noinput

template_from_env="$(env_file_value CADDYFILE_TEMPLATE)"
template_from_env="${template_from_env:-Caddyfile.local}"
EXPECTED_CADDYFILE="${ROOT_DIR}/compose/${template_from_env}"

if [[ ! -f "${EXPECTED_CADDYFILE}" ]]; then
  echo "[deploy] expected caddy template file not found: ${EXPECTED_CADDYFILE}" >&2
  exit 1
fi

ACTUAL_CADDYFILE="$(docker inspect classhub_caddy --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)"

if [[ -z "${ACTUAL_CADDYFILE}" ]]; then
  echo "[deploy] unable to resolve classhub_caddy mount source" >&2
  rollback_if_configured
  exit 1
fi

if [[ "${ACTUAL_CADDYFILE}" != "${EXPECTED_CADDYFILE}" ]]; then
  echo "[deploy] caddy config guardrail failed" >&2
  echo "[deploy] expected: ${EXPECTED_CADDYFILE}" >&2
  echo "[deploy] actual:   ${ACTUAL_CADDYFILE}" >&2
  rollback_if_configured
  exit 1
fi

echo "[deploy] caddy mount guardrail OK"

EXPECTED_CADDY_EXTRA="${ROOT_DIR}/compose/${extra_template_from_env}"
ACTUAL_CADDY_EXTRA="$(docker inspect classhub_caddy --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile.extra"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)"
if [[ "${ACTUAL_CADDY_EXTRA}" != "${EXPECTED_CADDY_EXTRA}" ]]; then
  echo "[deploy] caddy extra config guardrail failed" >&2
  echo "[deploy] expected: ${EXPECTED_CADDY_EXTRA}" >&2
  echo "[deploy] actual:   ${ACTUAL_CADDY_EXTRA:-missing}" >&2
  rollback_if_configured
  exit 1
fi

if [[ "${extra_template_from_env}" == "Caddyfile.extra.static-site" ]]; then
  ACTUAL_STATIC_SITE_ROOT="$(docker inspect classhub_caddy --format '{{range .Mounts}}{{if eq .Destination "/srv/caddy-static-site"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)"
  if [[ "${ACTUAL_STATIC_SITE_ROOT}" != "${EXPECTED_STATIC_SITE_ROOT}" ]]; then
    echo "[deploy] caddy static site mount guardrail failed" >&2
    echo "[deploy] expected: ${EXPECTED_STATIC_SITE_ROOT}" >&2
    echo "[deploy] actual:   ${ACTUAL_STATIC_SITE_ROOT:-missing}" >&2
    rollback_if_configured
    exit 1
  fi
fi

echo "[deploy] caddy extra mount guardrail OK"

CADDY_RUNNING="$(docker inspect classhub_caddy --format '{{.State.Running}}' 2>/dev/null || true)"
if [[ "${CADDY_RUNNING}" != "true" ]]; then
  echo "[deploy] classhub_caddy is not running (state=${CADDY_RUNNING:-unknown})" >&2
  rollback_if_configured
  exit 1
fi

echo "[deploy] caddy runtime guardrail OK"

echo "[deploy] formatting caddy config in container temp path"
if ! docker exec classhub_caddy sh -ec \
  'cp /etc/caddy/Caddyfile /tmp/Caddyfile.deploy && caddy fmt --overwrite /tmp/Caddyfile.deploy >/dev/null'; then
  echo "[deploy] caddy fmt failed" >&2
  rollback_if_configured
  exit 1
fi

echo "[deploy] reloading caddy config from formatted template"
if ! docker exec classhub_caddy caddy reload --config /tmp/Caddyfile.deploy --adapter caddyfile; then
  echo "[deploy] caddy reload failed" >&2
  rollback_if_configured
  exit 1
fi
echo "[deploy] caddy reload OK"

SMOKE_MODE="${DEPLOY_SMOKE_MODE:-strict}"
HELPER_SMOKE_MODE="${DEPLOY_HELPER_SMOKE_MODE:-auto}"
if [[ -f "${COMPOSE_ENV_LIB}" ]]; then
  # shellcheck disable=SC1090
  source "${COMPOSE_ENV_LIB}"
  if [[ "${HELPER_SMOKE_MODE}" == "auto" ]]; then
    HELPER_SMOKE_MODE="$(helper_smoke_mode_auto "${ROOT_DIR}/compose/.env")"
  fi
fi
if [[ "${SMOKE_MODE}" == "golden" ]]; then
  set +e
  "${GOLDEN_SMOKE}" --compose-mode prod --skip-up --helper-smoke-mode "${HELPER_SMOKE_MODE}"
  smoke_status=$?
  set -e
elif [[ "${SMOKE_MODE}" == "strict" ]]; then
  set +e
  SMOKE_HELPER_MODE="${HELPER_SMOKE_MODE}" "${SMOKE_CHECK}" --strict 2>&1 | tee "${SMOKE_LOG_FILE}"
  smoke_status=$?
  set -e
  if [[ ${smoke_status} -ne 0 ]] && grep -Eq '\[smoke\] FAIL: /join returned (404: \{"error":[[:space:]]*"invalid_code"\}|invalid_code for SMOKE_CLASS_CODE=)' "${SMOKE_LOG_FILE}"; then
    echo "[deploy] strict smoke failed due stale SMOKE_CLASS_CODE; retrying golden smoke"
    set +e
    "${GOLDEN_SMOKE}" --compose-mode prod --skip-up
    smoke_status=$?
    set -e
  fi
else
  set +e
  SMOKE_HELPER_MODE="${HELPER_SMOKE_MODE}" "${SMOKE_CHECK}"
  smoke_status=$?
  set -e
fi

if [[ ${smoke_status} -ne 0 ]]; then
  rollback_if_configured
  exit ${smoke_status}
fi

mkdir -p "$(dirname "${LAST_GOOD_FILE}")"
git -C "${ROOT_DIR}" rev-parse HEAD > "${LAST_GOOD_FILE}" 2>/dev/null || true

echo "[deploy] SUCCESS"
