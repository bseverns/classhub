# Tool Charter: ClassHub + Homework Helper

Version: 1.0  
Effective date: 2026-02-26  
Review cadence: quarterly (or after major incident/change)

## 1) Purpose

This tool exists to support classroom instruction with:
- fast student join, lesson access, and submission workflows,
- teacher operational control from `/teach`,
- bounded tutoring support via Homework Helper under `/helper/*`.

This tool is not for:
- surveillance analytics, ad-tech tracking, or brokered data sharing,
- high-stakes automated grading/discipline decisions without teacher review,
- general-purpose AI assistant use outside classroom/course scope.

## 2) Ownership

- Primary owner: Ben Severns (createMPLS)
- Backup owner: `TBD (name + role required before production sign-off)`

Owner responsibilities:
- approve production changes,
- maintain retention and security settings,
- coordinate incident response and communications,
- ensure quarterly policy + access review is completed.

## 3) Support Boundary

In scope (supported):
- class creation/join flow, roster controls, submissions, teacher portal workflows,
- helper availability, helper class reset, helper policy/config tuning,
- deploy/release operations using documented scripts and smoke checks.

Out of scope (not supported by this tool):
- unmanaged third-party plugin integrations,
- custom data pipelines not documented in repo runbooks,
- emergency legal/compliance decisions without organizational leadership.

## 4) Data Posture

Stored data classes:
- classroom operational records (classes, modules, materials, submissions),
- teacher/admin audit events,
- student events (metadata-focused),
- short-lived helper conversation cache,
- optional helper class-reset archive snapshots for internal research/ops.

Retention + control:
- submission/event/helper-export retention managed via `scripts/retention_maintenance.sh`,
- helper reset archive defaults: `/uploads/helper_reset_exports`, 30-day prune window,
- helper archive path constrained under `/uploads`, with maintenance-time permission tightening (`0700` dir, `0600` files),
- student self-service controls at `/student/my-data` (export/delete/end-session),
- teacher/admin controls for class-level data actions in `/teach`.

Access boundary statement:
- helper reset archives are internal artifacts available only to authorized teachers and createMPLS admins,
- helper reset archives are not publicly served routes and are not included in student-facing exports.

## 5) Change Control

Standard release path:
1. Build release artifact (`scripts/make_release_zip.sh` when applicable).
2. Deploy with migration gate + smoke (`scripts/deploy_with_smoke.sh`).
3. Verify strict checks (`/healthz`, `/helper/healthz`, join/helper/teacher paths).
4. Record release notes + decisions in docs (`docs/DECISIONS.md`, release docs).

Any production-impacting config change must include:
- rollback path,
- smoke verification result,
- owner approval.

## 6) Exit Plan (Safe Sunset)

If the tool is retired:
1. Announce timeline and freeze new feature changes.
2. Export required data for admins/teachers (per policy).
3. Run final retention/export cycle and archive required records.
4. Revoke helper/internal API tokens and external credentials.
5. Disable public routing and stop scheduled maintenance timers.
6. Shut down services and preserve encrypted backups for policy-defined hold period.
7. Document final state, custody, and deletion dates.

