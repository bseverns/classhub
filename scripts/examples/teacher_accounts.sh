#!/usr/bin/env bash
set -euo pipefail

# Teacher account command cookbook.
#
# Run from repo root:
#   bash scripts/examples/teacher_accounts.sh
#
# Defaults to dry-run (prints commands only). To execute commands:
#   RUN=1 bash scripts/examples/teacher_accounts.sh
#
# Optional:
#   COMPOSE_MODE=prod RUN=1 bash scripts/examples/teacher_accounts.sh
#   USERNAME=teacher2 EMAIL=teacher2@example.org PASSWORD=... NEW_PASSWORD=... RUN=1 bash scripts/examples/teacher_accounts.sh

RUN="${RUN:-0}"
COMPOSE_MODE="${COMPOSE_MODE:-dev}" # dev or prod
COMPOSE_DIR="compose"
SERVICE="classhub_web"

USERNAME="${USERNAME:-teacher1}"
EMAIL="${EMAIL:-teacher1@example.org}"
PASSWORD="${PASSWORD:-CHANGE_ME}"
NEW_PASSWORD="${NEW_PASSWORD:-NEW_PASSWORD}"

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml")
else
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml" -f "${COMPOSE_DIR}/docker-compose.override.yml")
fi

run_cmd() {
  local description="$1"
  shift
  echo "== ${description} =="
  echo "$*"
  if [[ "${RUN}" == "1" ]]; then
    "$@"
  fi
}

run_cmd "Create a staff teacher (non-superuser)" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --email "${EMAIL}" \
    --password "${PASSWORD}"

run_cmd "Reset/update password" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --password "${NEW_PASSWORD}" \
    --update

run_cmd "Disable account" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --inactive \
    --update

run_cmd "Re-enable account" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --active \
    --update

run_cmd "Promote to superuser (optional)" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --superuser \
    --update

run_cmd "Demote from superuser" \
  docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
    python manage.py create_teacher \
    --username "${USERNAME}" \
    --no-superuser \
    --update

if [[ "${RUN}" == "1" ]]; then
  echo "Done."
else
  echo "Dry-run mode (RUN=${RUN}); no commands were executed."
fi
