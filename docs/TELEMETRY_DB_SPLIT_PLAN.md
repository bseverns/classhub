# Telemetry Database Split Plan (Phase 1)

## Summary
This page defines a low-risk, near-zero-downtime plan to split high-churn telemetry workloads from ClassHub's core transactional database.

Goal:
- keep join/login/submission core flows stable during event spikes and retention pruning,
- reduce blast radius and backup/restore time for core LMS data.

Non-goal (Phase 1):
- do not split core transactional models (`Class`, `Module`, `Material`, `Submission`, auth tables).

## What to do now
1. Provision a second Postgres instance/database for telemetry.
2. Add dual-write + read-toggle scaffolding in Django.
3. Backfill telemetry data from core in batches.
4. Cut reads over to telemetry, then keep dual-write for stabilization.
5. Only after stable period, decide whether to stop writing telemetry events to core.

## Verification signal
At the end of Phase 1:
- student join/upload latency remains stable during prune jobs,
- teacher support board and telemetry-derived rollups work with telemetry reads enabled,
- rollback to core reads can be done by env toggle only.

## Why this split first
`StudentEvent` and `StudentOutcomeEvent` are append-only, high-write, and retention-pruned.
They are good isolation candidates because:
- they can tolerate eventual consistency during migration windows,
- they do not gate core identity/material integrity.

## Target topology
- `default` DB (core): auth, classes, roster, materials, submissions, staff audit.
- `telemetry` DB: append-only student telemetry streams and related read paths.
- object storage (already external): lesson assets + uploads remain external and separate from DB.

## Important model constraint
Do not move existing FK-constrained event tables directly to a second DB in one step.
Cross-database FK constraints and ORM joins are not safe for this codebase today.

Phase 1 approach:
- introduce telemetry-native tables with scalar IDs (no cross-DB FKs),
- dual-write from existing event emit points,
- progressively move read paths to telemetry queries.

## Execution plan

### Phase 0: Infrastructure prep
- Provision telemetry Postgres with:
  - PITR backups,
  - separate credentials,
  - connection pooling.
- Add monitoring:
  - write QPS,
  - replication/backlog (if managed service),
  - slow query logs.

### Phase 1A: Django config + flags (no behavior change yet)
- Add env vars:
  - `CLASSHUB_TELEMETRY_DATABASE_URL` (optional; empty disables feature),
  - `CLASSHUB_TELEMETRY_WRITE_MODE=off|dual|telemetry_only` (start with `off`),
  - `CLASSHUB_TELEMETRY_READ_MODE=core|telemetry` (start with `core`).
- Settings pattern:
  - add `DATABASES["telemetry"]` only when URL is set,
  - keep `DATABASE_ROUTERS` empty until telemetry models exist.

### Phase 1B: Telemetry app + schema
- Create a dedicated app (recommended: `hub_telemetry`) with tables:
  - `TelemetryStudentEvent`
  - `TelemetryStudentOutcomeEvent`
- Store scalar references instead of FKs:
  - `classroom_id`, `student_id`, `module_id`, `material_id` (nullable integers),
  - plus event type, source, details JSON, created_at.
- Add indexes equivalent to current event query shapes.

### Phase 1C: Dual-write implementation
- Keep existing core writes untouched.
- Update event emit helpers to write:
  - core only when write mode `off`,
  - core + telemetry when `dual`,
  - telemetry only when `telemetry_only`.
- For `dual` mode:
  - telemetry write failures should log loudly and increment counters,
  - core write must continue to preserve behavior during rollout.

### Phase 1D: Backfill
- Implement management command, e.g.:
  - `python manage.py backfill_telemetry_events --batch-size 5000 --since-id N`
- Backfill order:
  1. `StudentEvent`
  2. `StudentOutcomeEvent`
- Backfill idempotency:
  - use deterministic natural key hash or `(legacy_id, source_table)` markers.

