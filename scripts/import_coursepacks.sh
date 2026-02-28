#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Which environment? Let the user specify via COMPOSE_MODE=prod if desired.
COMPOSE_MODE="${COMPOSE_MODE:-prod}"
COMPOSE_DIR="${ROOT_DIR}/compose"
SERVICE="classhub_web"

# The courses we want to instantiate as full Classes
COURSES=(
  "piper_scratch_12_session"
  "scratch_intro_games_code_grade9_6_session"
  "swarm_aesthetics"
)

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml")
else
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml" -f "${COMPOSE_DIR}/docker-compose.override.yml")
fi

echo "[import] Running in ${COMPOSE_MODE} mode"

# Check if docker is available and the container is running
if command -v docker >/dev/null 2>&1; then
  if docker compose "${COMPOSE_ARGS[@]}" ps --services --filter status=running | grep -qx "${SERVICE}"; then
    echo "[import] Found running ${SERVICE} container. Importing..."
    cd "${ROOT_DIR}"
    for course_slug in "${COURSES[@]}"; do
      echo "[import] Importing $course_slug via docker compose..."
      docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
        python3 manage.py import_coursepack --course-slug "${course_slug}" --create-class --replace
    done
    echo "[import] Done!"
    exit 0
  fi
fi

echo "[import] Docker container '${SERVICE}' not found or not running."
echo "[import] Falling back to local python environment..."

if [[ -d "${ROOT_DIR}/.venv" ]]; then
  echo "[import] Activating virtual environment at ${ROOT_DIR}/.venv"
  source "${ROOT_DIR}/.venv/bin/activate"
elif [[ -d "${ROOT_DIR}/services/classhub/.venv" ]]; then
  echo "[import] Activating virtual environment at ${ROOT_DIR}/services/classhub/.venv"
  source "${ROOT_DIR}/services/classhub/.venv/bin/activate"
else
   echo "[import] Warning: No obvious virtual environment found in services/classhub."
   echo "[import] Assuming your current python environment has Django installed."
fi

cd "${ROOT_DIR}/services/classhub"
for course_slug in "${COURSES[@]}"; do
  echo "[import] Importing $course_slug locally..."
  python3 manage.py import_coursepack --course-slug "${course_slug}" --create-class --replace
done

echo "[import] Done!"
