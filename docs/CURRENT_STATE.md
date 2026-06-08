# Current State (May 7, 2026)

## Summary
This page is the live snapshot of what ClassHub currently ships on `main`.

## What is live now
- Student access uses class code + display name, with return-code/device-hint rejoin.
- Student trust controls are live: `/trust` and `/student/my-data`.
- Family-visible join/privacy/trust/upload pages now support deterministic `simple` / `standard` reading-level copy via query parameter.
- Student portfolio and session gallery flows are live with teacher-first visibility defaults.
- Student artifact remix actions are live on portfolio/gallery/upload flows, with per-submission lineage preserved.
- Student upload flow includes offline queue/retry behavior for intermittent networks.
- Student kiosk shell mode is available behind `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED` (manifest + route allowlist + focused nav constraints).
- Teacher portal includes roster, submissions, moderation, outcomes, and certificate workflows.
- Google teacher SSO is shipped behind deployment flags; Microsoft and custom OIDC providers remain scaffolded.
- Operator data-lifespan dashboard is live at `/teach/data-lifespan` with retention trend rows and CSV/JSON snapshot export (`/teach/data-lifespan/export`).
- `/teach/data-lifespan` now also surfaces aggregate remote-helper-compute posture: active lease status, low-noise trend summary, and recent class activity rows from helper-owned evidence.
- Repo now ships an unattended remote-compute evidence watcher (`python3 scripts/remote_compute_operator_watch.py`) plus reference systemd timer units for bounded webhook alerting from the helper-owned operator snapshot.
- Lesson pages now support belonging-layer metadata (`local_anchors`, `example_variants`, `community_glossary`) plus print-friendly offline handout export and PDF download.
- Teacher syllabus import now preserves belonging-layer and offline-handout sections instead of dropping them during coursepack compilation.
- Homework Helper runs as a separate Django service behind `/helper/*`.
- Homework Helper supports optional bounded local curriculum RAG (pgvector) with curriculum-only retrieval scope.
- Helper exposes an internal RAG posture contract at `/helper/internal/rag-status` (token-protected) for ClassHub operator evidence panels.
- Helper now ships a staff-only bounded remote compute control for class sessions; provider control URLs stay server-side, the remote backend is used only when state is `ready`, and helper requests fall back to local/default mode when remote compute is off, not ready, or unavailable.
- Remote helper compute now produces durable class-scoped lease evidence: requested duration, time spent in `starting`/`ready`/`degraded`, remote route and fallback counts, leased minutes, auto-stop/manual-stop counts, recent events, and an optional approximate cost estimate when operator pricing assumptions are configured.
- Remote helper control now emits explicit bridge correlation/idempotency metadata and treats duplicate same-class activate/deactivate requests as calm bounded no-op control actions.
- `/teach/class/<id>` now surfaces a tighter remote-compute evidence slice for staff: recent lease sessions, recent events, and a simple cost-risk state alongside the existing control/export path.
- Repo now ships a narrow Headscale control-plane ops bundle for createMPLS-style deployments: bootstrap, Compose stack, backup, restore, and systemd timer artifacts live under `ops/headscale/`.
- Repo now also ships a Headscale replacement-host rehearsal wrapper (`bash scripts/headscale_restore_rehearsal_evidence.sh --backup ...`) that captures control-plane restore artifacts plus LMS/GPU-side verification placeholders.
- Helper classroom-quality eval tooling is live (`scripts/run_helper_classroom_eval.sh` + classroom prompt pack in `services/homework_helper/tutor/fixtures/eval_prompts_classroom_realistic.jsonl`).
- Coursepack Authoring SDK is live via `scripts/coursepack_sdk.py` (validate/build/package local content artifacts, checksum sidecars, static registry index create/validate/list/fetch flows), and ClassHub can now import directly from a static registry index via `manage.py import_coursepack_registry` as well as superuser browser flows in `/teach` and `/admin`.
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
- Security and ops guardrails are live in CI (smoke, migration gate, endpoint guard checks, view-size/function budgets, docs-truth checks, and container/dependency scanning).
- Q2-Q3 ecosystem milestones are complete; implementation status now lives here and in feature-specific docs (the temporary milestones plan doc is retired).
- Telemetry split Phase 1 Slice 0/1/2/3/4/5/6 scaffolding is live (validated telemetry mode envs, optional telemetry DB registration in settings, telemetry router + dedicated `hub_telemetry` schema app, centralized dual-write service seam for event/outcome emit paths, read abstraction for support/rollup/lifespan event queries, baseline split-write instrumentation counters/log fields, an idempotent `backfill_telemetry_events` command with dry-run/batch resume controls, and a strict `check_telemetry_parity` command for cutover gates). Slice 7 release-cycle evidence capture is complete at `artifacts/stability/2026-03-10/telemetry/` (parity + strict smoke + rollback drill).
- Telemetry evidence tooling now also renders machine-checked `slo_summary.md` artifacts from explicit metric inputs and can include telemetry DB backup/restore validation in restore rehearsal evidence when telemetry split is active.
- Superuser runtime policy lock checks are live in `/teach?advanced=1&portal_mode=admin` and in stability guardrails via `scripts/check_runtime_policy_lock.py`.
- Teacher top-task choreography and `Start Here Today` contract wiring are live in `/teach` and guarded by `scripts/check_teacher_top_tasks_contract.py`.
- Registry-backed docs truth checks are live via `docs/_registry/runtime_contracts.json` and `scripts/check_docs_truth.py`.

