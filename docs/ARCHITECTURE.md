# Architecture

This repo runs a small, self-hosted learning system on one Ubuntu box.

## High level routing

- Caddy terminates HTTP/HTTPS and routes:
  - `/helper/*` → Homework Helper Django service
  - everything else → Class Hub Django service

## Data services

- Postgres: primary database
- Redis: caching + rate limiting + job queues (later)
- MinIO: S3-compatible file storage for uploads

## Code + content packaging

- Production images bake in Django code, templates, and repo-authored curriculum.
- Containers run migrations and `collectstatic` on startup, then serve via Gunicorn.
- Local dev uses a Compose override that bind-mounts source and uses `runserver`
  for hot reload (see `docs/DEVELOPMENT.md`).

## Why two Django services?

We intentionally split the Homework Helper away from the Class Hub:

- A helper outage shouldn’t take down class materials.
- Security boundaries are cleaner (rate limits, logs, prompt policies).
- Later, you can scale the helper independently.

## Mermaid diagram

```mermaid
graph TD
  U[Users] -->|HTTPS| C[Caddy]
  C -->|/helper/*| H[Homework Helper (Django)]
  C -->|/*| W[Class Hub (Django)]
  W --> P[(Postgres)]
  W --> R[(Redis)]
  W --> M[(MinIO)]
  H --> P
  H --> R
  H --> L[Local LLM (Ollama)]
  H -. optional .-> O[OpenAI API]
```
