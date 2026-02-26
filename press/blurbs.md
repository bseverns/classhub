# Press Blurbs

## Summary
These blurbs are short, factual descriptions for listings, announcements, and internal evaluation notes.

## What to do now
1. Pick the length that matches your channel.
2. Keep wording factual; avoid implied features not in docs.
3. Link back to `docs/PUBLIC_OVERVIEW.md` or `docs/TRY_IT_LOCAL.md`.

## Verification signal
If a blurb is suitable, it should describe scope and audience without marketing claims or unsupported promises.

## 30-word
Class Hub is a self-hosted, classroom-first micro-LMS with a separate helper service. Students join by class code; teachers manage classes, invite-only cohorts, outcomes, and certificates through Django workflows.

## 60-word
Class Hub is a self-hosted classroom platform built with Django, Postgres, Redis, and Caddy. It emphasizes reliable workflows and privacy-forward defaults: students join with class code plus display name, while staff use authenticated teacher/admin portals. It includes org-aware access, invite-only enrollment options, outcomes/certificate reporting, and a separate Homework Helper service. Deployment, security, and operations docs are included for public-domain setups.

## 140-word
Class Hub is a self-hosted micro-LMS designed for real classroom operations. Students use a low-friction join flow (class code + display name) while teachers use authenticated workflows for lessons, uploads, release controls, and exports. The platform now includes organization-aware staff access, invite-only cohorts with expiring/seat-capped links, and outcomes/certificate workflows for reporting without surveillance posture. Architecture stays intentionally simple and inspectable: Django services behind Caddy with Postgres and Redis. A separate Homework Helper service provides scoped hints and can run in mock or local-LLM mode for demos. The project emphasizes privacy-forward defaults, explicit operational runbooks, and defensive controls for public deployments, including accessibility smoke checks in CI for core user paths. It is aimed at teams that want direct infrastructure control and predictable behavior over SaaS lock-in.

## Tweet-length (factual)
Class Hub is a self-hosted, classroom-first micro-LMS: class-code student join, org-aware teacher workflows, invite-only cohorts, outcomes/certificate reporting, and a separate helper service. Local demo + deployment docs included.
