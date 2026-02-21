#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COURSE_SLUG="demo_classhub_quickstart"
SRC_DIR="${ROOT_DIR}/demo_coursepack/${COURSE_SLUG}"
DST_DIR="${ROOT_DIR}/services/classhub/content/courses/${COURSE_SLUG}"
SRC_REF="${SRC_DIR}/reference.md"
DST_REF="${ROOT_DIR}/services/homework_helper/tutor/reference/${COURSE_SLUG}.md"

COMPOSE_MODE="${COMPOSE_MODE:-dev}" # dev or prod
COMPOSE_DIR="${ROOT_DIR}/compose"
SERVICE="classhub_web"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "[demo] missing source coursepack: ${SRC_DIR}" >&2
  exit 1
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml")
else
  COMPOSE_ARGS=(-f "${COMPOSE_DIR}/docker-compose.yml" -f "${COMPOSE_DIR}/docker-compose.override.yml")
fi

if ! docker compose "${COMPOSE_ARGS[@]}" ps --services --filter status=running | grep -qx "${SERVICE}"; then
  echo "[demo] ${SERVICE} is not running. Start the stack first, then retry." >&2
  echo "[demo] example: docker compose ${COMPOSE_ARGS[*]} up -d --build ${SERVICE}" >&2
  exit 1
fi

echo "[demo] syncing demo coursepack into services/classhub/content/courses"
rm -rf "${DST_DIR}"
mkdir -p "$(dirname "${DST_DIR}")"
cp -R "${SRC_DIR}" "${DST_DIR}"

if [[ -f "${SRC_REF}" ]]; then
  echo "[demo] syncing demo helper reference"
  mkdir -p "$(dirname "${DST_REF}")"
  cp "${SRC_REF}" "${DST_REF}"
fi

echo "[demo] syncing demo coursepack into running classhub container"
docker compose "${COMPOSE_ARGS[@]}" exec -T "${SERVICE}" \
  sh -lc "mkdir -p /app/content/courses && rm -rf /app/content/courses/${COURSE_SLUG}"
docker compose "${COMPOSE_ARGS[@]}" cp "${SRC_DIR}" "${SERVICE}:/app/content/courses/"

if [[ -f "${SRC_REF}" ]]; then
  echo "[demo] syncing demo helper reference into running helper container (best-effort)"
  if docker compose "${COMPOSE_ARGS[@]}" ps --services --filter status=running | grep -qx "helper_web"; then
    docker compose "${COMPOSE_ARGS[@]}" exec -T helper_web \
      sh -lc "mkdir -p /app/tutor/reference"
    docker compose "${COMPOSE_ARGS[@]}" cp "${SRC_REF}" "helper_web:/app/tutor/reference/${COURSE_SLUG}.md"
  else
    echo "[demo] helper_web is not running; skipped container reference sync"
  fi
fi

echo "[demo] importing coursepack into class database"
cd "${ROOT_DIR}"
docker compose "${COMPOSE_ARGS[@]}" exec "${SERVICE}" \
  python manage.py import_coursepack --course-slug "${COURSE_SLUG}" --create-class --replace

CLASS_NAME="Class Hub Demo Quickstart (2 Sessions)"
DEMO_CLASS_CODE="$(docker compose "${COMPOSE_ARGS[@]}" exec -T "${SERVICE}" \
  python manage.py shell -c "from hub.models import Class; c=Class.objects.filter(name='${CLASS_NAME}').order_by('-id').first(); print(c.join_code if c else '')" | tr -d '\r' | tr -d '\n')"

if [[ -z "${DEMO_CLASS_CODE}" ]]; then
  echo "[demo] import completed, but class code lookup failed." >&2
  exit 1
fi

echo "[demo] done"
echo "DEMO_COURSE_SLUG=${COURSE_SLUG}"
echo "DEMO_CLASS_CODE=${DEMO_CLASS_CODE}"
echo "DEMO_LESSON_URL=http://localhost/course/${COURSE_SLUG}/s01-join-and-first-artifact"