### Phase 1E: Read cutover
- Move read-heavy paths behind `CLASSHUB_TELEMETRY_READ_MODE`:
  - facilitator support board queries,
  - event/outcome rollups and metrics panels.
- Keep fallback path to core queries under same code path.

### Phase 1F: Stabilization window
- Run with:
  - `WRITE_MODE=dual`
  - `READ_MODE=telemetry`
  - for at least 1-2 release cycles.
- Validate:
  - row counts by event_type/day between core and telemetry,
  - key dashboard aggregates parity.

### Phase 1G: Optional completion
- If stable and parity is proven:
  - set `WRITE_MODE=telemetry_only`.
- Keep core event tables for retention window before any destructive cleanup.

## Rollback plan

Fast rollback (no migration):
1. Set `CLASSHUB_TELEMETRY_READ_MODE=core`.
2. Keep `WRITE_MODE=dual` (or `off` if telemetry DB is degraded).
3. Redeploy app.

Data safety rule:
- never disable core writes until telemetry parity checks are green for the stabilization window.

## Operational checks
- Add to CI/deploy checklist:
  - telemetry DB connectivity check (when URL configured),
  - dual-write smoke check logs.
- Add runbook tasks:
  - parity spot-check command output,
  - backlog/failed-write alert thresholds.

## Suggested env matrix
- Local/default:
  - telemetry URL unset
  - `WRITE_MODE=off`
  - `READ_MODE=core`
- Staging rollout:
  - telemetry URL set
  - `WRITE_MODE=dual`
  - `READ_MODE=core` then `telemetry`
- Production steady-state (after validation):
  - telemetry URL set
  - `WRITE_MODE=dual` (safer) or `telemetry_only` (leaner)
  - `READ_MODE=telemetry`

## Phase 2 candidates (not part of this change)
- Core DB read replica for teacher dashboards/reporting.
- Dedicated analytics warehouse fed from telemetry DB.
- Optional audit stream hardening (keep `AuditEvent` in core unless compliance architecture changes).

## Phase 1 implementation backlog (execution checklist)

Use this as the canonical execution tracker for the next stable build.
Ship each slice as an isolated PR with rollback-safe toggles.

- [x] Slice 0: Baseline instrumentation + guardrails
  - Add explicit counters/log fields for telemetry dual-write attempts, successes, and failures.
  - Add an env validation rule set for telemetry toggles (invalid mode values fail early).
  - Ensure deploy smoke remains green with telemetry toggles unset.
- [x] Slice 1: Settings + telemetry DB registration
  - Add `CLASSHUB_TELEMETRY_DATABASE_URL`, `CLASSHUB_TELEMETRY_WRITE_MODE`, `CLASSHUB_TELEMETRY_READ_MODE` parsing in settings.
  - Register `DATABASES["telemetry"]` only when URL is set.
  - Keep behavior identical with default envs (`WRITE_MODE=off`, `READ_MODE=core`).
- [ ] Slice 2: Telemetry app + schema
  - Add `hub_telemetry` app and migrations for:
    - `TelemetryStudentEvent`,
    - `TelemetryStudentOutcomeEvent`.
  - Use scalar references only (no cross-DB FKs).
  - Add indexes matching support-board and outcomes rollup read patterns.
- [ ] Slice 3: Dual-write service seam
  - Introduce a single telemetry write service called by event emit points.
  - In `off`: write core only.
  - In `dual`: write core + telemetry (telemetry failures must not break core writes).
  - In `telemetry_only`: write telemetry only (not enabled in production until Phase 1F gate is complete).
- [ ] Slice 4: Read abstraction + core/telemetry switch
  - Add read helper layer for event/outcome queries used by:
    - support board,
    - teacher class rollups,
    - data lifespan rollups that include event counts.
  - Keep shared return contract for both backends to avoid UI/view branching.
