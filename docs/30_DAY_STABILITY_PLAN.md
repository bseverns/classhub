# 30-Day Stability Plan (30/60/90 Execution)

## Summary

This plan converts the stability freeze into a command-backed operating plan.

Primary goal: make ClassHub calmer to run and easier to hand off.
Secondary goal: ship proof artifacts with each release so operations are inspectable.

## Plan Window

- Plan start: March 10, 2026
- Day 30 checkpoint: April 9, 2026
- Day 60 checkpoint: May 9, 2026
- Day 90 checkpoint: June 8, 2026

## Scope And Constraints

- No new product primitives during Day 0-30.
- Any exception must follow [STABILITY_CHARTER.md](STABILITY_CHARTER.md).
- Prefer workflow simplification, guardrails, and rehearsal over feature expansion.

## Owner Map

| Role | Responsibility | Backup |
| --- | --- | --- |
| Maintainer | Code changes, guardrail enforcement, release evidence assembly | Secondary maintainer |
| Ops Director | Runtime checks, restore drills, retention verification, incident rituals | Engineering manager |
| Teacher Lead | Top-task validation, classroom workflow feedback, onboarding clarity | Instructional coach |
| Executive Director | Policy sign-off, reporting semantics sign-off, survivability governance | Ops Director |

Owner/cadence tracker:
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)

## Workstreams

1. Teacher workflow calm (`/teach` sequencing and progressive disclosure).
2. Release evidence culture (proof artifacts per release, not narrative-only confidence).
3. Survivability and turnover (restore, retention, access-review, handoff packet).
4. Accessibility and localization coverage for core teacher/student paths.
5. Outcome and certificate semantic clarity for operator/reporting consistency.
6. Coursepack portability hardening (validation + authoring ergonomics, no marketplace pivot).

## 30/60/90 Milestones

| Horizon | Focus | Owners | Required Artifacts | Exit Criteria |
| --- | --- | --- | --- | --- |
| Day 0-30 | Teacher calm + release proof + survivability baselines | Maintainer, Ops Director, Teacher Lead | Top-10 task map, first release evidence pack, turnover packet v1 | New staff can start `/teach` in under 2 minutes, restore drill completed with dated evidence, release artifacts generated for one full release cycle |
| Day 31-60 | Accessibility/localization core + outcomes/reporting semantics | Maintainer, Teacher Lead, Executive Director | Core-flow a11y checklist, translation coverage matrix, outcomes semantics note | Core teacher/student flows pass critical a11y smoke and have reviewed copy/translation coverage; reporting terms are canonical and reused |
| Day 61-90 | Coursepack portability + long-term survivability cadence | Maintainer, Ops Director | Coursepack validation report template, quarterly ritual calendar, turnover packet v2 | Coursepack import/export quality is measurable and repeatable; quarterly rituals are scheduled with owners and runbooks |

## Day 0-30 Detailed Execution

### Track A: Teacher Workflow Calm

Owner: Maintainer + Teacher Lead

Deliverables:

- One canonical "Top 10 teacher tasks" list for `/teach`.
- Canonical task map is documented in [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md).
- Task-first navigation labels and copy for daily teacher flows.
- Separation language that distinguishes classroom actions from org/operator actions.
- Friction log from one observed teacher run (notes only, no surveillance instrumentation).

Command checklist (per PR touching teacher surfaces):

- `python scripts/check_view_size_budgets.py`
- `python scripts/check_view_function_budgets.py`
- `python scripts/check_teacher_endpoint_capability_map.py`
- `python scripts/check_rbac_endpoint_guards.py`
- `python scripts/check_frontend_static_refs.py`
- `python scripts/check_no_inline_template_js.py`
- `python scripts/check_no_inline_template_css.py`

Exit criteria:

- Top-10 task list approved by Teacher Lead and Maintainer.
- `/teach` first-contact path reviewed in a live walkthrough.
- No duplicated/conflicting action wording in high-risk teacher paths.

