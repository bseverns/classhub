#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_MODE="${COMPOSE_MODE:-prod}" # prod or dev
KEEPDB="${KEEPDB:-1}" # 1 to speed local reruns

DEFAULT_TARGETS=(
  "hub.tests.test_teacher_admin_auth"
  "hub.tests.test_teacher_admin_portal"
  "hub.tests.test_teacher_admin_release"
)

usage() {
  cat <<'EOF'
Usage: bash scripts/test_teacher_admin.sh [test_target ...]

Runs teacher/admin focused ClassHub tests inside classhub_web.

Environment:
  COMPOSE_MODE=prod|dev   Compose files to use (default: prod)
  KEEPDB=1|0              Reuse test DB between runs (default: 1)

Examples:
  bash scripts/test_teacher_admin.sh
  bash scripts/test_teacher_admin.sh hub.tests.TeacherPortalTests
  COMPOSE_MODE=dev KEEPDB=0 bash scripts/test_teacher_admin.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[teacher-admin-tests] docker is required" >&2
  exit 1
fi

if [[ "${COMPOSE_MODE}" == "prod" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml")
elif [[ "${COMPOSE_MODE}" == "dev" ]]; then
  COMPOSE_ARGS=(-f "${ROOT_DIR}/compose/docker-compose.yml" -f "${ROOT_DIR}/compose/docker-compose.override.yml")
else
  echo "[teacher-admin-tests] invalid COMPOSE_MODE='${COMPOSE_MODE}' (expected prod|dev)" >&2
  exit 1
fi

run_compose() {
  docker compose "${COMPOSE_ARGS[@]}" "$@"
}

if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
else
  TARGETS=("${DEFAULT_TARGETS[@]}")
fi

TEST_ARGS=("${TARGETS[@]}")
if [[ "${KEEPDB}" == "1" ]]; then
  TEST_ARGS+=("--keepdb")
fi

echo "[teacher-admin-tests] compose mode: ${COMPOSE_MODE}"
echo "[teacher-admin-tests] targets: ${TARGETS[*]}"
run_compose exec -T classhub_web python manage.py test "${TEST_ARGS[@]}"
