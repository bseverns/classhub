# Self‑Hosted Class Hub + Homework Helper (Django)

A lightweight, self-hosted learning portal inspired by the needs that surfaced around TailorEDU-style workflows — but built to be **reliable, inspectable, and owned by your org**.

This repo is intentionally *Day‑1 shippable*: it boots on a single Ubuntu server using Docker Compose and gives you:

- **Class Hub** (Django): class-code student access, teacher/admin management via Django admin, class materials pages.
- **Homework Helper** (Django): separate service behind `/helper/*` using OpenAI **Responses API**.
- **Postgres + Redis + MinIO + Caddy**: boring infrastructure you can trust.

> Philosophy: keep the system legible. Logs you can read. Deploys you can repeat. Features that don’t hide in someone else’s cloud.

## Quick start (local / no domain yet)

1) Copy env template:

```bash
cp compose/.env.example compose/.env
# Set OPENAI_API_KEY when ready (helper will error without it)
```

2) Run the stack:

```bash
cd compose
docker compose up -d --build
```

3) Check health:

- Class Hub: `http://localhost/healthz`
- Helper: `http://localhost/helper/healthz`

4) Create a teacher/admin:

```bash
cd compose
docker compose exec classhub_web python manage.py createsuperuser
```

5) Visit:

- Admin: `http://localhost/admin/`
- Student join page: `http://localhost/`

## Production (with a domain)

See:
- `docs/DAY1_DEPLOY_CHECKLIST.md`
- `docs/BOOTSTRAP_SERVER.md`

## What’s next

- Add content authoring UI (beyond admin)
- Add RAG over class materials (pgvector) and citations in helper
- Add optional “return code” for students who clear cookies
- Add Google SSO for teachers (student access can remain class-code)

## Repository map

- `compose/` – Docker Compose + Caddy routing
- `services/classhub/` – Django class portal
- `services/homework_helper/` – Django helper service (OpenAI)
- `docs/` – architecture, decisions, ops, and policy
- `scripts/` – server bootstrap + backup helpers
