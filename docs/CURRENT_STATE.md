# Current State (March 5, 2026)

## Summary
This page is the live snapshot of what ClassHub currently ships on `main`.

## What is live now
- Student access uses class code + display name, with return-code/device-hint rejoin.
- Student trust controls are live: `/trust` and `/student/my-data`.
- Student portfolio and session gallery flows are live with teacher-first visibility defaults.
- Student upload flow includes offline queue/retry behavior for intermittent networks.
- Teacher portal includes roster, submissions, moderation, outcomes, and certificate workflows.
- Operator data-lifespan dashboard is live at `/teach/data-lifespan`.
- Homework Helper runs as a separate Django service behind `/helper/*`.
- Homework Helper supports optional bounded local curriculum RAG (pgvector) with curriculum-only retrieval scope.
- Coursepack Authoring SDK is live via `scripts/coursepack_sdk.py` (validate/build/package local content artifacts).
- Teacher syllabus zip import now maps session-prefixed support images into lesson assets.
- Organization boundaries and RBAC capability checks are live.
- Scoped RBAC grants are live behind `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED`.
- RBAC simulation and policy bundle import/export endpoints are live for operators.
- RBAC custom roles are live (role definitions, capabilities, and staff assignments) in teacher RBAC tools and policy bundles.
- RBAC delegated approval workflow is live behind `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED` (default off for initial rollout).
- RBAC approval reviews now require org owner/admin role (or superuser) and block self-approval.
- Superuser class-to-teacher assignment workflows are live in `/teach` org admin tools and `/teach/class/<id>`.
- Superuser account lifecycle actions are live in `/teach` (enable/disable, promote/demote superuser, reset password, resend invite).
- Superuser organization lifecycle controls are live in `/teach` (rename, guarded archive/restore, class-to-organization move).
- Security and ops guardrails are live in CI (smoke, migration gate, endpoint guard checks, view-size/function budgets, workflow lint).

## Deployment and reliability posture
- Day-1 local mode: `compose/Caddyfile.local` over HTTP.
- Domain mode: `compose/Caddyfile.domain` (or `Caddyfile.domain.assets`) with Caddy-managed TLS.
- Cookie transport in local HTTP mode: `DJANGO_SESSION_COOKIE_SECURE=0`, `DJANGO_CSRF_COOKIE_SECURE=0`.
- Cookie transport in domain/TLS mode: both values set to `1`.
- System validation command: `bash scripts/validate_env_secrets.sh`.
- System validation command: `bash scripts/system_doctor.sh --smoke-mode golden`.

## Current product posture
- Privacy-forward default: minimal student identity model.
- Privacy-forward default: class-level retention presets.
- Privacy-forward default: student rename/export/delete controls.
- Privacy-forward default: structured staff-only support tags (no default freeform note field).
- No rankings/leaderboards in student-facing artifact and feedback flows.
- Multilingual UI is active for supported strings (`en`, `es`) with ongoing i18n cleanup work.

## Active known constraints
- Scoped RBAC grants are still feature-flagged for controlled rollout.
- RBAC delegated approval workflow remains feature-flagged for controlled rollout.
- Async/self-paced sequencing exists as an RFC direction; synchronous teacher-led flow remains the default operation model.
- Some docs and screenshots are placeholders and are still being refreshed in the press kit shotlist.

## Where to look next
- Strategy and rationale: [DECISIONS.md](DECISIONS.md)
- Operator onboarding: [START_HERE.md](START_HERE.md)
- Ops execution: [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- RBAC implementation and policy ops: [RBAC_GUIDE.md](RBAC_GUIDE.md), [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md)
