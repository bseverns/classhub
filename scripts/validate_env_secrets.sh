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

require_matching_values_if_both_set() {
  local left_key="$1"
  local right_key="$2"
  local left_value right_value
  left_value="$(env_file_value "${left_key}")"
  right_value="$(env_file_value "${right_key}")"
  if [[ -n "${left_value}" && -n "${right_value}" && "${left_value}" != "${right_value}" ]]; then
    fail "${left_key} and ${right_key} must match when both are set"
  fi
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

normalize_mode() {
  local raw="$1"
  local normalized
  normalized="$(to_lower "${raw}")"
  normalized="${normalized//-/_}"
  echo "${normalized}"
}

trim_spaces() {
  local raw="$1"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  printf '%s' "${raw}"
}

url_host() {
  local url="$1"
  local without_scheme
  without_scheme="${url#*://}"
  without_scheme="${without_scheme%%/*}"
  without_scheme="${without_scheme%%\?*}"
  without_scheme="${without_scheme%%#*}"
  printf '%s' "${without_scheme%%:*}"
}

is_local_llm_url() {
  local host
  host="$(to_lower "$(url_host "$1")")"
  case "${host}" in
    ""|localhost|127.0.0.1|ollama|classhub_ollama)
      return 0
      ;;
  esac
  return 1
}

contains_icase() {
  local haystack="$1"
  local needle="$2"
  local haystack_lower
  local needle_lower
  haystack_lower="$(to_lower "${haystack}")"
  needle_lower="$(to_lower "${needle}")"
  if [[ "${haystack_lower}" == *"${needle_lower}"* ]]; then
    return 0
  fi
  return 1
}

