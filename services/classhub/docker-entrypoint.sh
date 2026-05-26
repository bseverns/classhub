#!/usr/bin/env bash
set -euo pipefail

CONTENT_ROOT="${CLASSHUB_CONTENT_ROOT:-/app/content}"
CONTENT_SEED_ROOT="${CLASSHUB_CONTENT_SEED_ROOT:-/content_seed}"

seed_content() {
  if [[ ! -d "${CONTENT_SEED_ROOT}/courses" ]]; then
    return 0
  fi
  mkdir -p "${CONTENT_ROOT}/courses"
  for seed_course in "${CONTENT_SEED_ROOT}"/courses/*; do
    [[ -d "${seed_course}" ]] || continue
    course_name="$(basename "${seed_course}")"
    if [[ ! -e "${CONTENT_ROOT}/courses/${course_name}" ]]; then
      cp -a "${seed_course}" "${CONTENT_ROOT}/courses/${course_name}"
    fi
  done
}

seed_content

if [[ "${RUN_MIGRATIONS_ON_START:-1}" == "1" ]]; then
  python manage.py migrate --noinput
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${CLASSHUB_GUNICORN_WORKERS:-2}" \
  --timeout "${CLASSHUB_GUNICORN_TIMEOUT_SECONDS:-1200}"
