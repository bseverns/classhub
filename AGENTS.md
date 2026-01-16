# AGENTS.md

This file is a “working contract” for coding agents.

## North Star
Build a self-hosted Class Hub + Homework Helper that is:
- reliable (boring infra)
- inspectable (logs, metrics, audit trails)
- privacy-forward (minimal PII, clear boundaries)
- fast to ship (MVP first)

## Hard constraints
- Django for both services.
- Student access uses **class code + display name** (no student email/password in MVP).
- Teachers/admins use Django auth (email/password now; Google SSO later).
- Homework Helper is a separate service routed under `/helper/*`.
- Use OpenAI **Responses API** (current recommended interface).

## Deliverables
- Implement models and views in `services/classhub/` for:
  - class join via code
  - student session middleware
  - class materials listing by module
  - teacher/admin management in Django admin
- Implement helper in `services/homework_helper/`:
  - `/helper/chat` endpoint
  - rate limiting using Redis-backed Django cache
  - prompt policy: tutor stance, anti-cheating posture
  - minimal redaction of obvious PII patterns
- Expand docs, not just code. If you make a choice, write it down in `docs/DECISIONS.md`.

## Design notes
- If domain isn’t known, use `compose/Caddyfile.local` and HTTP.
- When domain is known, use `compose/Caddyfile.domain` and let Caddy handle TLS.
