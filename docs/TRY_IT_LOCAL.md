# Try It Local (10 Minutes)

## Summary
This guide gets a local demo running with Docker Compose so you can verify student join, teacher login, and a preloaded demo course.

## What to do now
1. Copy env defaults and start the stack.
2. Create your admin account.
3. Load the shipped demo coursepack.
4. Open student + teacher URLs and verify core flows.

## Fastest path (guided wrapper)

If you want one command instead of manual steps:

```bash
bash scripts/quickstart_stack.sh --yes --mode local --with-admin \
  --admin-username admin --admin-email admin@example.org
```

Store the generated admin password, authenticator URI/manual secret, and backup token when they are printed. Placeholder passwords are rejected.

This wrapper:
- prepares `compose/.env`,
- generates missing placeholder secrets,
- brings up Docker Compose,
- runs migrations,
- creates/updates admin,
- provisions the admin authenticator when missing,
- loads demo content,
- runs `system_doctor.sh --smoke-mode golden`.

For a real hostname, use `--mode domain --domain lms.your-org.org`. Domain mode writes the matching Django allowed-host and HTTPS CSRF-origin settings and runs the operator preflight before startup; `--domain` is required with `--yes`.

## Verification signal
At the end, you should be able to: (a) join as a student using a class code, (b) sign in at `/admin/login/`, and (c) open `/teach` with a class that contains 2 demo lessons.

## Prerequisites
- Docker Engine
- Docker Compose v2
- Git if you are cloning the repo from GitHub
- SSH access if you are copying the repo to another machine

Check:

```bash
docker --version
docker compose version
git --version
```

Expected: all three commands print versions without errors.

## 0) Get the repo onto your machine

Use this section if someone sent you the project link and you are starting from a blank terminal.

### Normal path: clone from GitHub

```bash
mkdir -p ~/classhub-demo
cd ~/classhub-demo
git clone https://github.com/bseverns/classhub.git
cd classhub
```

If you prefer Git over SSH instead of HTTPS:

```bash
mkdir -p ~/classhub-demo
cd ~/classhub-demo
git clone git@github.com:bseverns/classhub.git
cd classhub
```

Verification signal:

```bash
pwd
ls compose scripts docs services
git status --short
```

Expected: `pwd` ends in `classhub`, the folders exist, and `git status --short` prints nothing.

### If you downloaded a ZIP instead

```bash
cd ~/Downloads
unzip classhub-main.zip
cd classhub-main
```

This works for a quick read-through or demo, but `git clone` is better if you plan to update the repo later.

### Copy the repo to another machine

If you already cloned the repo on your laptop and want to copy it to a lab server or demo box, use `rsync` from your laptop:

```bash
rsync -av --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".venv_docs" \
  --exclude "site" \
  ./ user@SERVER_IP:/srv/lms/app/
```

Then SSH into the target:

```bash
ssh user@SERVER_IP
cd /srv/lms/app
ls compose scripts docs services
```

To verify that the source and target are on the same revision:

On your laptop:

```bash
git rev-parse HEAD
```

On the target machine:

```bash
cd /srv/lms/app
git rev-parse HEAD
```

If the target machine already has GitHub access, cloning directly there is usually simpler than copying:

```bash
ssh user@SERVER_IP
mkdir -p ~/classhub-demo
cd ~/classhub-demo
git clone https://github.com/bseverns/classhub.git app
cd app
ls compose scripts docs services
```

### Update an existing checkout

If you already have the repo on a machine and just need the latest `main` before running the demo:

```bash
cd /srv/lms/app  # or your repo root
git fetch origin
git switch main
git pull --ff-only origin main
```

Verification signal:

```bash
git status --short
git log -1 --oneline
```

Expected: `git status --short` prints nothing, and `git log -1 --oneline` shows the commit you expect to run.

For an actual internet-facing deployment, use [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md), [BOOTSTRAP_SERVER.md](BOOTSTRAP_SERVER.md), and [RUNBOOK.md](RUNBOOK.md) instead of treating this local demo guide as the deployment plan.

## 1) Configure local demo env

```bash
cd /srv/lms/app  # or your repo root
cp compose/.env.example.local compose/.env
sed -i.bak 's/^CADDYFILE_TEMPLATE=.*/CADDYFILE_TEMPLATE=Caddyfile.local/' compose/.env
```

Verification signal: `compose/.env` contains `CADDYFILE_TEMPLATE=Caddyfile.local`, `LLM_BACKEND=ollama`, and `COMPOSE_LOCAL_OLLAMA_AUTO=1`.

## 2) Start containers

```bash
cd compose
docker compose --profile local-ollama up -d --build
docker compose exec ollama ollama pull llama3.2:1b
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
- This guide uses the bundled CPU-local Ollama backend by default, so no OpenAI key is required.
- The quickstart wrapper auto-starts the `local-ollama` Compose profile and pulls the configured model before doctor/smoke.
- `make smoke-full` uses a deliberately small local helper profile (reduced context and short replies) so LMS hosts can validate `/helper/chat` without pretending the LMS box is the serious long-term inference node.
- If you need deterministic helper replies for CI-style testing, you can still switch to `HELPER_LLM_BACKEND=mock` in `compose/.env`.

Verification signal: helper responses return locally and no external LLM credentials are required.

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