### Track B: Release Evidence Culture

Owner: Maintainer + Ops Director

Deliverables:

- One release evidence folder per release under `artifacts/stability/<release-date>/`.
- A short release scorecard markdown file describing live flags/modes and pass/fail checks.
- A repeatable artifact checklist attached to PR/release process.

Command checklist (per release candidate):

- `python scripts/check_test_inventory_coverage.py`
- `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`
- `bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical --install-browsers`
- `bash scripts/backup_restore_rehearsal.sh --compose-mode prod`
- `bash scripts/kiosk_resilience_check.sh --non-interactive`
- `python scripts/lint_release_artifact.py <release-zip-path>`
- `bash scripts/stability_release_evidence.sh --compose-mode prod --release-date <YYYY-MM-DD>` (recommended one-command collector)

Exit criteria:

- One complete evidence pack published for at least one real release.
- Operator scorecard is generated and reviewed before release sign-off.
- No release without attached artifacts for smoke, a11y, and restore rehearsal.

### Track C: Survivability And Turnover Baseline

Owner: Ops Director + Maintainer

Deliverables:

- Turnover packet v1 with one-hour start path and one-week confidence path.
- Turnover packet v1 is documented in [TURNOVER_PACKET.md](TURNOVER_PACKET.md).
- Turnover drill evidence log is documented in [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md).
- Named owners for restore, retention, access review, and release sign-off.
- Documented cadence table for monthly and quarterly rituals.
- Monthly/quarterly cadence checklist is documented in [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md).
- Org-boundary policy audit template is documented in [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md).

Command checklist (monthly minimum):

- `bash scripts/retention_maintenance.sh --dry-run`
- `bash scripts/retention_health_snapshot.sh --compose-mode prod --out artifacts/stability/<date>/retention_health.log`
- `bash scripts/restore_rehearsal_evidence.sh --compose-mode prod --out-dir artifacts/stability/<date>`
- `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`

Exit criteria:

- Team can answer "when did we last test restore?" with a date and artifact path.
- Team can answer "is retention active and healthy?" with command output.
- New maintainer can run core health checks without maintainer-only tribal knowledge.

## Day 31-60 Detailed Execution

### Track D: Accessibility And Localization Core Coverage

Owner: Teacher Lead + Maintainer

Deliverables:

- Core-route accessibility checklist for student join/session/module and top teacher actions.
- Translation coverage matrix for trust pages, kiosk shell, join flow, and top teacher tasks.
- Priority fixes for keyboard order, focus visibility, and screen-reader labels in dense teacher flows.

Command checklist:

- `bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical`
- `python scripts/check_frontend_static_refs.py`
- `python scripts/check_no_inline_template_js.py`
- `python scripts/check_no_inline_template_css.py`

Exit criteria:

- Critical a11y smoke passes for core routes.
- Translation coverage decisions are explicit (what is complete, partial, deferred).
- Keyboard-first flow succeeds for top teacher daily tasks.

### Track E: Outcome And Reporting Semantics

Owner: Executive Director + Ops Director + Maintainer

Deliverables:

- Canonical semantics doc for `session_completed`, `artifact_submitted`, `eligible`, `issued`.
- Canonical semantics doc is published at [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md).
- One end-to-end reporting rehearsal: join -> submit -> complete -> export -> certificate issue.
- Reporting rehearsal template + evidence log is documented in [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md).
- Operator-facing explanation copy in relevant `/teach` surfaces.

Command checklist:

- `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`
- `python scripts/check_test_inventory_coverage.py`

Exit criteria:

- Fundraising, ops, and teachers use the same definitions.
- Certificate thresholds and semantics are confirmed in handoff docs.

## Day 61-90 Detailed Execution

### Track F: Coursepack Portability Hardening

Owner: Maintainer

Deliverables:

- Coursepack validation/report template for import/export quality checks.
- Authoring error taxonomy (what failed, where, and what to fix) for teacher-facing ingestion.
- RFC-ready note for decentralized discovery that preserves non-marketplace posture.

