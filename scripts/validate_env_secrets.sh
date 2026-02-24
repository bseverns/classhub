#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/compose/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[env-check] missing compose/.env (copy from compose/.env.example first)" >&2
  exit 1
fi

env_file_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

env_file_raw_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d= -f2- || true)"
  echo "${raw}"
}

fail() {
  echo "[env-check] FAIL: $*" >&2
  exit 1
}

contains_icase() {
  local haystack="$1"
  local needle="$2"
  if [[ "${haystack,,}" == *"${needle,,}"* ]]; then
    return 0
  fi
  return 1
}

is_unsafe_secret() {
  local v="$1"
  local lower="${v,,}"

  if [[ -z "${v}" ]]; then
    return 0
  fi

  if [[ "${#v}" -lt 16 ]]; then
    return 0
  fi

  local blocked=(
    "replace_me"
    "replace_me_strong"
    "change_me"
    "changeme"
    "dev-secret"
    "secret"
    "password"
    "__set_me__"
    "example"
  )

  local token
  for token in "${blocked[@]}"; do
    if contains_icase "${lower}" "${token}"; then
      return 0
    fi
  done

  if [[ "${lower}" == django-insecure* ]]; then
    return 0
  fi

  return 1
}

require_nonempty() {
  local key="$1"
  local val
  val="$(env_file_value "${key}")"
  if [[ -z "${val}" ]]; then
    fail "${key} is empty or missing"
  fi
}

require_strong_secret() {
  local key="$1"
  local min_len="$2"
  local val
  val="$(env_file_value "${key}")"
  if [[ -z "${val}" ]]; then
    fail "${key} is empty or missing"
  fi
  if [[ "${#val}" -lt "${min_len}" ]]; then
    fail "${key} must be at least ${min_len} characters"
  fi
  if is_unsafe_secret "${val}"; then
    fail "${key} looks like a placeholder/default value"
  fi
}

require_distinct_values() {
  local key_a="$1"
  local key_b="$2"
  local value_a
  local value_b
  value_a="$(env_file_value "${key_a}")"
  value_b="$(env_file_value "${key_b}")"
  if [[ -n "${value_a}" && -n "${value_b}" && "${value_a}" == "${value_b}" ]]; then
    fail "${key_a} and ${key_b} must not be identical"
  fi
}

