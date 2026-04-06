#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="${ROOT_DIR}/compose"
ENV_FILE="${COMPOSE_DIR}/.env"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"
COMPOSE_ENV_LIB="${ROOT_DIR}/scripts/lib/compose_env.sh"

MODE=""
HELPER_BACKEND=""
WITH_ADMIN=""
WITH_DEMO=""
WITH_DOCTOR=""
NON_INTERACTIVE=0
ADMIN_USERNAME="${ADMIN_USERNAME:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

log() { echo -e "\n[quickstart] $*\n"; }
warn() { echo -e "\n[quickstart][warn] $*\n" >&2; }
die() { echo -e "\n[quickstart][error] $*\n" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Usage: bash scripts/quickstart_stack.sh [options]

Options:
  --mode <local|domain>         Stack mode (default: local)
  --helper-backend <name>       Helper backend (default: ollama)
  --with-admin                  Create/update Django superuser
  --without-admin               Skip superuser setup
  --admin-username <value>      Superuser username (with --with-admin)
  --admin-email <value>         Superuser email (with --with-admin)
  --admin-password <value>      Superuser password (with --with-admin)
  --with-demo                   Load demo coursepack (default: yes)
  --without-demo                Skip demo load
  --with-doctor                 Run system doctor at end (default: yes)
  --without-doctor              Skip system doctor
  --yes                         Non-interactive defaults
  -h, --help                    Show this help
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "missing required command: $1"
  fi
}

is_placeholder_value() {
  local value="${1:-}"
  [[ -z "${value}" || "${value}" == REPLACE_ME* || "${value}" == __SET_ME__* || "${value}" == CHANGE_ME* ]]
}

env_get() {
  local key="$1"
  local file="$2"
  awk -F= -v key="${key}" '
    $1 == key {
      print substr($0, index($0, "=") + 1)
    }
  ' "${file}" | tail -n 1
}

env_set() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp
  tmp="$(mktemp)"
  awk -v key="${key}" -v value="${value}" '
    BEGIN { done = 0 }
    $0 ~ ("^" key "=") {
      if (done == 0) {
        print key "=" value
        done = 1
      }
      next
    }
    { print }
    END {
      if (done == 0) {
        print key "=" value
      }
    }
  ' "${file}" > "${tmp}"
  mv "${tmp}" "${file}"
}

prompt_default() {
  local message="$1"
  local default="$2"
  local input
  if [[ "${NON_INTERACTIVE}" == "1" ]]; then
    echo "${default}"
    return
  fi
  read -r -p "${message} [${default}]: " input
  if [[ -z "${input}" ]]; then
    echo "${default}"
  else
    echo "${input}"
  fi
}

prompt_yes_no() {
  local message="$1"
  local default="$2"
  local answer
  if [[ "${NON_INTERACTIVE}" == "1" ]]; then
    echo "${default}"
    return
  fi
  read -r -p "${message} [${default}] (y/n): " answer
  if [[ -z "${answer}" ]]; then
    answer="${default}"
  fi
  case "$(echo "${answer}" | tr '[:upper:]' '[:lower:]')" in
    y|yes) echo "yes" ;;
    n|no) echo "no" ;;
    *) echo "${default}" ;;
  esac
}

generate_secret() {
  openssl rand -hex 32
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)
        MODE="${2:-}"
        shift 2
        ;;
      --helper-backend)
        HELPER_BACKEND="${2:-}"
        shift 2
        ;;
      --with-admin)
        WITH_ADMIN="yes"
        shift
        ;;
      --without-admin)
        WITH_ADMIN="no"
        shift
        ;;
      --admin-username)
        ADMIN_USERNAME="${2:-}"
        shift 2
        ;;
      --admin-email)
        ADMIN_EMAIL="${2:-}"
        shift 2
        ;;
      --admin-password)
        ADMIN_PASSWORD="${2:-}"
        shift 2
        ;;
      --with-demo)
        WITH_DEMO="yes"
        shift
        ;;
      --without-demo)
        WITH_DEMO="no"
        shift
        ;;
      --with-doctor)
        WITH_DOCTOR="yes"
        shift
        ;;
      --without-doctor)
        WITH_DOCTOR="no"
        shift
        ;;
      --yes)
        NON_INTERACTIVE=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done
}

