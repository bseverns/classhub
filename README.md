# Class Hub
[![test-suite](https://github.com/bseverns/ClassHub/actions/workflows/test-suite.yml/badge.svg)](https://github.com/bseverns/ClassHub/actions/workflows/test-suite.yml)
[![security](https://github.com/bseverns/ClassHub/actions/workflows/security.yml/badge.svg)](https://github.com/bseverns/ClassHub/actions/workflows/security.yml)
[![docs](https://github.com/bseverns/ClassHub/actions/workflows/docs.yml/badge.svg)](https://github.com/bseverns/ClassHub/actions/workflows/docs.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Class Hub is classroom-first, self-hosted learning infrastructure built for reliable operations, inspectable behavior, and privacy-forward defaults.

## Front-door map

Use these four docs as the canonical entrypoints, each with one job:

- `README.md` (this file): repository front door and quick operator/developer start.
- [`docs/START_HERE.md`](docs/START_HERE.md): role-based docs router.
- [`docs/PUBLIC_OVERVIEW.md`](docs/PUBLIC_OVERVIEW.md): external evaluator/funder overview.
- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md): what is live on `main` right now.

## What it is

- Cohort-based learning container.
- Organization-scoped access boundaries.
- Invite-only enrollment with seat controls.
- Outcome tracking and export.
- Certificate eligibility and issuance.

## What it is not

- Not a marketing website.
- Not a payment processor.
- Not a CRM.
- Not a behavioral analytics system.
- Not a surveillance-based LMS.

## Architecture at a glance

- `Class Hub` (Django): student join/session flows, class views, `/teach`, `/admin`.
- `Homework Helper` (Django): separate tutor service under `/helper/*`.
- `Caddy`: reverse proxy and TLS termination.
- `Postgres`: primary data store.
- `Redis`: cache/rate-limit/queue state.
- `MinIO`: optional backup/ops component.

Detailed architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

```mermaid
flowchart LR
  You["Browser or operator terminal"]
  Edge["Caddy edge"]
  Hub["Class Hub app"]
  Helper["Homework Helper app (/helper/*)"]
  Data["Postgres + Redis + uploads"]
  Model["Ollama local or OpenAI optional"]

  You --> Edge
  Edge --> Hub
  Edge --> Helper
  Hub --> Data
  Helper --> Data
  Helper --> Model
```

## Quickstart (local)

```bash
cp compose/.env.example.local compose/.env
cd compose
docker compose --profile local-ollama up -d --build
cd ..
bash scripts/load_demo_coursepack.sh
```

Then open:

- Student join: `http://localhost/`
- Teacher login: `http://localhost/teach/login` (or `http://localhost/admin/login/` for admin console access)

## Production posture (important)

- Domain/TLS deployments should start from `compose/.env.example.domain`.
- Production default is strict org boundary: `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`.
- Local/dev and migration scenarios may temporarily use `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`.

## Next docs

- Local demo and first run: [`docs/TRY_IT_LOCAL.md`](docs/TRY_IT_LOCAL.md)
- Security baseline: [`docs/SECURITY.md`](docs/SECURITY.md)
- Day-1 deployment checklist: [`docs/DAY1_DEPLOY_CHECKLIST.md`](docs/DAY1_DEPLOY_CHECKLIST.md)
- Runbook and operations: [`docs/RUNBOOK.md`](docs/RUNBOOK.md)
- Feature flags and maturity: [`docs/FEATURE_MATURITY.md`](docs/FEATURE_MATURITY.md)

## Repository links

- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- Service docs: [`services/classhub/README.md`](services/classhub/README.md), [`services/homework_helper/README.md`](services/homework_helper/README.md)
- Press kit: [`press/README.md`](press/README.md)