- [ ] Slice 5: Backfill command + idempotency
  - Add `backfill_telemetry_events` management command with:
    - `--batch-size`,
    - `--since-id`,
    - `--dry-run`,
    - `--max-batches`.
  - Guarantee idempotent re-runs.
  - Emit backfill progress metrics and summary.
- [ ] Slice 6: Parity checker + cutover runbook hooks
  - Add parity check command/script for row counts and key aggregates by day/event type.
  - Add deploy checklist step: parity must be green before `READ_MODE=telemetry`.
  - Add rollback checklist step: immediate switch back to `READ_MODE=core`.
- [ ] Slice 7: Staging/prod stabilization evidence
  - Run at least one full release cycle with `WRITE_MODE=dual`, `READ_MODE=telemetry`.
  - Capture parity evidence snapshots and rollback drill output.
  - Only then decide whether to keep `dual` or move to `telemetry_only`.

## Code touchpoints inventory (expected)

Primary ClassHub areas likely to change:
- `services/classhub/config/settings.py` (env parsing + `DATABASES["telemetry"]`)
- `services/classhub/hub/models.py` (core telemetry model contract reference points only; no cross-db FK extension)
- `services/classhub/hub/services/teacher_roster_class.py` (support board and rollup read paths)
- `services/classhub/hub/services/teacher_tracker.py` (helper-access telemetry rollups)
- `services/classhub/hub/services/data_lifespan.py` (event/outcome count sources)
- `services/classhub/hub/views/internal.py` (helper telemetry ingestion write path)
- `services/classhub/hub/views/student*.py` and `services/classhub/hub/views/api_student_upload.py` (student event emit points)
- `services/classhub/hub/management/commands/` (new backfill/parity commands)
- `services/classhub/hub/tests/` + `services/classhub/hub/tests_services.py` (behavior parity and toggle tests)
- `scripts/system_doctor.sh` / smoke docs (optional telemetry parity gates when URL is configured)

Planned new app path:
- `services/classhub/hub_telemetry/` (models, migrations, query adapters).

## Exit criteria by gate

### Gate A (after Slice 3)
- Core behavior unchanged with toggles at defaults.
- Dual-write emits telemetry failure counters without user-visible regression.
- Smoke + migration gates pass.

### Gate B (after Slice 5)
- Backfill can run incrementally and re-run safely.
- Backfill dry-run output is deterministic.
- No lock contention regressions on core tables during backfill batches.

### Gate C (before `READ_MODE=telemetry` in production)
- Parity checks pass for:
  - daily row counts by event type,
  - support-board unresolved counts,
  - teacher outcomes rollups.
- Rollback drill (`READ_MODE=core`) completes via env toggle + redeploy only.

### Gate D (before `WRITE_MODE=telemetry_only`)
- At least one release cycle of stable dual-write telemetry.
- No unresolved parity deltas above agreed threshold.
- Retention and backup procedures tested with telemetry DB present.

## Verification command set (operator-ready)

Use these commands as the minimum proof set per rollout stage.

Baseline stack validation:

```bash
cd /srv/lms/app
bash scripts/system_doctor.sh --smoke-mode golden
```

Targeted ClassHub regression set (during implementation slices):

```bash
cd /srv/lms/app/compose
docker compose exec -T classhub_web python manage.py test \
  hub.tests.test_student_ops \
  hub.tests.test_teacher_admin_portal \
  hub.tests_services
```

Planned parity/backfill command examples (once implemented):

```bash
cd /srv/lms/app/compose
docker compose exec -T classhub_web python manage.py backfill_telemetry_events --dry-run --batch-size 5000
docker compose exec -T classhub_web python manage.py check_telemetry_parity --window-days 7
```

## Open decisions requiring sign-off

- Threshold for acceptable parity deltas during stabilization (strict zero vs bounded percentage).
- Whether production steady-state remains `WRITE_MODE=dual` for safety or moves to `telemetry_only`.
- Retention/backup ownership boundaries for telemetry DB in disaster-recovery drills.