choose_defaults() {
  MODE="${MODE:-$(prompt_default "Choose mode" "local")}"
  case "${MODE}" in
    local|domain) ;;
    *) die "mode must be 'local' or 'domain'" ;;
  esac

  if [[ -z "${HELPER_BACKEND}" ]]; then
    HELPER_BACKEND="ollama"
  fi

  WITH_ADMIN="${WITH_ADMIN:-$(prompt_yes_no "Create/update admin account?" "yes")}"
  WITH_DEMO="${WITH_DEMO:-$(prompt_yes_no "Load demo coursepack?" "yes")}"
  WITH_DOCTOR="${WITH_DOCTOR:-$(prompt_yes_no "Run system doctor checks?" "yes")}"

  if [[ "${WITH_ADMIN}" == "yes" ]]; then
    ADMIN_USERNAME="${ADMIN_USERNAME:-$(prompt_default "Admin username" "admin")}"
    ADMIN_EMAIL="${ADMIN_EMAIL:-$(prompt_default "Admin email" "admin@example.org")}"
    if [[ -z "${ADMIN_PASSWORD}" && "${NON_INTERACTIVE}" == "0" ]]; then
      read -r -s -p "Admin password: " ADMIN_PASSWORD
      echo
    fi
  fi
}

prepare_env_file() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    local source_env
    if [[ "${MODE}" == "local" ]]; then
      source_env="${COMPOSE_DIR}/.env.example.local"
    else
      source_env="${COMPOSE_DIR}/.env.example.domain"
    fi
    cp "${source_env}" "${ENV_FILE}"
    log "created compose/.env from $(basename "${source_env}")"
  else
    log "using existing compose/.env"
  fi

  if [[ "${MODE}" == "local" ]]; then
    env_set "CADDYFILE_TEMPLATE" "Caddyfile.local" "${ENV_FILE}"
    env_set "DJANGO_SESSION_COOKIE_SECURE" "0" "${ENV_FILE}"
    env_set "DJANGO_CSRF_COOKIE_SECURE" "0" "${ENV_FILE}"
    env_set "CSRF_TRUSTED_ORIGINS" "http://localhost" "${ENV_FILE}"
    env_set "DJANGO_ALLOWED_HOSTS" "localhost,127.0.0.1" "${ENV_FILE}"
  else
    env_set "CADDYFILE_TEMPLATE" "Caddyfile.domain" "${ENV_FILE}"
    if is_placeholder_value "$(env_get "DOMAIN" "${ENV_FILE}")"; then
      local domain_value
      domain_value="$(prompt_default "Domain for production mode" "lms.example.org")"
      env_set "DOMAIN" "${domain_value}" "${ENV_FILE}"
    fi
  fi

  env_set "HELPER_LLM_BACKEND" "${HELPER_BACKEND}" "${ENV_FILE}"
  env_set "LLM_BACKEND" "${HELPER_BACKEND}" "${ENV_FILE}"
  env_set "HELPER_CONFIG_FILE" "/app/config/helper.config.yaml" "${ENV_FILE}"
  env_set "COMPOSE_LOCAL_OLLAMA_AUTO" "1" "${ENV_FILE}"
  if [[ "${HELPER_BACKEND}" == "ollama" ]]; then
    env_set "LLM_BASE_URL" "http://ollama:11434" "${ENV_FILE}"
    env_set "OLLAMA_BASE_URL" "http://ollama:11434" "${ENV_FILE}"
  fi
  if [[ "${HELPER_BACKEND}" == "mock" ]]; then
    if is_placeholder_value "$(env_get "HELPER_MOCK_RESPONSE_TEXT" "${ENV_FILE}")"; then
      env_set "HELPER_MOCK_RESPONSE_TEXT" "Let's work one step at a time. What did you try first?" "${ENV_FILE}"
    fi
  fi
}