require_compose_safe_dollars() {
  local key="$1"
  local raw
  raw="$(env_file_raw_value "${key}")"
  if [[ -z "${raw}" ]]; then
    return 0
  fi

  # Docker Compose treats unescaped "$" as interpolation. Allow either:
  # - a single-quoted value (literal)
  # - escaped dollars "$$"
  if [[ "${raw}" == \'*\' ]]; then
    return 0
  fi

  local reduced="${raw//\$\$/}"
  if [[ "${reduced}" == *'$'* ]]; then
    fail "${key} contains unescaped '$'. Use single quotes around the value or escape each '$' as '$$' in compose/.env"
  fi
}

int_or_default() {
  local raw="$1"
  local fallback="$2"
  if [[ "${raw}" =~ ^[0-9]+$ ]]; then
    echo "${raw}"
    return 0
  fi
  echo "${fallback}"
}

number_or_default() {
  local raw="$1"
  local fallback="$2"
  if [[ "${raw}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "${raw}"
    return 0
  fi
  echo "${fallback}"
}

DJANGO_DEBUG="$(env_file_value DJANGO_DEBUG)"
DJANGO_DEBUG="${DJANGO_DEBUG:-0}"
RUN_MIGRATIONS_ON_START="$(env_file_value RUN_MIGRATIONS_ON_START)"
RUN_MIGRATIONS_ON_START="${RUN_MIGRATIONS_ON_START:-1}"

require_nonempty "POSTGRES_DB"
require_nonempty "POSTGRES_USER"
require_strong_secret "POSTGRES_PASSWORD" 16
require_strong_secret "MINIO_ROOT_PASSWORD" 16
require_nonempty "MINIO_ROOT_USER"

if [[ "${DJANGO_DEBUG}" == "0" ]]; then
  require_strong_secret "DJANGO_SECRET_KEY" 32
  require_strong_secret "DEVICE_HINT_SIGNING_KEY" 32
  require_distinct_values "DJANGO_SECRET_KEY" "DEVICE_HINT_SIGNING_KEY"
  require_strong_secret "CLASSHUB_INTERNAL_EVENTS_TOKEN" 16
  ADMIN_2FA_REQUIRED="$(env_file_value DJANGO_ADMIN_2FA_REQUIRED)"
  ADMIN_2FA_REQUIRED="${ADMIN_2FA_REQUIRED:-1}"
  if [[ "${ADMIN_2FA_REQUIRED}" != "1" ]]; then
    fail "DJANGO_ADMIN_2FA_REQUIRED must be 1 when DJANGO_DEBUG=0"
  fi
  if [[ "${RUN_MIGRATIONS_ON_START}" != "0" ]]; then
    fail "RUN_MIGRATIONS_ON_START must be 0 when DJANGO_DEBUG=0 (deploy scripts run migrations explicitly)"
  fi
else
  if [[ -z "$(env_file_value DJANGO_SECRET_KEY)" ]]; then
    fail "DJANGO_SECRET_KEY is required even in debug mode"
  fi
fi

if [[ "${RUN_MIGRATIONS_ON_START}" != "0" && "${RUN_MIGRATIONS_ON_START}" != "1" ]]; then
  fail "RUN_MIGRATIONS_ON_START must be 0 or 1"
fi

APP_UID_RAW="$(env_file_value APP_UID)"
APP_GID_RAW="$(env_file_value APP_GID)"
if [[ -n "${APP_UID_RAW}" && ! "${APP_UID_RAW}" =~ ^[0-9]+$ ]]; then
  fail "APP_UID must be an integer when set"
fi
if [[ -n "${APP_GID_RAW}" && ! "${APP_GID_RAW}" =~ ^[0-9]+$ ]]; then
  fail "APP_GID must be an integer when set"
fi
APP_UID="${APP_UID_RAW:-1000}"
APP_GID="${APP_GID_RAW:-1000}"
if [[ "${APP_UID}" -le 0 ]]; then
  fail "APP_UID must be greater than 0 (non-root runtime identity)"
fi
if [[ "${APP_GID}" -le 0 ]]; then
  fail "APP_GID must be greater than 0 (non-root runtime identity)"
fi

HELPER_LLM_BACKEND="$(env_file_value HELPER_LLM_BACKEND)"
if [[ "${HELPER_LLM_BACKEND,,}" == "openai" ]]; then
  require_strong_secret "OPENAI_API_KEY" 20
fi

HELPER_GUNICORN_TIMEOUT_SECONDS="$(number_or_default "$(env_file_value HELPER_GUNICORN_TIMEOUT_SECONDS)" "180")"
HELPER_BACKEND_MAX_ATTEMPTS="$(int_or_default "$(env_file_value HELPER_BACKEND_MAX_ATTEMPTS)" "2")"
if [[ "${HELPER_BACKEND_MAX_ATTEMPTS}" -lt 1 ]]; then
  HELPER_BACKEND_MAX_ATTEMPTS=1
fi
OLLAMA_TIMEOUT_SECONDS="$(number_or_default "$(env_file_value OLLAMA_TIMEOUT_SECONDS)" "30")"
HELPER_QUEUE_MAX_WAIT_SECONDS="$(number_or_default "$(env_file_value HELPER_QUEUE_MAX_WAIT_SECONDS)" "10")"
HELPER_BACKOFF_SECONDS="$(number_or_default "$(env_file_value HELPER_BACKOFF_SECONDS)" "0.4")"

if [[ "${HELPER_LLM_BACKEND,,}" == "ollama" ]]; then
  # Worst-case helper request budget:
  # queue wait + retries * ollama timeout + exponential backoff + safety margin.
  helper_backoff_total="0"
  helper_backoff_step="${HELPER_BACKOFF_SECONDS}"
  for ((i=1; i<HELPER_BACKEND_MAX_ATTEMPTS; i++)); do
    helper_backoff_total="$(
      awk -v total="${helper_backoff_total}" -v step="${helper_backoff_step}" 'BEGIN { printf "%.6f", total + step }'
    )"
    helper_backoff_step="$(
      awk -v step="${helper_backoff_step}" 'BEGIN { printf "%.6f", step * 2 }'
    )"
  done

  helper_required_timeout="$(
    awk -v queue="${HELPER_QUEUE_MAX_WAIT_SECONDS}" \
        -v tries="${HELPER_BACKEND_MAX_ATTEMPTS}" \
        -v call_timeout="${OLLAMA_TIMEOUT_SECONDS}" \
        -v backoff="${helper_backoff_total}" \
        'BEGIN { printf "%.6f", queue + (tries * call_timeout) + backoff + 5 }'
  )"

  if awk -v gunicorn_timeout="${HELPER_GUNICORN_TIMEOUT_SECONDS}" -v required="${helper_required_timeout}" \
      'BEGIN { exit !(gunicorn_timeout < required) }'
  then
    fail "HELPER_GUNICORN_TIMEOUT_SECONDS (${HELPER_GUNICORN_TIMEOUT_SECONDS}) is too low for current Ollama retry budget (~${helper_required_timeout}s required; check HELPER_BACKEND_MAX_ATTEMPTS, OLLAMA_TIMEOUT_SECONDS, HELPER_QUEUE_MAX_WAIT_SECONDS, HELPER_BACKOFF_SECONDS)"
  fi
fi

CADDYFILE_TEMPLATE="$(env_file_value CADDYFILE_TEMPLATE)"
if [[ "${CADDYFILE_TEMPLATE}" != "Caddyfile.local" && "${CADDYFILE_TEMPLATE}" != "Caddyfile.domain" && "${CADDYFILE_TEMPLATE}" != "Caddyfile.domain.assets" ]]; then
  fail "CADDYFILE_TEMPLATE must be Caddyfile.local, Caddyfile.domain, or Caddyfile.domain.assets"
fi

if [[ "${CADDYFILE_TEMPLATE}" == "Caddyfile.domain" || "${CADDYFILE_TEMPLATE}" == "Caddyfile.domain.assets" ]]; then
  DOMAIN_VAL="$(env_file_value DOMAIN)"
  if [[ -z "${DOMAIN_VAL}" ]]; then
    fail "DOMAIN is required when using Caddyfile.domain or Caddyfile.domain.assets"
  fi
  if contains_icase "${DOMAIN_VAL}" "example.org" || contains_icase "${DOMAIN_VAL}" "example.com"; then
    fail "DOMAIN appears to be a placeholder: ${DOMAIN_VAL}"
  fi
fi

if [[ "${CADDYFILE_TEMPLATE}" == "Caddyfile.domain.assets" ]]; then
  ASSET_DOMAIN_VAL="$(env_file_value ASSET_DOMAIN)"
  if [[ -z "${ASSET_DOMAIN_VAL}" ]]; then
    fail "ASSET_DOMAIN is required when using Caddyfile.domain.assets"
  fi
  if contains_icase "${ASSET_DOMAIN_VAL}" "example.org" || contains_icase "${ASSET_DOMAIN_VAL}" "example.com"; then
    fail "ASSET_DOMAIN appears to be a placeholder: ${ASSET_DOMAIN_VAL}"
  fi
fi

CADDY_ADMIN_BASIC_AUTH_ENABLED="$(env_file_value CADDY_ADMIN_BASIC_AUTH_ENABLED)"
CADDY_ADMIN_BASIC_AUTH_ENABLED="${CADDY_ADMIN_BASIC_AUTH_ENABLED:-0}"
if [[ "${CADDY_ADMIN_BASIC_AUTH_ENABLED}" != "0" && "${CADDY_ADMIN_BASIC_AUTH_ENABLED}" != "1" ]]; then
  fail "CADDY_ADMIN_BASIC_AUTH_ENABLED must be 0 or 1"
fi
require_compose_safe_dollars "CADDY_ADMIN_BASIC_AUTH_HASH"
if [[ "${CADDY_ADMIN_BASIC_AUTH_ENABLED}" == "1" ]]; then
  require_nonempty "CADDY_ADMIN_BASIC_AUTH_USER"
  require_nonempty "CADDY_ADMIN_BASIC_AUTH_HASH"
  if contains_icase "$(env_file_value CADDY_ADMIN_BASIC_AUTH_USER)" "disabled-admin"; then
    fail "CADDY_ADMIN_BASIC_AUTH_USER must be changed from default when basic auth is enabled"
  fi
  CADDY_ADMIN_BASIC_AUTH_HASH_VAL="$(env_file_value CADDY_ADMIN_BASIC_AUTH_HASH)"
  CADDY_ADMIN_BASIC_AUTH_HASH_VAL="${CADDY_ADMIN_BASIC_AUTH_HASH_VAL//\$\$/\$}"
  if [[ "${CADDY_ADMIN_BASIC_AUTH_HASH_VAL}" != \$2* ]]; then
    fail "CADDY_ADMIN_BASIC_AUTH_HASH should be a bcrypt hash (starts with '$2')"
  fi
fi

CADDY_ALLOW_PUBLIC_STAFF_ROUTES="$(env_file_value CADDY_ALLOW_PUBLIC_STAFF_ROUTES)"
CADDY_ALLOW_PUBLIC_STAFF_ROUTES="${CADDY_ALLOW_PUBLIC_STAFF_ROUTES:-0}"
if [[ "${CADDY_ALLOW_PUBLIC_STAFF_ROUTES}" != "0" && "${CADDY_ALLOW_PUBLIC_STAFF_ROUTES}" != "1" ]]; then
  fail "CADDY_ALLOW_PUBLIC_STAFF_ROUTES must be 0 or 1"
fi

if [[ "${CADDYFILE_TEMPLATE}" == "Caddyfile.domain" || "${CADDYFILE_TEMPLATE}" == "Caddyfile.domain.assets" ]]; then
  STAFF_V4="$(env_file_value CADDY_STAFF_IP_ALLOWLIST_V4)"
  STAFF_V6="$(env_file_value CADDY_STAFF_IP_ALLOWLIST_V6)"
  STAFF_V4="${STAFF_V4:-0.0.0.0/0}"
  STAFF_V6="${STAFF_V6:-::/0}"

  if [[ "${STAFF_V4}" == "0.0.0.0/0" && "${STAFF_V6}" == "::/0" ]]; then
    if [[ "${CADDY_ALLOW_PUBLIC_STAFF_ROUTES}" != "1" ]]; then
      fail "Domain mode with open staff allowlists requires CADDY_ALLOW_PUBLIC_STAFF_ROUTES=1 acknowledgement"
    fi
    if [[ "${CADDY_ADMIN_BASIC_AUTH_ENABLED}" != "1" ]]; then
      fail "When CADDY_ALLOW_PUBLIC_STAFF_ROUTES=1, set CADDY_ADMIN_BASIC_AUTH_ENABLED=1"
    fi
  fi
fi

CSP_MODE_VAL="$(env_file_value DJANGO_CSP_MODE)"
CSP_MODE_VAL="${CSP_MODE_VAL:-relaxed}"
case "${CSP_MODE_VAL}" in
  relaxed|report-only|report_only|reportonly|strict)
    ;;
  *)
    fail "DJANGO_CSP_MODE must be one of: relaxed, report-only, strict"
    ;;
esac

SITE_MODE_VAL="$(env_file_value CLASSHUB_SITE_MODE)"
SITE_MODE_VAL="${SITE_MODE_VAL:-normal}"
case "${SITE_MODE_VAL}" in
  normal|read-only|join-only|maintenance|readonly|read_only|joinonly|join_only)
    ;;
  *)
    fail "CLASSHUB_SITE_MODE must be one of normal, read-only, join-only, maintenance"
    ;;
esac

echo "[env-check] OK"
