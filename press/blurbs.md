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
Class Hub is a self-hosted, classroom-first micro-LMS with a separate helper service. Students join by class code; teachers run invite-only cohorts, outcomes exports, and certificates with privacy-forward defaults.

## 60-word
Class Hub is a self-hosted classroom platform built with Django, Postgres, Redis, and Caddy. It emphasizes reliable workflows and privacy-forward defaults: students join with class code plus pseudonym display name and land on a clear weekly start page, while staff use authenticated teacher/admin portals. It includes org-aware access, invite-only enrollment options, outcomes/certificate reporting, and a separate lesson-scoped helper service without prompt archiving.

## 140-word
Class Hub is a self-hosted micro-LMS designed for real classroom operations. Students use a low-friction join flow (class code + pseudonym display name), then see a multi-lingual class landing page that highlights the current week and keeps the rest of the course one click away. Teachers use authenticated workflows for lessons, uploads, release controls, invite links, and exports. The platform includes organization-aware staff access, invite-only cohorts with expiring/seat-capped links, and outcomes/certificate workflows for reporting without surveillance posture. Architecture stays intentionally simple and inspectable: Django services behind Caddy with Postgres and Redis. A separate Homework Helper service provides lesson-scoped hints, is collapsed by default in student views, and avoids prompt archiving. The project emphasizes privacy-forward defaults, explicit operational runbooks, and defensive controls for public deployments, including accessibility smoke checks in CI for core user paths.

## Tweet-length (factual)
Class Hub is a self-hosted, classroom-first micro-LMS: class-code student join with pseudonyms, multi-lingual weekly-first student landing, org-aware teacher workflows, invite-only cohorts, outcomes/certificate reporting, and a separate helper service with no prompt archive.
