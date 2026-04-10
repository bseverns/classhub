#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_CHECK="${ROOT_DIR}/scripts/validate_env_secrets.sh"
OPERATOR_PREFLIGHT="${ROOT_DIR}/scripts/operator_preflight.py"
PORT_GUARD="${ROOT_DIR}/scripts/check_compose_port_exposure.py"
MIGRATION_GATE="${ROOT_DIR}/scripts/migration_gate.sh"
CONTENT_PREFLIGHT="${ROOT_DIR}/scripts/content_preflight.sh"
LLM_BACKEND_CHECK="${ROOT_DIR}/scripts/check_llm_backend.sh"
ENSURE_LOCAL_OLLAMA_MODEL="${ROOT_DIR}/scripts/ensure_local_ollama_model.sh"
COMPOSE_ENV_LIB="${ROOT_DIR}/scripts/lib/compose_env.sh"
SMOKE_CHECK="${ROOT_DIR}/scripts/smoke_check.sh"
GOLDEN_SMOKE="${ROOT_DIR}/scripts/golden_path_smoke.sh"
ENV_FILE="${ROOT_DIR}/compose/.env"

COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod or dev
BRING_UP=1
BUILD_STACK=0
UP_TIMEOUT_SECONDS=180

COURSE_SLUG="${COURSE_SLUG:-piper_scratch_12_session}"
STRICT_CONTENT=0

SMOKE_MODE="${SMOKE_MODE:-golden}" # golden|strict|basic|off
LLM_CHECK_MODE="${LLM_CHECK_MODE:-auto}" # auto|required|advisory|off
HELPER_SMOKE_MODE="${HELPER_SMOKE_MODE:-auto}" # auto|required|advisory|off
SMOKE_BASE_URL="${SMOKE_BASE_URL:-}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-20}"
SMOKE_INSECURE_TLS="${SMOKE_INSECURE_TLS:-0}"
SMOKE_HELPER_MESSAGE="${SMOKE_HELPER_MESSAGE:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/system_doctor.sh [options]

Runs a full stack self-check:
1) env guardrails
2) operator preflight
3) port exposure guard
4) migration gate
5) content preflight
6) compose health
7) private LLM backend check
8) smoke checks

Options:
  --compose-mode <prod|dev>       Compose files (default: prod)
  --skip-up                       Do not run docker compose up -d
  --build                         Build images when bringing up stack
  --up-timeout-seconds <seconds>  Max wait for healthy services (default: 180)
  --course-slug <slug>            Course slug for content preflight (default: piper_scratch_12_session)
  --strict-content                Run strict global content preflight checks
  --smoke-mode <golden|strict|basic|off>
                                  golden: bootstrap fixtures + strict smoke
                                  strict: run scripts/smoke_check.sh --strict
                                  basic: run scripts/smoke_check.sh
                                  off: skip smoke step
  --llm-check-mode <auto|required|advisory|off>
                                  auto: require local CPU/backend health, warn only for remote/private backends
  --helper-smoke-mode <auto|required|advisory|off>
                                  auto: require helper chat for local CPU/backend, warn only for remote/private backends
  --base-url <url>                Override smoke base URL
  --timeout-seconds <seconds>     Curl timeout passed to smoke checks (default: 20)
  --insecure-tls                  Use curl -k for HTTPS smoke checks
  --helper-message <text>         Override helper smoke message
  -h, --help                      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --skip-up)
      BRING_UP=0
      shift
      ;;
    --build)
      BUILD_STACK=1
      shift
      ;;
    --up-timeout-seconds)
      UP_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --course-slug)
      COURSE_SLUG="$2"
      shift 2
      ;;
    --strict-content)
      STRICT_CONTENT=1
      shift
      ;;
    --smoke-mode)
      SMOKE_MODE="$2"
      shift 2
      ;;
    --llm-check-mode)
      LLM_CHECK_MODE="$2"
      shift 2
      ;;
    --helper-smoke-mode)
      HELPER_SMOKE_MODE="$2"
      shift 2
      ;;
    --base-url)
      SMOKE_BASE_URL="$2"
      shift 2
      ;;
    --timeout-seconds)
      SMOKE_TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --insecure-tls)
      SMOKE_INSECURE_TLS=1
      shift
      ;;
    --helper-message)
      SMOKE_HELPER_MESSAGE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[doctor] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "[doctor] docker is required" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[doctor] missing compose/.env (copy from compose/.env.example first)" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${COMPOSE_ENV_LIB}"

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[doctor] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

