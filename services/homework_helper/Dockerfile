FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY homework_helper/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY common /app/common
COPY homework_helper /app

EXPOSE 8000

CMD ["bash", "-lc", "if [ \"${RUN_MIGRATIONS_ON_START:-1}\" = \"1\" ]; then python manage.py migrate --noinput; fi; exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${HELPER_GUNICORN_WORKERS:-2} --timeout ${HELPER_GUNICORN_TIMEOUT_SECONDS:-180}"]
