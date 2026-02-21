# Self-Hosted Class Hub + Homework Helper (Django)

Class Hub is a classroom-first, self-hosted micro-LMS with a separate Homework Helper service.

- Public overview: `docs/PUBLIC_OVERVIEW.md`
- Start here (canonical docs landing page): `docs/START_HERE.md`

## Try it locally in 10 minutes

See: `docs/TRY_IT_LOCAL.md`

Quick path:

```bash
cp compose/.env.example compose/.env
cd compose && docker compose up -d --build
cd ..
bash scripts/load_demo_coursepack.sh
```

Then open:
- Student join: `http://localhost/`
- Teacher login: `http://localhost/admin/login/`

## Security + deployment links

- Security posture: `docs/SECURITY.md`
- Day-1 deploy checklist: `docs/DAY1_DEPLOY_CHECKLIST.md`

## Contributing + press

- Contributing guide: `CONTRIBUTING.md`
- Press kit: `press/README.md`

A lightweight, self-hosted LMS focused on reliable classroom operations.

Mission:
- reliable (boring infra)
- inspectable (logs, checks, audit trails)
- privacy-forward (minimal student identity model)
- fast to ship (MVP-first architecture)

## Architecture at a glance

- `Class Hub` (Django): student join/session flow, class views, `/teach`, `/admin`.
- `Homework Helper` (Django): separate AI tutor service under `/helper/*`.
- `Caddy`: reverse proxy and TLS termination.
- `Postgres`: primary data store.
- `Redis`: cache/rate-limit/queue state.
- `MinIO`: object storage for uploads/assets.

Detailed architecture: `docs/ARCHITECTURE.md`

Service notebooks:
- `services/classhub/README.md`
- `services/homework_helper/README.md`

## Quickstart (local)

1. Configure environment:

```bash
cp compose/.env.example compose/.env
```

2. Set routing template in `compose/.env`:

```env
CADDYFILE_TEMPLATE=Caddyfile.local
```

3. Build and run:

```bash
cd compose
docker compose up -d --build
```

4. Create initial admin:

```bash
docker compose exec classhub_web python manage.py createsuperuser
```

5. Verify health:

- `http://localhost/healthz`
- `http://localhost/helper/healthz`

6. Run full stack self-check:

```bash
bash scripts/system_doctor.sh
```

## Docs entrypoint

Start with `docs/README.md` for the documentation contract and map.
Then use `docs/START_HERE.md` for role-specific paths:
- Operator
- Teacher/staff
- Developer

For guided hands-on learning tracks, use `docs/LEARNING_PATHS.md`.
For incident triage by symptom, use `docs/TROUBLESHOOTING.md`.
For documentation pedagogy and maintainership standards, use `docs/TEACHING_PLAYBOOK.md`.

Before opening a PR, run through `docs/MERGE_READINESS.md`.