if llm_uses_local_ollama_compose "${ENV_FILE}"; then
  COMPOSE_ARGS+=(--profile local-ollama)
fi

case "${SMOKE_MODE}" in
  golden|strict|basic|off)
    ;;
  *)
    echo "[doctor] invalid --smoke-mode '${SMOKE_MODE}' (expected golden|strict|basic|off)" >&2
    exit 1
    ;;
esac

case "${LLM_CHECK_MODE}" in
  auto|required|advisory|off)
    ;;
  *)
    echo "[doctor] invalid --llm-check-mode '${LLM_CHECK_MODE}' (expected auto|required|advisory|off)" >&2
    exit 1
    ;;
esac

case "${HELPER_SMOKE_MODE}" in
  auto|required|advisory|off)
    ;;
  *)
    echo "[doctor] invalid --helper-smoke-mode '${HELPER_SMOKE_MODE}' (expected auto|required|advisory|off)" >&2
    exit 1
    ;;
esac

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

print_compose_diagnostics() {
  echo "[doctor] compose service state (for failure diagnosis):" >&2
  run_compose ps >&2 || true
  echo "[doctor] recent compose logs (tail=200):" >&2
  run_compose logs --no-color --tail=200 classhub_web helper_web caddy postgres redis >&2 || true
}

health_state() {
  local container_name="$1"
  docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_name}" 2>/dev/null || true
}

