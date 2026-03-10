# Stability Freeze Issue Drafts

Use this file to create the first execution issues for the stability freeze.

## Shared defaults

- Milestone: `Stability Freeze (30 days)`
- Base labels for all issues:
  - `stability-freeze`
  - `ops`
  - `docs`
  - `no-new-primitives`

## Issue 1: Stability freeze kickoff and owner assignment

- Suggested labels:
  - `stability-freeze`
  - `governance`
  - `risk-R1`
  - `risk-R5`
- Owner role:
  - `OD` + `maintainer`

### Description

Adopt [STABILITY_CHARTER.md](STABILITY_CHARTER.md) as active PR policy and assign owner/cadence for all five risks in [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md).

### Tasks

- Assign a named owner and cadence for each risk.
- Add next review date for each risk to the team calendar.
- Confirm freeze checklist is used in review comments.
- Keep owner/cadence/next-review tracking in [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md).

### Done means

- Every risk has a named owner and review date.
- Freeze checklist is visible in active PR reviews.
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md) is current.

---

## Issue 2: Define top 10 teacher tasks (current state)

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `risk-R1`
- Owner role:
  - `OD` + instructor lead

### Description

Document the top 10 real tasks staff perform in `/teach` so stabilization targets current operations, not theoretical workflows.

### Tasks

- Identify top 10 recurring teacher/admin tasks.
- Map each to route and completion signal.
- Add checklist link into stability docs.

### Done means

- One agreed list exists and is linked from stability docs.
- List is used in weekly regression walkthroughs.

---

## Issue 3: Teacher portal declutter pass (copy and ordering only)

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `ux-smoothing`
  - `risk-R1`
- Owner role:
  - `maintainer`

### Description

Reduce operator confusion in `/teach` and `/teach/class/<id>` without adding routes, tabs, models, or workflows.

### Tasks

- Improve copy for existing controls.
- Reorder controls for safer first actions.
- Ensure destructive actions use explicit warning language.
- Add/update tests only where behavior/visibility changes.

### Done means

- First-time instructor can locate class setup, enrollment, invites, exports, and certificates quickly.
- No new primitives were introduced.

---

## Issue 4: Org boundary policy decision and production audit

- Suggested labels:
  - `stability-freeze`
  - `security`
  - `risk-R2`
- Owner role:
  - `OD`

### Description

Choose and document intended posture for `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` and verify production matches policy.

### Tasks

- Confirm intended value (`0` transition vs `1` strict) for current deployment.
- Record who approved any non-strict exception.
- Add next review date.
- Record audit output using [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md).

### Done means

- Current setting is verified and documented.
- Boundary policy is explicit and review-dated.

---

## Issue 5: Add explicit strict-mode-off operator warning

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `hardening`
  - `risk-R2`
- Owner role:
  - `maintainer`

### Description

Add an explicit staff-facing warning when org strict mode is off. UI/copy only; no role or permission model changes.

### Tasks

- Add visible warning indicator in appropriate teacher/admin context.
- Link warning text to policy docs.
- Add/update tests for visibility conditions.

### Done means

- Operators can see boundary posture in normal workflow.
- Warning behavior is test-backed.

---

## Issue 6: Outcomes and certificate semantics canonical note

- Suggested labels:
  - `stability-freeze`
  - `reporting`
  - `risk-R3`
- Owner role:
  - `OD` + fundraising lead

### Description

Create one canonical note that defines outcome event meanings and certificate issuance semantics for staff-facing reporting.

### Tasks

- Define `session_completed`, `artifact_submitted`, `milestone_earned` in plain language.
- Define what certificate issuance does and does not assert.
- Link note from teacher and fundraising docs.

### Done means

- Staff can explain certificate eligibility consistently.
- No competing definitions in docs.

---

## Issue 7: End-to-end reporting rehearsal

- Suggested labels:
  - `stability-freeze`
  - `scenario-testing`
  - `risk-R3`
- Owner role:
  - `OD` + instructor lead

### Description

Run an operational dry run of the full reporting path: join -> submission -> mark completion -> outcomes export -> certificate issue/download.

### Tasks

- Execute full workflow in a rehearsal class.
- Record friction points and ambiguities.
- Convert findings into docs/copy tickets (not new features).
- Record run evidence using [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md).

### Done means

- Rehearsal notes are saved and linked.
- Follow-up tasks are narrowed to stabilization scope.
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md) has a dated evidence row.

---

## Issue 8: Quarterly restore rehearsal baseline and evidence log

- Suggested labels:
  - `stability-freeze`
  - `recovery`
  - `risk-R4`
- Owner role:
  - `OD` + `maintainer`

### Description

Institutionalize restore rehearsal and record outcomes to prevent backup confidence drift.

### Tasks

- Run: `bash scripts/backup_restore_rehearsal.sh --compose-mode prod`
- Record date, pass/fail, and blockers.
- Schedule next quarterly rehearsal.
- Capture artifacts and summary with:
  - `bash scripts/restore_rehearsal_evidence.sh --compose-mode prod --out-dir artifacts/stability/<date>`
- Log the run in [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md).

### Done means

- Most recent rehearsal date is documented.
- Next rehearsal is on calendar with owner.
- [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md) contains a dated evidence row with artifact path.

---

## Issue 9: Retention automation health check and alert path

