FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/app

ARG APP_UID=10001
ARG APP_GID=10001

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" --non-unique app \
  && useradd --uid "${APP_UID}" --gid "${APP_GID}" --non-unique --create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY classhub/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY common /tmp/common
RUN pip install --no-cache-dir /tmp/common

COPY classhub /app

EXPOSE 8000

# Build static assets once so container boot only has to migrate + start gunicorn.
# Use production-mode static storage so runtime (DJANGO_DEBUG=0) sees a valid manifest.
RUN DJANGO_SECRET_KEY=build-time-static-secret-key-aaaaaaaaaaaaaaaa \
  DEVICE_HINT_SIGNING_KEY=build-time-device-hint-key-bbbbbbbbbbbbbbbb \
  HELPER_SCOPE_SIGNING_KEY=build-time-helper-scope-key-cccccccccccccccc \
  DJANGO_DEBUG=0 \
  CLASSHUB_USE_MANIFEST_STATICFILES=1 \
  python manage.py collectstatic --noinput

RUN mkdir -p /uploads/authoring_templates /content /content_seed \
  && cp -a /app/content/. /content_seed/ \
  && chmod 755 /app/docker-entrypoint.sh \
  && chown -R app:app /app /uploads /content /content_seed

USER app

CMD ["/app/docker-entrypoint.sh"]