seed_required_secrets() {
  local keys=(
    "POSTGRES_PASSWORD"
    "MINIO_ROOT_PASSWORD"
    "DJANGO_SECRET_KEY"
    "DEVICE_HINT_SIGNING_KEY"
    "HELPER_SCOPE_SIGNING_KEY"
    "HELPER_INTERNAL_API_TOKEN"
    "CLASSHUB_INTERNAL_EVENTS_TOKEN"
  )
  local key current
  for key in "${keys[@]}"; do
    current="$(env_get "${key}" "${ENV_FILE}")"
    if is_placeholder_value "${current}"; then
      env_set "${key}" "$(generate_secret)" "${ENV_FILE}"
      log "generated ${key}"
    fi
  done
}

run_compose() {
  local compose_args=(-f "${COMPOSE_FILE}")
  if [[ -f "${COMPOSE_ENV_LIB}" ]]; then
    # shellcheck disable=SC1090
    source "${COMPOSE_ENV_LIB}"
    if llm_uses_local_ollama_compose "${ENV_FILE}"; then
      compose_args+=(--profile local-ollama)
    fi
  fi
  docker compose "${compose_args[@]}" "$@"
}

create_or_update_admin() {
  if [[ "${WITH_ADMIN}" != "yes" ]]; then
    return
  fi
  if [[ -z "${ADMIN_USERNAME}" || -z "${ADMIN_EMAIL}" || -z "${ADMIN_PASSWORD}" ]]; then
    warn "admin fields missing; skipping admin bootstrap"
    return
  fi

  log "creating/updating admin account ${ADMIN_USERNAME}"
  run_compose exec -T \
    -e DJANGO_SUPERUSER_USERNAME="${ADMIN_USERNAME}" \
    -e DJANGO_SUPERUSER_EMAIL="${ADMIN_EMAIL}" \
    -e DJANGO_SUPERUSER_PASSWORD="${ADMIN_PASSWORD}" \
    classhub_web \
    python manage.py shell -c \
      "import os; U=__import__('django.contrib.auth').contrib.auth.get_user_model(); u=os.environ['DJANGO_SUPERUSER_USERNAME']; e=os.environ['DJANGO_SUPERUSER_EMAIL']; p=os.environ['DJANGO_SUPERUSER_PASSWORD']; obj, created = U.objects.get_or_create(username=u, defaults={'email': e, 'is_staff': True, 'is_superuser': True, 'is_active': True}); obj.email = e; obj.is_staff = True; obj.is_superuser = True; obj.is_active = True; obj.set_password(p); obj.save(); print('created' if created else 'updated')"
}

main() {
  parse_args "$@"
  require_cmd docker
  require_cmd openssl

  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    die "missing compose file: ${COMPOSE_FILE}"
  fi

  choose_defaults
  prepare_env_file
  seed_required_secrets

  log "starting stack (docker compose up -d --build)"
  run_compose up -d --build

  log "ensuring local ollama model is ready"
  bash "${ROOT_DIR}/scripts/ensure_local_ollama_model.sh"

  log "running Django migrations"
  run_compose exec -T classhub_web python manage.py migrate --noinput
  run_compose exec -T helper_web python manage.py migrate --noinput

  create_or_update_admin

  if [[ "${WITH_DEMO}" == "yes" ]]; then
    log "loading demo coursepack"
    bash "${ROOT_DIR}/scripts/load_demo_coursepack.sh"
  fi

  if [[ "${WITH_DOCTOR}" == "yes" ]]; then
    log "running system doctor"
    bash "${ROOT_DIR}/scripts/system_doctor.sh" --smoke-mode golden
  fi

  log "done"
  echo "Student join: http://localhost/"
  echo "Teacher login: http://localhost/admin/login/"
  echo "Teacher portal: http://localhost/teach"
  echo "Health: http://localhost/healthz and http://localhost/helper/healthz"
}

main "$@"
