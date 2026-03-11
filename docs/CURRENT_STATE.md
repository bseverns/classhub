# Current State (March 11, 2026)

## Summary
This page is the live snapshot of what ClassHub currently ships on `main`.

## What is live now
- Student access uses class code + display name, with return-code/device-hint rejoin.
- Student trust controls are live: `/trust` and `/student/my-data`.
- Student portfolio and session gallery flows are live with teacher-first visibility defaults.
- Student upload flow includes offline queue/retry behavior for intermittent networks.
- Student kiosk shell mode is available behind `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED` (manifest + route allowlist + focused nav constraints).
- Teacher portal includes roster, submissions, moderation, outcomes, and certificate workflows.
- Operator data-lifespan dashboard is live at `/teach/data-lifespan` with retention trend rows and CSV/JSON snapshot export (`/teach/data-lifespan/export`).
- Homework Helper runs as a separate Django service behind `/helper/*`.
- Homework Helper supports optional bounded local curriculum RAG (pgvector) with curriculum-only retrieval scope.
- Helper exposes an internal RAG posture contract at `/helper/internal/rag-status` (token-protected) for ClassHub operator evidence panels.
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
- Superuser operator config snapshot is live in `/teach` (active profile/flag summary + doc pointers).
- Facilitator CLI (`hubctl`) is live from repo tooling for teacher API class controls (`tools/hubctl/`).
- Security and ops guardrails are live in CI (smoke, migration gate, endpoint guard checks, view-size/function budgets, workflow lint).
- Q2-Q3 ecosystem milestones are complete; implementation status now lives here and in feature-specific docs (the temporary milestones plan doc is retired).
- Telemetry split Phase 1 Slice 0/1/2/3/4/5/6 scaffolding is live (validated telemetry mode envs, optional telemetry DB registration in settings, telemetry router + dedicated `hub_telemetry` schema app, centralized dual-write service seam for event/outcome emit paths, read abstraction for support/rollup/lifespan event queries, baseline split-write instrumentation counters/log fields, an idempotent `backfill_telemetry_events` command with dry-run/batch resume controls, and a strict `check_telemetry_parity` command for cutover gates). Slice 7 release-cycle evidence capture is complete at `artifacts/stability/2026-03-10/telemetry/` (parity + strict smoke + rollback drill).
- Superuser runtime policy lock checks are live in `/teach?advanced=1&portal_mode=admin` and in stability guardrails via `scripts/check_runtime_policy_lock.py`.
- Teacher top-task choreography and `Start Here Today` contract wiring are live in `/teach` and guarded by `scripts/check_teacher_top_tasks_contract.py`.

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
- Multilingual UI is active for supported strings (`en`, `es`) across join/login and core student class chrome + activity copy, with broader flow coverage still in progress.

## Active known constraints
- Scoped RBAC grants are still feature-flagged for controlled rollout.
- RBAC delegated approval workflow remains feature-flagged for controlled rollout.
- Async/self-paced sequencing exists as an RFC direction; synchronous teacher-led flow remains the default operation model.
- Screenshot backlog is now narrow and explicit in `press/screenshots/PLACEHOLDERS.md` (remaining: `19-rbac-tools-tab-approval-on.png` optional companion, plus `20`/`21` data-lifespan evidence captures; target closeout 2026-03-15).

## Screenshot evidence status
- Canonical gallery: [SCREENSHOT_GALLERY.md](SCREENSHOT_GALLERY.md).
- Capture plan and ownership: `press/screenshots/SHOTLIST.md`.
- Placeholder inventory: `press/screenshots/PLACEHOLDERS.md`.
- Interpretation:
  - `Live capture`: screenshot reflects current `main`.
  - `Placeholder`: feature is live, screenshot refresh is pending.

## Where to look next
- Strategy and rationale: [DECISIONS.md](DECISIONS.md)
- Operator onboarding: [START_HERE.md](START_HERE.md)
- Non-technical evaluation path: [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md)
- Feature maturity and rollout flags: [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- Ops execution: [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- RBAC implementation and policy ops: [RBAC_GUIDE.md](RBAC_GUIDE.md), [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md)
