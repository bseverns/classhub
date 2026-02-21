FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY classhub/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY common /app/common
COPY classhub /app

EXPOSE 8000

# Build static assets once so container boot only has to migrate + start gunicorn.
RUN DJANGO_SECRET_KEY=build-time-static-secret-key-aaaaaaaaaaaaaaaa DJANGO_DEBUG=1 \
  python manage.py collectstatic --noinput

# Default keeps Day-1 behavior; set RUN_MIGRATIONS_ON_START=0 once migrations are moved to deploy step.
CMD ["bash", "-lc", "if [ \"${RUN_MIGRATIONS_ON_START:-1}\" = \"1\" ]; then python manage.py migrate --noinput; fi; exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${CLASSHUB_GUNICORN_WORKERS:-2} --timeout ${CLASSHUB_GUNICORN_TIMEOUT_SECONDS:-1200}"]