is_unsafe_secret() {
  local v="$1"
  local lower
  lower="$(to_lower "${v}")"

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
  require_strong_secret "HELPER_SCOPE_SIGNING_KEY" 32
  require_distinct_values "DJANGO_SECRET_KEY" "DEVICE_HINT_SIGNING_KEY"
  require_distinct_values "DJANGO_SECRET_KEY" "HELPER_SCOPE_SIGNING_KEY"
  require_strong_secret "CLASSHUB_INTERNAL_EVENTS_TOKEN" 16
  require_strong_secret "HELPER_INTERNAL_API_TOKEN" 16
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

CADDYFILE_TEMPLATE="$(env_file_value CADDYFILE_TEMPLATE)"
SMOKE_BASE_URL="$(env_file_value SMOKE_BASE_URL)"
DJANGO_SESSION_COOKIE_SECURE="$(env_file_value DJANGO_SESSION_COOKIE_SECURE)"
DJANGO_CSRF_COOKIE_SECURE="$(env_file_value DJANGO_CSRF_COOKIE_SECURE)"
if [[ "${CADDYFILE_TEMPLATE}" == "Caddyfile.local" || "${SMOKE_BASE_URL}" == http://* ]]; then
  if [[ "${DJANGO_SESSION_COOKIE_SECURE}" != "0" ]]; then
    fail "DJANGO_SESSION_COOKIE_SECURE must be 0 for local HTTP mode (Caddyfile.local / SMOKE_BASE_URL=http://...)"
  fi
  if [[ "${DJANGO_CSRF_COOKIE_SECURE}" != "0" ]]; then
    fail "DJANGO_CSRF_COOKIE_SECURE must be 0 for local HTTP mode (Caddyfile.local / SMOKE_BASE_URL=http://...)"
  fi
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

LLM_ENABLED="$(env_file_value LLM_ENABLED)"
LLM_ENABLED="${LLM_ENABLED:-1}"
LLM_LOG_PROMPT_CONTENT="$(env_file_value LLM_LOG_PROMPT_CONTENT)"
LLM_LOG_PROMPT_CONTENT="${LLM_LOG_PROMPT_CONTENT:-0}"
LLM_REDACTION_ENABLED="$(env_file_value LLM_REDACTION_ENABLED)"
LLM_REDACTION_ENABLED="${LLM_REDACTION_ENABLED:-1}"
HELPER_LLM_BACKEND="$(env_file_value LLM_BACKEND)"
if [[ -z "${HELPER_LLM_BACKEND}" ]]; then
  HELPER_LLM_BACKEND="$(env_file_value HELPER_LLM_BACKEND)"
fi
HELPER_LLM_BACKEND_LOWER="$(to_lower "${HELPER_LLM_BACKEND}")"
require_matching_values_if_both_set "LLM_BACKEND" "HELPER_LLM_BACKEND"
require_matching_values_if_both_set "LLM_BASE_URL" "OLLAMA_BASE_URL"
require_matching_values_if_both_set "LLM_MODEL" "OLLAMA_MODEL"
require_matching_values_if_both_set "LLM_TIMEOUT_SECONDS" "OLLAMA_TIMEOUT_SECONDS"
if [[ "${DJANGO_DEBUG}" == "0" && "${LLM_ENABLED}" == "1" && "${LLM_LOG_PROMPT_CONTENT}" == "1" ]]; then
  fail "LLM_LOG_PROMPT_CONTENT must remain 0 when DJANGO_DEBUG=0"
fi
if [[ "${DJANGO_DEBUG}" == "0" && "${LLM_ENABLED}" == "1" && "${LLM_REDACTION_ENABLED}" != "1" ]]; then
  fail "LLM_REDACTION_ENABLED must be 1 when DJANGO_DEBUG=0"
fi
if [[ "${HELPER_LLM_BACKEND_LOWER}" == "openai" || "${HELPER_LLM_BACKEND_LOWER}" == "openai_responses" ]]; then
  require_strong_secret "OPENAI_API_KEY" 20
fi
if [[ "${LLM_ENABLED}" == "1" && "${HELPER_LLM_BACKEND_LOWER}" == "openai_compatible" ]]; then
  require_nonempty "LLM_BASE_URL"
  require_nonempty "LLM_MODEL"
  require_strong_secret "LLM_API_KEY" 20
fi
if [[ "${LLM_ENABLED}" == "1" && "${HELPER_LLM_BACKEND_LOWER}" == "ollama" ]]; then
  LLM_OLLAMA_BASE_URL="$(env_file_value LLM_BASE_URL)"
  if [[ -z "${LLM_OLLAMA_BASE_URL}" ]]; then
    LLM_OLLAMA_BASE_URL="$(env_file_value OLLAMA_BASE_URL)"
  fi
  if [[ -z "${LLM_OLLAMA_BASE_URL}" ]]; then
    fail "LLM_BASE_URL or OLLAMA_BASE_URL is required when HELPER_LLM_BACKEND/LLM_BACKEND=ollama"
  fi
  LLM_OLLAMA_MODEL="$(env_file_value LLM_MODEL)"
  if [[ -z "${LLM_OLLAMA_MODEL}" ]]; then
    LLM_OLLAMA_MODEL="$(env_file_value OLLAMA_MODEL)"
  fi
  if [[ -z "${LLM_OLLAMA_MODEL}" ]]; then
    fail "LLM_MODEL or OLLAMA_MODEL is required when HELPER_LLM_BACKEND/LLM_BACKEND=ollama"
  fi
  HELPER_REMOTE_MODE_ACKNOWLEDGED="$(env_file_value HELPER_REMOTE_MODE_ACKNOWLEDGED)"
  if [[ -z "${HELPER_REMOTE_MODE_ACKNOWLEDGED}" ]]; then
    HELPER_REMOTE_MODE_ACKNOWLEDGED="$(env_file_value CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED)"
  fi
  HELPER_REMOTE_MODE_ACKNOWLEDGED="${HELPER_REMOTE_MODE_ACKNOWLEDGED:-0}"
  if [[ "${DJANGO_DEBUG}" == "0" ]] && ! is_local_llm_url "${LLM_OLLAMA_BASE_URL}"; then
    if [[ "${HELPER_REMOTE_MODE_ACKNOWLEDGED}" != "1" ]]; then
      fail "HELPER_REMOTE_MODE_ACKNOWLEDGED must be 1 for a private remote Ollama path in production"
    fi
    if [[ "${LLM_OLLAMA_BASE_URL}" != https://* ]]; then
      fail "Private remote Ollama must use HTTPS for production helper traffic"
    fi
    LLM_OLLAMA_API_KEY="$(env_file_value LLM_API_KEY)"
    if [[ -z "${LLM_OLLAMA_API_KEY}" ]]; then
      LLM_OLLAMA_API_KEY="$(env_file_value OLLAMA_API_KEY)"
    fi
    if [[ -z "${LLM_OLLAMA_API_KEY}" ]]; then
      fail "LLM_API_KEY or OLLAMA_API_KEY is required for a private remote Ollama path in production"
    fi
    if [[ "${#LLM_OLLAMA_API_KEY}" -lt 20 ]] || is_unsafe_secret "${LLM_OLLAMA_API_KEY}"; then
      fail "LLM_API_KEY or OLLAMA_API_KEY must be a strong shared secret for a private remote Ollama path in production"
    fi
  fi
fi

HELPER_REMOTE_COMPUTE_ENABLED="$(env_file_value HELPER_REMOTE_COMPUTE_ENABLED)"
if [[ -z "${HELPER_REMOTE_COMPUTE_ENABLED}" ]]; then
  HELPER_REMOTE_COMPUTE_ENABLED="$(env_file_value CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED)"
fi
HELPER_REMOTE_COMPUTE_ENABLED="${HELPER_REMOTE_COMPUTE_ENABLED:-0}"
if [[ "$(to_lower "${HELPER_REMOTE_COMPUTE_ENABLED}")" == "1" || "$(to_lower "${HELPER_REMOTE_COMPUTE_ENABLED}")" == "true" ]]; then
  require_nonempty "REMOTE_LLM_BASE_URL"
  require_nonempty "REMOTE_LLM_API_KEY"
  require_nonempty "REMOTE_LLM_MODEL"
  require_nonempty "HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER"
  require_nonempty "HELPER_REMOTE_COMPUTE_ACTIVATE_URL"
  require_nonempty "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL"
  require_nonempty "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL"
  require_nonempty "HELPER_INTERNAL_REMOTE_COMPUTE_CONTROL_URL"
  require_strong_secret "HELPER_REMOTE_COMPUTE_CONTROL_API_KEY" 20
  if [[ "${DJANGO_DEBUG}" == "0" && "$(env_file_value REMOTE_LLM_BASE_URL)" != https://* ]]; then
    fail "REMOTE_LLM_BASE_URL must use HTTPS when HELPER_REMOTE_COMPUTE_ENABLED=1 in production"
  fi
  if [[ "${DJANGO_DEBUG}" == "0" && "${HELPER_REMOTE_MODE_ACKNOWLEDGED}" != "1" ]]; then
    fail "HELPER_REMOTE_MODE_ACKNOWLEDGED must be 1 when HELPER_REMOTE_COMPUTE_ENABLED=1 in production"
  fi
fi

TELEMETRY_WRITE_MODE="$(normalize_mode "$(env_file_value CLASSHUB_TELEMETRY_WRITE_MODE)")"
TELEMETRY_WRITE_MODE="${TELEMETRY_WRITE_MODE:-off}"
case "${TELEMETRY_WRITE_MODE}" in
  off|dual|telemetry_only)
    ;;
  *)
    fail "CLASSHUB_TELEMETRY_WRITE_MODE must be one of: off, dual, telemetry_only"
    ;;
esac

TELEMETRY_READ_MODE="$(normalize_mode "$(env_file_value CLASSHUB_TELEMETRY_READ_MODE)")"
TELEMETRY_READ_MODE="${TELEMETRY_READ_MODE:-core}"
case "${TELEMETRY_READ_MODE}" in
  core|telemetry)
    ;;
  *)
    fail "CLASSHUB_TELEMETRY_READ_MODE must be one of: core, telemetry"
    ;;
esac

TELEMETRY_DATABASE_URL="$(env_file_value CLASSHUB_TELEMETRY_DATABASE_URL)"
if [[ "${TELEMETRY_WRITE_MODE}" != "off" || "${TELEMETRY_READ_MODE}" == "telemetry" ]]; then
  if [[ -z "${TELEMETRY_DATABASE_URL}" ]]; then
    fail "CLASSHUB_TELEMETRY_DATABASE_URL is required when telemetry write mode is not 'off' or read mode is 'telemetry'"
  fi
fi

TEACHER_SSO_ENABLED="$(env_file_value CLASSHUB_TEACHER_SSO_ENABLED)"
TEACHER_SSO_ENABLED="${TEACHER_SSO_ENABLED:-0}"
if [[ "${TEACHER_SSO_ENABLED}" != "0" && "${TEACHER_SSO_ENABLED}" != "1" ]]; then
  fail "CLASSHUB_TEACHER_SSO_ENABLED must be 0 or 1"
fi

TEACHER_SSO_ALLOW_PASSWORD_FALLBACK="$(env_file_value CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK)"
TEACHER_SSO_ALLOW_PASSWORD_FALLBACK="${TEACHER_SSO_ALLOW_PASSWORD_FALLBACK:-1}"
if [[ "${TEACHER_SSO_ALLOW_PASSWORD_FALLBACK}" != "0" && "${TEACHER_SSO_ALLOW_PASSWORD_FALLBACK}" != "1" ]]; then
  fail "CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK must be 0 or 1"
fi

TEACHER_SSO_STATE_MAX_AGE_RAW="$(env_file_value CLASSHUB_TEACHER_SSO_STATE_MAX_AGE_SECONDS)"
if [[ -n "${TEACHER_SSO_STATE_MAX_AGE_RAW}" ]]; then
  if ! [[ "${TEACHER_SSO_STATE_MAX_AGE_RAW}" =~ ^[0-9]+$ ]]; then
    fail "CLASSHUB_TEACHER_SSO_STATE_MAX_AGE_SECONDS must be a positive integer when set"
  fi
  if [[ "${TEACHER_SSO_STATE_MAX_AGE_RAW}" -lt 60 ]]; then
    fail "CLASSHUB_TEACHER_SSO_STATE_MAX_AGE_SECONDS must be >= 60"
  fi
fi

if [[ "${TEACHER_SSO_ENABLED}" == "1" ]]; then
  SSO_PROVIDERS_RAW="$(env_file_value CLASSHUB_TEACHER_SSO_PROVIDERS)"
  if [[ -z "${SSO_PROVIDERS_RAW}" ]]; then
    fail "CLASSHUB_TEACHER_SSO_PROVIDERS is required when CLASSHUB_TEACHER_SSO_ENABLED=1"
  fi

  declare -A seen_sso_provider=()
  enabled_provider_count=0
  IFS=',' read -r -a sso_provider_items <<< "${SSO_PROVIDERS_RAW}"
  for provider_item in "${sso_provider_items[@]}"; do
    provider="$(normalize_mode "$(trim_spaces "${provider_item}")")"
    if [[ -z "${provider}" ]]; then
      continue
    fi
    if [[ -n "${seen_sso_provider["${provider}"]+x}" ]]; then
      continue
    fi
    seen_sso_provider["${provider}"]=1
    enabled_provider_count=$((enabled_provider_count + 1))
    case "${provider}" in
      google)
        require_nonempty "CLASSHUB_SSO_GOOGLE_CLIENT_ID"
        require_nonempty "CLASSHUB_SSO_GOOGLE_CLIENT_SECRET"
        ;;
      microsoft)
        require_nonempty "CLASSHUB_SSO_MICROSOFT_CLIENT_ID"
        require_nonempty "CLASSHUB_SSO_MICROSOFT_CLIENT_SECRET"
        ;;
      oidc_custom)
        require_nonempty "CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_ID"
        require_nonempty "CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_SECRET"
        require_nonempty "CLASSHUB_SSO_OIDC_CUSTOM_ISSUER"
        require_nonempty "CLASSHUB_SSO_OIDC_CUSTOM_DISCOVERY_URL"
        ;;
      *)
        fail "CLASSHUB_TEACHER_SSO_PROVIDERS contains unsupported provider '${provider}' (allowed: google,microsoft,oidc_custom)"
        ;;
    esac
  done

  if [[ "${enabled_provider_count}" -le 0 ]]; then
    fail "CLASSHUB_TEACHER_SSO_PROVIDERS must include at least one provider when CLASSHUB_TEACHER_SSO_ENABLED=1"
  fi
