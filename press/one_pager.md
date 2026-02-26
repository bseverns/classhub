# Class Hub One-Pager

## Summary
Class Hub is a self-hosted, classroom-first micro-LMS with a separate Homework Helper service for guided hints.

## What to do now
1. Share this page for quick project context.
2. Pair it with `docs/PUBLIC_OVERVIEW.md` and `docs/TRY_IT_LOCAL.md`.
3. Use the blurbs and architecture page for shorter channels.

## Verification signal
A reader should understand the system scope, deployment shape, and privacy stance in under five minutes.

## What it is
- Django-based class hub for lesson delivery and teacher workflows.
- Separate helper service routed under `/helper/*`.
- Self-hosted stack using Caddy, Postgres, Redis, and optional Ollama.

## Who it is for
- Schools and programs wanting local operational control.
- Teams that prefer low-complexity, inspectable infrastructure.

## Key features
- Student join by class code + display name (no student password accounts in MVP).
- Teacher/admin auth with OTP support and teacher self-service profile updates.
- Organization-aware staff access with optional hard org boundary mode.
- Invite-only enrollment controls with expiring/seat-capped invite links.
- Lesson release controls, upload dropboxes, and privacy-safe export tooling.
- Outcomes and certificate eligibility/issuance workflows for teacher reporting.
- Site degradation modes for operational incidents.
- Accessibility smoke gate in CI for core student/teacher routes.

## Deployment summary
- Local demo: Docker Compose (`Caddyfile.local`).
- Public deployment: domain Caddy template with TLS and operator guardrails.
- Operations playbooks in `docs/DAY1_DEPLOY_CHECKLIST.md` and `docs/RUNBOOK.md`.

## Privacy and safety stance
- Minimal student identity model.
- No surveillance analytics posture.
- Explicit retention and cleanup operations.
- Hardened download and no-store patterns on sensitive routes.
- Export and certificate/report surfaces avoid helper prompt content by design.

## Try it locally
- `docs/TRY_IT_LOCAL.md`
