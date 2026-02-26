#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"
A11Y_DIR="${ROOT_DIR}/scripts/a11y"

COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod|dev
CLASS_NAME="${CLASS_NAME:-Smoke Validation Class}"
TEACHER_USERNAME="${TEACHER_USERNAME:-smoke_teacher}"
A11Y_BASE_URL="${A11Y_BASE_URL:-}"
A11Y_FAIL_IMPACT="${A11Y_FAIL_IMPACT:-critical}"
A11Y_TIMEOUT_MS="${A11Y_TIMEOUT_MS:-30000}"
A11Y_INSTALL_BROWSERS="${A11Y_INSTALL_BROWSERS:-0}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/a11y_smoke.sh [options]

Options:
  --compose-mode <prod|dev>   Compose files (default: prod)
  --base-url <url>            Base URL to scan (default: derived from compose/.env)
  --class-name <name>         Class fixture name (default: Smoke Validation Class)
  --teacher-username <name>   Teacher fixture username (default: smoke_teacher)
  --fail-impact <impact>      Violation threshold: minor|moderate|serious|critical (default: critical)
  --timeout-ms <ms>           Per-page navigation timeout (default: 30000)
  --install-browsers          Install Playwright chromium + system deps before scan
  -h, --help                  Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-mode)
      COMPOSE_MODE="$2"
      shift 2
      ;;
    --base-url)
      A11Y_BASE_URL="$2"
      shift 2
      ;;
    --class-name)
      CLASS_NAME="$2"
      shift 2
      ;;
    --teacher-username)
      TEACHER_USERNAME="$2"
      shift 2
      ;;
    --fail-impact)
      A11Y_FAIL_IMPACT="$2"
      shift 2
      ;;
    --timeout-ms)
      A11Y_TIMEOUT_MS="$2"
      shift 2
      ;;
    --install-browsers)
      A11Y_INSTALL_BROWSERS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[a11y] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[a11y] invalid --compose-mode '${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
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

resolve_base_url() {
  if [[ -n "${A11Y_BASE_URL}" ]]; then
    echo "${A11Y_BASE_URL}"
    return 0
  fi
  local caddyfile_template
  local domain
  local env_base
  caddyfile_template="$(env_file_value CADDYFILE_TEMPLATE)"
  env_base="$(env_file_value SMOKE_BASE_URL)"
  domain="$(env_file_value DOMAIN)"

  if [[ "${caddyfile_template}" == "Caddyfile.local" ]]; then
    echo "http://localhost"
  elif [[ -n "${env_base}" ]]; then
    echo "${env_base}"
  elif [[ -n "${domain}" ]]; then
    echo "https://${domain}"
  else
    echo "http://localhost"
  fi
}

if ! command -v node >/dev/null 2>&1; then
  echo "[a11y] node is required" >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "[a11y] npm is required" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "[a11y] docker is required" >&2
  exit 1
fi

echo "[a11y] installing smoke dependencies"
if [[ -f "${A11Y_DIR}/package-lock.json" ]]; then
  npm ci --prefix "${A11Y_DIR}" --no-fund --no-audit
else
  npm install --prefix "${A11Y_DIR}" --no-fund --no-audit
fi

if [[ "${A11Y_INSTALL_BROWSERS}" == "1" ]]; then
  echo "[a11y] installing Playwright chromium"
  npm --prefix "${A11Y_DIR}" run install-browsers
fi

echo "[a11y] preparing teacher session"
SESSION_OUTPUT="$(run_compose exec -T \
  -e SMOKE_CLASS_NAME="${CLASS_NAME}" \
  -e SMOKE_TEACHER_USERNAME="${TEACHER_USERNAME}" \
  classhub_web \
  python manage.py shell -c \
  "import os; from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model; from django.contrib.sessions.backends.db import SessionStore; from django_otp.plugins.otp_totp.models import TOTPDevice; from hub.models import Class; cls = Class.objects.get(name=os.environ['SMOKE_CLASS_NAME']); user = get_user_model().objects.get(username=os.environ['SMOKE_TEACHER_USERNAME']); device, _ = TOTPDevice.objects.get_or_create(user=user, name='teacher-primary', defaults={'confirmed': True}); device.confirmed = True; device.save(update_fields=['confirmed']); session = SessionStore(); session[SESSION_KEY] = str(user.pk); session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'; session[HASH_SESSION_KEY] = user.get_session_auth_hash(); session['otp_device_id'] = device.persistent_id; session.save(); print(f'{cls.id}:{session.session_key}')")"
SESSION_OUTPUT="$(echo "${SESSION_OUTPUT}" | tr -d '\r' | tail -n1)"
CLASS_ID="${SESSION_OUTPUT%%:*}"
A11Y_TEACHER_SESSION_KEY="${SESSION_OUTPUT#*:}"
if [[ -z "${CLASS_ID}" || -z "${A11Y_TEACHER_SESSION_KEY}" || "${SESSION_OUTPUT}" != *:* ]]; then
  echo "[a11y] FAIL: unable to mint teacher session; run golden smoke first" >&2
  exit 1
fi

A11Y_BASE_URL="$(resolve_base_url)"
echo "[a11y] scanning ${A11Y_BASE_URL} (class_id=${CLASS_ID}, fail-impact=${A11Y_FAIL_IMPACT})"

A11Y_BASE_URL="${A11Y_BASE_URL}" \
A11Y_CLASS_ID="${CLASS_ID}" \
A11Y_TEACHER_SESSION_KEY="${A11Y_TEACHER_SESSION_KEY}" \
A11Y_FAIL_IMPACT="${A11Y_FAIL_IMPACT}" \
A11Y_TIMEOUT_MS="${A11Y_TIMEOUT_MS}" \
npm --prefix "${A11Y_DIR}" run smoke

echo "[a11y] PASS"
