# Public Overview

## Summary
Class Hub is a classroom-first, self-hosted micro-LMS with a separate Homework Helper service. It is designed for calm classroom operations, low-friction student access, and operator control over infrastructure and data.

## What to do now
1. Decide if this fits your context (quick bullets below).
2. Try the local demo path in `docs/TRY_IT_LOCAL.md`.
3. If you plan public deployment, read `docs/SECURITY.md`, then `docs/DAY1_DEPLOY_CHECKLIST.md` and `docs/RUNBOOK.md`.

## Verification signal
If this page is useful, you should be able to answer: who this is for, what it deliberately does not do, and the next 2 docs to read for an evaluation.

## What it is
- A self-hosted learning hub for classes, modules, and lesson materials.
- A simple student join flow (`class code + display name`) without student password accounts in MVP.
- A teacher/admin workflow built on Django auth, with safety controls for public-domain operation.

## Who it is for
- Small schools and programs that want self-hosted control.
- Makerspaces, after-school labs, and classroom pilots.
- Teams that prefer simple operational primitives over large platform complexity.

## What makes it different
- Privacy-first defaults (minimal student identity model, explicit retention controls).
- Calm student join model (no student email/password in MVP).
- Public-domain hardening options (CSP, site-mode degradation, proxy guardrails).
- Self-hosted architecture with boring, inspectable components (Django, Postgres, Redis, Caddy).

## What it will not do
- No surveillance analytics posture.
- No ad-tech or data resale model.
- No dark-pattern growth loops.
- No hidden SaaS lock-in requirement for core operation.

## Try it in 10 minutes
- Local demo path: `docs/TRY_IT_LOCAL.md`

## Screenshots (placeholders)
- Student join screen: `press/screenshots/01-student-join.png`
- Teacher dashboard: `press/screenshots/03-teacher-dashboard.png`
- Lesson page with helper: `press/screenshots/05-lesson-with-helper.png`

## Ops and security links
- `docs/SECURITY.md`
- `docs/DAY1_DEPLOY_CHECKLIST.md`
- `docs/RUNBOOK.md`
