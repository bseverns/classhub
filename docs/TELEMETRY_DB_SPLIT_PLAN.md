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
