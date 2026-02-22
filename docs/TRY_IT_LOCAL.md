# Try It Local (10 Minutes)

## Summary
This guide gets a local demo running with Docker Compose so you can verify student join, teacher login, and a preloaded demo course.

## What to do now
1. Copy env defaults and start the stack.
2. Create your admin account.
3. Load the shipped demo coursepack.
4. Open student + teacher URLs and verify core flows.

## Verification signal
At the end, you should be able to: (a) join as a student using a class code, (b) sign in at `/admin/login/`, and (c) open `/teach` with a class that contains 2 demo lessons.

## Prerequisites
- Docker Engine
- Docker Compose v2

Check:

```bash
docker --version
docker compose version
```

Expected: both commands print versions without errors.

## 1) Configure local demo env

```bash
cd /srv/lms/app  # or your repo root
cp compose/.env.example compose/.env
sed -i.bak 's/^CADDYFILE_TEMPLATE=.*/CADDYFILE_TEMPLATE=Caddyfile.local/' compose/.env
sed -i.bak 's/^HELPER_LLM_BACKEND=.*/HELPER_LLM_BACKEND=mock/' compose/.env
```

Verification signal: `compose/.env` contains `CADDYFILE_TEMPLATE=Caddyfile.local` and `HELPER_LLM_BACKEND=mock`.

## 2) Start containers

```bash
cd compose
docker compose up -d --build
```

Verification signal:

```bash
docker compose ps
```

Expected: `classhub_web`, `helper_web`, `postgres`, `redis`, and `caddy` are up.

## 3) Create first admin account

```bash
docker compose exec classhub_web python manage.py createsuperuser
```

Use your own username/password (do not commit credentials anywhere).

Verification signal: command ends without traceback.

## 4) Load demo coursepack

From repo root:

```bash
cd /srv/lms/app
bash scripts/load_demo_coursepack.sh
```

Expected output includes:
- imported course slug `demo_classhub_quickstart`
- a class join code line like `DEMO_CLASS_CODE=...`

## 5) Open demo URLs

- Student join page: `http://localhost/`
- Teacher login page: `http://localhost/admin/login/`
- Teacher portal: `http://localhost/teach`
- Health checks:
  - `http://localhost/healthz`
  - `http://localhost/helper/healthz`

Verification signal:
- Student join succeeds with the class code printed by `load_demo_coursepack.sh`.
- Teacher login succeeds with your superuser credentials.
- `/teach` shows a class with 2 demo sessions.

## Helper defaults for safe demo
- This guide sets `HELPER_LLM_BACKEND=mock` so the helper works without OpenAI keys.
- You can optionally set a demo response text in `compose/.env`:

```dotenv
HELPER_MOCK_RESPONSE_TEXT=Let's work one step at a time. What did you try first?
```

Verification signal: helper responses return quickly and no external LLM credentials are required.

## Reset / wipe demo state

From repo root:

```bash
cd compose
docker compose down -v
cd ..
rm -rf data/postgres data/minio data/classhub_uploads
```

Then repeat steps from the top.

Verification signal: a fresh run creates a new empty DB before you load the demo coursepack.

## Safety note (public demos)
- Localhost demos are not indexable by search engines.
- Do not expose a demo stack publicly without access controls.
- Local Caddy template also sends:
  - `X-Robots-Tag: noindex, nofollow, noarchive`
  - `robots.txt` with `Disallow: /`
- If you run an internet-facing demo, apply operator controls from:
  - [SECURITY.md](SECURITY.md)
  - [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md)
  - [START_HERE.md](START_HERE.md)

Quick check:

```bash
curl -I http://localhost/ | grep -i x-robots-tag
curl -s http://localhost/robots.txt
```

If you hit startup issues, use [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