- Suggested labels:
  - `stability-freeze`
  - `retention`
  - `risk-R4`
- Owner role:
  - `maintainer`

### Description

Verify retention jobs are healthy and observable so retention policy remains operational, not aspirational.

### Tasks

- Verify `classhub-retention.timer` status and recent runs.
- Verify retention command path and optional webhook alert configuration.
- Document monthly verification steps.
- Add and use one command for evidence capture:
  - `bash scripts/retention_health_snapshot.sh --compose-mode prod --out artifacts/stability/<date>/retention_health.log`

### Done means

- Retention status can be checked with a short documented sequence.
- Ops has clear owner for monthly retention verification.
- A dated retention health snapshot artifact exists for the cycle.

---

## Issue 10: Maintainer turnover drill (60 minutes + 1 day)

- Suggested labels:
  - `stability-freeze`
  - `handoff`
  - `risk-R5`
- Owner role:
  - `ED` + `OD` + `maintainer`

### Description

Run a live turnover drill using [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md) to validate docs and expose hidden assumptions.

### Tasks

- Execute 60-minute onboarding path with a backup maintainer.
- Execute first-day path (smoke + policy + recovery orientation).
- Log unclear steps and patch docs immediately.

### Done means

- Backup maintainer can run critical checks without coaching.
- Turnover packet gaps are closed with doc updates.

---

## Issue 11: Day-of-class first-contact lane clarity on `/teach`

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `ux-smoothing`
  - `risk-R1`
- Owner role:
  - `maintainer` + instructor lead

### Description

Improve first-contact clarity for daily teaching actions on `/teach` by tightening section labels/order for top tasks 1-4 in [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md). Copy and ordering only.

### Routes in scope

- `/teach`
- includes under `templates/includes/teach_home/*`

### Tasks

- Ensure first visible language prioritizes:
  - create/open class,
  - share join access,
  - review submission queue.
- Standardize CTA wording for class-opening actions (`Open class`, `Lessons`, `Print join card`) across day/setup surfaces.
- Move admin/operator language below classroom-first language when both are visible.
- Keep existing controls and route contracts unchanged.

### Out of scope

- New tabs, routes, workflows, or RBAC primitives.
- Data model changes.

### Done means

- A first-time teacher can complete top tasks 1-4 from `/teach` without opening docs.
- No conflicting wording for equivalent actions across day/setup panels.
- Capability and guardrail checks pass.

### Verification commands

- `python scripts/check_view_size_budgets.py`
- `python scripts/check_view_function_budgets.py`
- `python scripts/check_teacher_endpoint_capability_map.py`
- `python scripts/check_frontend_static_refs.py`

---

## Issue 12: Class dashboard safety copy pass for destructive actions

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `hardening`
  - `risk-R1`
- Owner role:
  - `maintainer`

### Description

Reduce accidental destructive operations on `/teach/class/<id>` by making reset/delete/lock language explicit and action intent unambiguous. Copy and confirmation-language pass only.

### Routes in scope

- `/teach/class/<id>`
- related teacher templates for class controls

### Tasks

- Normalize destructive-action copy (`reset`, `delete`, `lock`, `rotate code`) to explicit impact language.
- Ensure destructive forms include clear confirmation text and consistent warning tone.
- Keep non-destructive actions visually and textually distinct from destructive actions.
- Add/update tests for text visibility where behavior changes.

### Out of scope

- Permission model or endpoint behavior changes.
- New moderation or policy workflows.

### Done means

- A teacher can distinguish reversible vs irreversible actions at a glance.
- Existing destructive flows retain behavior but are harder to trigger accidentally.
- No route-map or RBAC guard drift.

### Verification commands

- `python scripts/check_view_size_budgets.py`
- `python scripts/check_teacher_endpoint_capability_map.py`
- `python scripts/check_rbac_endpoint_guards.py`
- `python scripts/check_no_inline_template_js.py`
- `python scripts/check_no_inline_template_css.py`

---

## Issue 13: Submission review discoverability and wording consistency

- Suggested labels:
  - `stability-freeze`
  - `teacher-portal`
  - `ux-smoothing`
  - `risk-R1`
- Owner role:
  - `maintainer` + instructor lead

### Description

Make submission review paths obvious and consistent so teachers can reliably complete top task 4 (review/download submissions) from both `/teach` and `/teach/class/<id>`.

### Routes in scope

- `/teach`
- `/teach/class/<id>`
- `/teach/material/<material_id>/submissions` entry links

### Tasks

- Standardize queue-entry wording (`Open queue`, `Review submissions`, `Submissions`) to one canonical phrase.
- Ensure at least one clear submission-review entry appears in classroom-first sections.
- Keep export/download wording consistent between list views and class dashboard.
- Add/update tests where link text assertions or visibility assumptions change.

### Out of scope

- New analytics surfaces.
- Changes to submission data model or export formats.

### Done means

- Teachers can find submission review from the home and class dashboards with no route hunting.
- Equivalent actions have one consistent label.
- Existing endpoint/capability contracts remain intact.

### Verification commands

- `python scripts/check_teacher_endpoint_capability_map.py`
- `python scripts/check_frontend_static_refs.py`
- `python scripts/check_no_inline_template_js.py`
- `python scripts/check_no_inline_template_css.py`

## Related docs

- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
- [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md)
