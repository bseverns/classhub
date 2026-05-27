#!/usr/bin/env bash
set -euo pipefail

CONTENT_ROOT="${CLASSHUB_CONTENT_ROOT:-/content}"
CONTENT_SEED_ROOT="${CLASSHUB_CONTENT_SEED_ROOT:-/content_seed}"

wait_for_db() {
  echo "Waiting for database to be reachable..."
  local deadline=$((SECONDS + 60))
  until python manage.py shell -c "from django.db import connections; connections['default'].ensure_connection()" >/dev/null 2>&1; do
    if [ $SECONDS -ge $deadline ]; then
      echo "Timeout waiting for database"
      exit 1
    fi
    sleep 2
  done
  echo "Database is reachable."
}

seed_content() {
  if [[ ! -d "${CONTENT_SEED_ROOT}/courses" ]]; then
    return 0
  fi
  # Try to create the directory if it doesn't exist. 
  # If it fails, we check for write permission on the target.
  mkdir -p "${CONTENT_ROOT}/courses" 2>/dev/null || true
  
  if [[ ! -w "${CONTENT_ROOT}/courses" ]]; then
    if [[ -f "${CONTENT_ROOT}/courses/piper_scratch_12_session/course.yaml" ]]; then
        echo "CONTENT_ROOT ${CONTENT_ROOT} is not writable, but course content already exists. Skipping seed."
        return 0
    fi
    echo "Warning: CONTENT_ROOT ${CONTENT_ROOT} is not writable and content is missing. Seeding will likely fail."
    echo "Operator: if using volume mounts, ensure host directory permissions match container UID/GID (${APP_UID:-unknown}:${APP_GID:-unknown})."
  fi

  for seed_course in "${CONTENT_SEED_ROOT}"/courses/*; do
    [[ -d "${seed_course}" ]] || continue
    course_name="$(basename "${seed_course}")"
    if [[ ! -e "${CONTENT_ROOT}/courses/${course_name}" ]]; then
      cp -a "${seed_course}" "${CONTENT_ROOT}/courses/" 2>/dev/null || {
          echo "Warning: Failed to seed course ${course_name} (permission denied)."
      }
    fi
  done
}

wait_for_db
seed_content

if [[ "${RUN_MIGRATIONS_ON_START:-1}" == "1" ]]; then
  python manage.py migrate --noinput
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${CLASSHUB_GUNICORN_WORKERS:-2}" \
  --timeout "${CLASSHUB_GUNICORN_TIMEOUT_SECONDS:-1200}"