## Deployment and reliability posture
- Day-1 local mode: `compose/Caddyfile.local` over HTTP.
- Domain mode: `compose/Caddyfile.domain` (or `Caddyfile.domain.assets`) with Caddy-managed TLS.
- Cookie transport in local HTTP mode: `DJANGO_SESSION_COOKIE_SECURE=0`, `DJANGO_CSRF_COOKIE_SECURE=0`.
- Cookie transport in domain/TLS mode: both values set to `1`.
- Repo-shipped env examples currently default to `DJANGO_CSP_MODE=report-only`; the Django code fallback remains `relaxed` when the setting is unset.
- System validation command: `bash scripts/validate_env_secrets.sh`.
- System validation command: `bash scripts/system_doctor.sh --smoke-mode golden`.
- Serious remote-LLM production posture is documented as: public LMS, private model host, helper-only server-to-server tailnet traffic, a Headscale-recommended control plane for createMPLS-style deployments, and a Gemma-family model as the recommended open-model example on the remote private host.

## Current product posture
- Privacy-forward default: minimal student identity model.
- Privacy-forward default: class-level retention presets.
- Privacy-forward default: student rename/export/delete controls.
- Privacy-forward default: structured staff-only support tags (no default freeform note field).
- No rankings/leaderboards in student-facing artifact and feedback flows.
- Multilingual UI is active for supported strings (`en`, `es`, `so`, `ksw`) across join/login, trust/privacy, core student flows (`/student`, `/student/my-data`, `/student/portfolio`, `/student/gallery`), and teacher day-of-class shell copy (`/teach?portal_mode=day`), with bounded tranche enforcement via `scripts/check_i18n_family_visible_contract.py`.
- S'gaw Karen (`ksw`) now ships across that same visible tranche with AI-assisted provisional copy pending native-speaker review, instead of falling back to English on the main family/student routes.

## Active known constraints
- Scoped RBAC grants are still feature-flagged for controlled rollout.
- RBAC delegated approval workflow remains feature-flagged for controlled rollout.
- Async/self-paced sequencing exists as an RFC direction; synchronous teacher-led flow remains the default operation model.
- Screenshot backlog is now clear in `press/screenshots/PLACEHOLDERS.md` (public screenshot set is complete through `21`, plus optional companion `19-rbac-tools-tab-approval-on.png`).

## Screenshot evidence status
- Canonical gallery: [SCREENSHOT_GALLERY.md](SCREENSHOT_GALLERY.md).
- Capture plan and ownership: `press/screenshots/SHOTLIST.md`.
- Placeholder inventory: `press/screenshots/PLACEHOLDERS.md`.
- Interpretation:
  - `Live capture`: screenshot reflects current `main`.
  - `Placeholder`: feature is live, screenshot refresh is pending.

## Where to look next
- Canonical policy/source map: [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md)
- Strategy and rationale: [DECISIONS.md](DECISIONS.md)
- Operator onboarding: [START_HERE.md](START_HERE.md)
- Non-technical evaluation path: [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md)
- Feature maturity and rollout flags: [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- Infrastructure hardening roadmap: [INFRASTRUCTURE_HARDENING_ROADMAP.md](INFRASTRUCTURE_HARDENING_ROADMAP.md)
- Ops execution: [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Remote-compute evidence: [EVIDENCE_REMOTE_COMPUTE.md](EVIDENCE_REMOTE_COMPUTE.md)
- RBAC implementation and policy ops: [RBAC_GUIDE.md](RBAC_GUIDE.md), [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md)
