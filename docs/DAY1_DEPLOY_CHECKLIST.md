# Day 1 deploy checklist (Ubuntu)

See `scripts/bootstrap_day1.sh` for an automated starter.

## Essentials
- Create non-root deploy user
- Enable firewall (SSH/80/443 only)
- Install Docker + Compose
- Set Docker log limits
- Create `/srv/classhub` directory spine
- Put backups off-server

## Run
- Copy `compose/.env.example` → `compose/.env`
- Run `docker compose up -d --build`
- Create superuser
- Verify health endpoints

## Domain later
If you do not have a domain yet:
- use `compose/Caddyfile.local` (HTTP on :80)

When a domain exists:
- set `DOMAIN=...` in `.env`
- point DNS A record to server
- copy `compose/Caddyfile.domain` → `compose/Caddyfile`
- Caddy will obtain TLS certificates automatically