Command checklist:

- `python scripts/coursepack_sdk.py --help`
- `python scripts/validate_coursepack.py --help`
- `python scripts/new_course_scaffold.py --help`
- `python scripts/ingest_syllabus_md.py --help`

Exit criteria:

- Coursepack quality is measured by repeatable checks, not ad-hoc judgment.
- Import failures produce actionable operator/author guidance.

### Track G: Survivability Cadence Lock-In

Owner: Ops Director + Executive Director

Deliverables:

- Quarterly ritual calendar committed to docs and shared operations calendar.
- Turnover packet v2 with scenario playbooks (helper outage, Wi-Fi degradation, staff offboarding, org boundary confusion).
- Signed owner matrix for all recurring checks.

Required recurring commands:

- Monthly: `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`
- Monthly: `bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical`
- Quarterly: `bash scripts/restore_rehearsal_evidence.sh --compose-mode prod --out-dir artifacts/stability/<date>`
- Release-time: `python scripts/lint_release_artifact.py <release-zip-path>`

Exit criteria:

- Rituals are scheduled and actually run on cadence.
- Operational confidence no longer depends on one maintainer's memory.

## Artifact Checklist (Per Release)

Store under `artifacts/stability/<release-date>/`:

- `system_doctor.log`
- `a11y_smoke.log`
- `restore_rehearsal.log`
- `restore_rehearsal_metrics.json`
- `restore_rehearsal_summary.md`
- `guardrails.log` (view budgets, endpoint guards, route map guards)
- `release_artifact_lint.log`
- `operator_scorecard.md` (live flags, known risks, manual checks remaining)

## Next-Cycle Closeout (Phase 1 + Slice 7)

Use this for one full sign-off cycle that closes Day 0-30 Phase 1 tracks and telemetry Slice 7 evidence.

### Runtime lock (Day 1)

Before running evidence capture, confirm:

- `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`
- `CLASSHUB_TELEMETRY_WRITE_MODE=dual`
- `CLASSHUB_TELEMETRY_READ_MODE=telemetry`
- no net-new primitives in scope (stabilization/docs/evidence only)

### One-command closeout run

```bash
cd /srv/lms/app
make stability-cycle-closeout \
  STABILITY_RELEASE_DATE=<YYYY-MM-DD> \
  SMOKE_COMPOSE_MODE=prod \
  TELEMETRY_WINDOW_DAYS=7
```

Expected outputs:

- `artifacts/stability/<date>/operator_scorecard.md`
- `artifacts/stability/<date>/runtime_lock_check.log`
- `artifacts/stability/<date>/cycle_closeout_summary.md`
- `artifacts/stability/<date>/telemetry/parity_check.log`
- `artifacts/stability/<date>/telemetry/smoke_strict.log`
- `artifacts/stability/<date>/telemetry/rollback_drill.log`
- `artifacts/stability/<date>/telemetry/slo_summary.md`

### Required manual follow-up before sign-off

- Add one dated review row for `R1-R5` in [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md).
- Add one dated turnover drill row in [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md).
- Confirm org-boundary row in [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md).
- Add a dated closeout decision note in [DECISIONS.md](DECISIONS.md):
  - Gate C evidence complete for this cycle,
  - write mode remains `dual`,
  - Gate D (`telemetry_only`) deferred.

### Hard blockers (do not sign off)

- missing `operator_scorecard.md`
- missing turnover drill row or owner-cadence review row
- any unresolved telemetry parity delta (strict zero drift for this cycle)
- missing rollback drill artifact in telemetry evidence packet

## Plan Guardrails

- No surveillance expansion.
- No engagement/growth mechanics.
- No widening of teacher control surface without clearer sequencing.
- Every accepted task must reduce support load, ambiguity, or recoverability risk.

## Related Docs

- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
- [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md)
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
- [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md)
- [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md)