wait_for_container_state() {
  local container_name="$1"
  local expected_state="$2"
  local deadline
  deadline=$((SECONDS + UP_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    local state
    state="$(health_state "${container_name}")"
    if [[ "${state}" == "${expected_state}" ]]; then
      echo "[doctor] ${container_name} ${state}"
      return 0
    fi
    sleep 2
  done
  echo "[doctor] timeout waiting for ${container_name} to become ${expected_state}" >&2
  echo "[doctor] last state: $(health_state "${container_name}")" >&2
  return 1
}

echo "[doctor] 1/8 env guardrails"
"${ENV_CHECK}"

echo "[doctor] 2/8 operator preflight"
python3 "${OPERATOR_PREFLIGHT}" --env-file "${ENV_FILE}"

echo "[doctor] 3/8 port exposure guard"
python3 "${PORT_GUARD}"

echo "[doctor] 4/8 migration gate"
"${MIGRATION_GATE}" --compose-mode "${COMPOSE_MODE}"

echo "[doctor] 5/8 content preflight (${COURSE_SLUG})"
if [[ "${STRICT_CONTENT}" == "1" ]]; then
  bash "${CONTENT_PREFLIGHT}" "${COURSE_SLUG}" --strict-global
else
  bash "${CONTENT_PREFLIGHT}" "${COURSE_SLUG}"
fi

echo "[doctor] 6/8 compose health"
if [[ "${BRING_UP}" == "1" ]]; then
  if [[ "${BUILD_STACK}" == "1" ]]; then
    if ! run_compose up -d --build; then
      echo "[doctor] compose up failed" >&2
      print_compose_diagnostics
      exit 1
    fi
  else
    if ! run_compose up -d; then
      echo "[doctor] compose up failed" >&2
      print_compose_diagnostics
      exit 1
    fi
  fi
fi

wait_for_container_state classhub_postgres healthy
wait_for_container_state classhub_redis healthy
wait_for_container_state classhub_web healthy
wait_for_container_state helper_web healthy
wait_for_container_state classhub_caddy running
if llm_uses_local_ollama_compose "${ENV_FILE}"; then
  wait_for_container_state classhub_ollama healthy
  bash "${ENSURE_LOCAL_OLLAMA_MODEL}" --compose-mode "${COMPOSE_MODE}"
fi

echo "[doctor] applying runtime migrations"
run_compose exec -T classhub_web python manage.py migrate --noinput
run_compose exec -T helper_web python manage.py migrate --noinput

echo "[doctor] 7/8 llm backend check"
EFFECTIVE_LLM_CHECK_MODE="${LLM_CHECK_MODE}"
if [[ "${EFFECTIVE_LLM_CHECK_MODE}" == "auto" ]]; then
  EFFECTIVE_LLM_CHECK_MODE="$(llm_check_mode_auto "${ENV_FILE}")"
fi
if [[ "${EFFECTIVE_LLM_CHECK_MODE}" == "off" ]]; then
  echo "[doctor] llm backend check skipped (mode=off)"
elif "${LLM_BACKEND_CHECK}" --compose-mode "${COMPOSE_MODE}" --probe-chat; then
  :
elif [[ "${EFFECTIVE_LLM_CHECK_MODE}" == "advisory" ]]; then
  echo "[doctor][warn] llm backend check failed in advisory mode; continuing with core stack validation" >&2
else
  print_compose_diagnostics
  exit 1
fi

echo "[doctor] 8/8 smoke checks (${SMOKE_MODE})"
EFFECTIVE_HELPER_SMOKE_MODE="${HELPER_SMOKE_MODE}"
if [[ "${EFFECTIVE_HELPER_SMOKE_MODE}" == "auto" ]]; then
  EFFECTIVE_HELPER_SMOKE_MODE="$(helper_smoke_mode_auto "${ENV_FILE}")"
fi
if [[ "${SMOKE_MODE}" == "golden" ]]; then
  GOLDEN_ARGS=(
    --compose-mode "${COMPOSE_MODE}"
    --skip-up
    --course-slug "${COURSE_SLUG}"
    --timeout-seconds "${SMOKE_TIMEOUT_SECONDS}"
    --helper-smoke-mode "${EFFECTIVE_HELPER_SMOKE_MODE}"
  )
  if [[ "${SMOKE_INSECURE_TLS}" == "1" ]]; then
    GOLDEN_ARGS+=(--insecure-tls)
  fi
  if [[ -n "${SMOKE_BASE_URL}" ]]; then
    GOLDEN_ARGS+=(--base-url "${SMOKE_BASE_URL}")
  fi
  if [[ -n "${SMOKE_HELPER_MESSAGE}" ]]; then
    GOLDEN_ARGS+=(--helper-message "${SMOKE_HELPER_MESSAGE}")
  fi
  if ! "${GOLDEN_SMOKE}" "${GOLDEN_ARGS[@]}"; then
    print_compose_diagnostics
    exit 1
  fi
elif [[ "${SMOKE_MODE}" == "strict" ]]; then
  SMOKE_ENV=(
    "SMOKE_TIMEOUT_SECONDS=${SMOKE_TIMEOUT_SECONDS}"
    "SMOKE_INSECURE_TLS=${SMOKE_INSECURE_TLS}"
    "SMOKE_HELPER_MODE=${EFFECTIVE_HELPER_SMOKE_MODE}"
  )
  if [[ -n "${SMOKE_BASE_URL}" ]]; then
    SMOKE_ENV+=("SMOKE_BASE_URL=${SMOKE_BASE_URL}")
  fi
  if [[ -n "${SMOKE_HELPER_MESSAGE}" ]]; then
    SMOKE_ENV+=("SMOKE_HELPER_MESSAGE=${SMOKE_HELPER_MESSAGE}")
  fi
  if ! env "${SMOKE_ENV[@]}" "${SMOKE_CHECK}" --strict; then
    print_compose_diagnostics
    exit 1
  fi
elif [[ "${SMOKE_MODE}" == "basic" ]]; then
  SMOKE_ENV=(
    "SMOKE_TIMEOUT_SECONDS=${SMOKE_TIMEOUT_SECONDS}"
    "SMOKE_INSECURE_TLS=${SMOKE_INSECURE_TLS}"
    "SMOKE_HELPER_MODE=${EFFECTIVE_HELPER_SMOKE_MODE}"
  )
  if [[ -n "${SMOKE_BASE_URL}" ]]; then
    SMOKE_ENV+=("SMOKE_BASE_URL=${SMOKE_BASE_URL}")
  fi
  if [[ -n "${SMOKE_HELPER_MESSAGE}" ]]; then
    SMOKE_ENV+=("SMOKE_HELPER_MESSAGE=${SMOKE_HELPER_MESSAGE}")
  fi
  if ! env "${SMOKE_ENV[@]}" "${SMOKE_CHECK}"; then
    print_compose_diagnostics
    exit 1
  fi
else
  echo "[doctor] smoke checks skipped (--smoke-mode off)"
fi

echo "[doctor] ALL CHECKS PASSED"
