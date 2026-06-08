# Async Self-Paced Learning Workflows RFC

## Status

- This is still an RFC, not a shipped feature.
- No progression policy model, no per-student unlock graph, and no background unlock commands are live on `main`.
- The only adjacent shipped primitive is resilient student upload queue/retry behavior for intermittent connectivity.

## Closure recommendation

Do not keep this as a broad multi-phase wish list. Narrow it to one real implementation gate:

1. If self-paced support is still desired, ship only prerequisite-based unlocks first.
2. Explicitly defer drip scheduling and spaced review until prerequisite unlocks exist and are stable.
3. If prerequisite unlocks are not planned for the next concrete build cycle, move this RFC to parked status instead of implying near-term delivery.

## Summary
ClassHub currently centers synchronous, teacher-led sessions. This RFC defines a staged path to support evergreen, self-paced delivery without breaking existing live-classroom workflows.

Core outcomes:
- release learning content automatically over time,
- gate later modules on demonstrated readiness,
- add optional spaced-review prompts without surveillance-heavy scoring.

## What to do now
1. Treat prerequisite-only unlocks as the sole candidate Phase 1 slice.
2. Do not begin drip scheduling or spaced-review work before prerequisite unlocks are implemented and exercised.
3. Add a feature-flagged data model + evaluator design review before migrations.
4. Define operator runbook updates (`doctor`, smoke, rollback) before rollout.

## Verification signal
A student in a self-paced class can:
- see exactly why Module B is locked,
- unlock Module B automatically after passing Module A prerequisite,
- receive newly released modules without teacher intervention.

## Current implementation status (March 2026)

Current `main` behavior:
- Default workflow is synchronous and teacher-led.
- Module pacing/release is still class/teacher managed.
- No shipped per-student module unlock graph yet.
- No shipped drip unlock command or spaced-review scheduler.
- Student upload flow now includes offline queue + retry behavior for intermittent connectivity on `/material/<id>/upload` (IndexedDB + service-worker-assisted flush via student API). This is a reliability primitive, not a self-paced unlock feature.

Planning status:
- This document remains an RFC roadmap, not an implemented feature record.
- Only the prerequisite-unlock slice should be treated as execution-eligible.
- Drip release and spaced repetition should be considered explicitly deferred.
- See [CURRENT_STATE.md](CURRENT_STATE.md) for shipped capability snapshot.

## Problem statement
Current assumptions:
- class cadence is controlled by live staff actions,
- release behavior is mostly class-wide and date-based,
- completion context is tied to teacher dashboards.

Gaps for self-paced programs:
- no module-level unlock graph per student,
- no prerequisite mastery thresholds,
- no automated drip release cadence,
- no long-running review scheduling for spaced reinforcement.

## Non-goals (this RFC)
- replacing teacher-led workflows,
- ranking students or adding leaderboard mechanics,
- introducing high-frequency telemetry collection.

## Proposed architecture

### 1) Progression policy model
Add explicit per-module unlock policy:
- `unlock_mode`: `immediate | drip | prerequisite`
- `drip_delay_days`: integer, relative to class join or prior completion
- `prerequisite_module_id` and/or `prerequisite_material_id`
- `prerequisite_threshold`: score/completion threshold for unlock

Keep defaults backward-compatible:
- existing classes/modules remain `immediate`.

Implementation status:
- Not started on `main`.

### 2) Student progression state
Add student-scoped progression rows:
- `student_id`
- `module_id`
- `unlocked_at`
- `completed_at`
- `mastery_score` (nullable)
- `review_due_at` (nullable, for later spaced repetition phases)
- `unlock_reason` (compact enum)

Implementation status:
- Not started on `main`.

### 3) Progression evaluator service
Add a pure service layer that computes:
- whether a module is unlockable now,
- what dependency is unmet when locked,
- whether completion thresholds have been satisfied.

This must be deterministic and reusable from:
- student home API/view rendering,
- management commands,
- staff override actions.

Implementation status:
- Not started on `main`.

### 4) Lightweight automation commands
Introduce low-risk periodic commands:
- `process_module_unlocks`:
  - evaluates pending learner-module locks,
  - unlocks newly eligible rows,
  - logs minimal audit/event metadata.
- `schedule_spaced_reviews` (later phase):
  - sets `review_due_at` based on completion/mastery policy.

No constant polling loop in web requests.

Implementation status:
- Not started on `main`.

### 5) UX behavior
Student roadmap:
- show module state (`locked`, `available`, `done`),
- show one short plain-language reason when locked,
- avoid punitive tone.

Staff view:
- optional progress summary by class/module,
- manual unlock override for intervention cases.

Implementation status:
- Not started on `main`.

## Rollout plan

### Phase 1: Prerequisite unlocks only
- add policy fields + progression table,
- compute unlock states in read path,
- support commands + manual trigger,
- explain lock reason clearly on student surfaces.

### Phase 2: Completion thresholds
- link rubric/checklist/quiz-like outcomes to prerequisite satisfaction,
- add threshold editor in teacher module controls.

### Phase 3: Drip scheduling
- add delay-based unlock policies only after prerequisite flows are stable.

### Phase 4: Spaced repetition
- add `review_due_at` scheduling and learner reminders,
- keep notifications low-noise and optional.

## Risks and mitigations
- Risk: policy complexity confuses teachers.
  - Mitigation: starter presets and clear defaults.
- Risk: regressions in live-class flows.
  - Mitigation: feature flag + backward-compatible defaults.
- Risk: over-collection of learner telemetry.
  - Mitigation: store only progression state/events needed for function.

## Testing plan
- Unit tests for progression evaluator across unlock modes.
- Integration tests for:
  - prerequisite unlock on threshold pass,
  - drip unlock after required delay,
  - roadmap state visibility for locked/available modules.
- Command tests for idempotent unlock processing.

## Operations and migration notes
- Add migration defaults that preserve current behavior (`immediate`).
- Backfill progression rows lazily on first access or by batch command.
- Keep command runtime bounded by class/module batches.

## Parking rule

If the repo does not begin the prerequisite-unlock slice in the next concrete implementation batch, this RFC should be reclassified from active roadmap guidance to parked future work.
