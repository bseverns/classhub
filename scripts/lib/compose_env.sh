#!/usr/bin/env bash

compose_env_value() {
  local key="$1"
  local env_file="$2"
  local explicit="${!key-}"
  if [[ -n "${explicit}" ]]; then
    echo "${explicit}"
    return 0
  fi
  if [[ ! -f "${env_file}" ]]; then
    echo ""
    return 0
  fi
  local raw
  raw="$(grep -E "^${key}=" "${env_file}" | tail -n1 | cut -d= -f2- || true)"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%\'}"
  raw="${raw#\'}"
  echo "${raw}"
}

_compose_env_url_host() {
  local url="${1:-}"
  local rest host
  rest="${url#*://}"
  rest="${rest%%/*}"
  rest="${rest##*@}"
  host="${rest%%:*}"
  printf '%s\n' "${host}" | tr '[:upper:]' '[:lower:]'
}

_compose_env_is_local_host() {
  local host
  host="$(printf '%s\n' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  [[ -z "${host}" || "${host}" == "localhost" || "${host}" == "127.0.0.1" || "${host}" == "ollama" || "${host}" == "classhub_ollama" ]]
}

llm_backend_name() {
  local env_file="$1"
  local backend
  backend="$(compose_env_value LLM_BACKEND "${env_file}")"
  if [[ -z "${backend}" ]]; then
    backend="$(compose_env_value HELPER_LLM_BACKEND "${env_file}")"
  fi
  backend="${backend:-ollama}"
  printf '%s\n' "${backend}" | tr '[:upper:]' '[:lower:]'
}

llm_backend_base_url() {
  local env_file="$1"
  local backend base_url
  backend="$(llm_backend_name "${env_file}")"
  base_url="$(compose_env_value LLM_BASE_URL "${env_file}")"
  if [[ -z "${base_url}" && "${backend}" == "ollama" ]]; then
    base_url="$(compose_env_value OLLAMA_BASE_URL "${env_file}")"
  fi
  if [[ -z "${base_url}" && "${backend}" == "ollama" ]]; then
    base_url="http://ollama:11434"
  fi
  printf '%s\n' "${base_url}"
}

llm_backend_model() {
  local env_file="$1"
  local backend model
  backend="$(llm_backend_name "${env_file}")"
  model="$(compose_env_value LLM_MODEL "${env_file}")"
  if [[ -z "${model}" && "${backend}" == "ollama" ]]; then
    model="$(compose_env_value OLLAMA_MODEL "${env_file}")"
  fi
  if [[ -z "${model}" && "${backend}" == "ollama" ]]; then
    model="llama3.2:1b"
  fi
  printf '%s\n' "${model}"
}

llm_backend_scope() {
  local env_file="$1"
  local backend host
  backend="$(llm_backend_name "${env_file}")"
  case "${backend}" in
    mock)
      echo "mock"
      return 0
      ;;
    openai|openai_responses)
      echo "remote"
      return 0
      ;;
  esac
  host="$(_compose_env_url_host "$(llm_backend_base_url "${env_file}")")"
  if _compose_env_is_local_host "${host}"; then
    echo "local"
  else
    echo "remote"
  fi
}

llm_uses_local_ollama_compose() {
  local env_file="$1"
  local auto_ollama
  auto_ollama="$(compose_env_value COMPOSE_LOCAL_OLLAMA_AUTO "${env_file}")"
  auto_ollama="${auto_ollama:-1}"
  [[ "${auto_ollama}" != "0" && "$(llm_backend_name "${env_file}")" == "ollama" && "$(llm_backend_scope "${env_file}")" == "local" ]]
}

llm_check_mode_auto() {
  local env_file="$1"
  local scope
  scope="$(llm_backend_scope "${env_file}")"
  if [[ "${scope}" == "remote" ]]; then
    echo "advisory"
  elif [[ "${scope}" == "mock" ]]; then
    echo "off"
  else
    echo "required"
  fi
}

helper_smoke_mode_auto() {
  local env_file="$1"
  local scope
  scope="$(llm_backend_scope "${env_file}")"
  if [[ "${scope}" == "remote" ]]; then
    echo "advisory"
  else
    echo "required"
  fi
}
