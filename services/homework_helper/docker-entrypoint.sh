#!/usr/bin/env bash
set -euo pipefail

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

wait_for_db

if [ "${RUN_MIGRATIONS_ON_START:-1}" = "1" ]; then
  echo "Running migrations..."
  python manage.py migrate --noinput
fi

if [ "${RUN_REMOTE_COMPUTE_RECONCILE_ON_START:-1}" = "1" ]; then
  echo "Reconciling remote compute state..."
  python manage.py reconcile_remote_compute_state --quiet || true
fi

echo "Starting gunicorn..."
exec gunicorn config.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers "${HELPER_GUNICORN_WORKERS:-2}" \
  --timeout "${HELPER_GUNICORN_TIMEOUT_SECONDS:-180}"