fi

HELPER_GUNICORN_TIMEOUT_SECONDS="$(number_or_default "$(env_file_value HELPER_GUNICORN_TIMEOUT_SECONDS)" "180")"
HELPER_BACKEND_MAX_ATTEMPTS="$(int_or_default "$(env_file_value HELPER_BACKEND_MAX_ATTEMPTS)" "2")"
if [[ "${HELPER_BACKEND_MAX_ATTEMPTS}" -lt 1 ]]; then
  HELPER_BACKEND_MAX_ATTEMPTS=1
fi
OLLAMA_TIMEOUT_SECONDS="$(number_or_default "$(env_file_value LLM_TIMEOUT_SECONDS)" "$(number_or_default "$(env_file_value OLLAMA_TIMEOUT_SECONDS)" "30")")"
HELPER_QUEUE_MAX_WAIT_SECONDS="$(number_or_default "$(env_file_value HELPER_QUEUE_MAX_WAIT_SECONDS)" "10")"
HELPER_BACKOFF_SECONDS="$(number_or_default "$(env_file_value HELPER_BACKOFF_SECONDS)" "0.4")"

if [[ "${HELPER_LLM_BACKEND_LOWER}" == "ollama" ]]; then
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
CADDY_EXPOSE_UPSTREAM_HEALTHZ="$(env_file_value CADDY_EXPOSE_UPSTREAM_HEALTHZ)"
CADDY_EXPOSE_UPSTREAM_HEALTHZ="${CADDY_EXPOSE_UPSTREAM_HEALTHZ:-}"
if [[ -n "${CADDY_EXPOSE_UPSTREAM_HEALTHZ}" && "${CADDY_EXPOSE_UPSTREAM_HEALTHZ}" != "0" && "${CADDY_EXPOSE_UPSTREAM_HEALTHZ}" != "1" ]]; then
  fail "CADDY_EXPOSE_UPSTREAM_HEALTHZ must be 0 or 1 when set"
fi
CADDY_READ_ONLY="$(env_file_value CADDY_READ_ONLY)"
CADDY_READ_ONLY="${CADDY_READ_ONLY:-false}"
case "${CADDY_READ_ONLY}" in
  0|1|true|false) ;;
  *)
    fail "CADDY_READ_ONLY must be one of: true, false, 0, 1"
    ;;
esac
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
  if [[ "${CADDY_ADMIN_BASIC_AUTH_HASH_VAL}" == '$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG' ]]; then
    fail "CADDY_ADMIN_BASIC_AUTH_HASH must be changed from default when basic auth is enabled"
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
