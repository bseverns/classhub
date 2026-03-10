# Outcome + Certificate Semantics

This is the canonical meaning of outcome events and certificate status in ClassHub.

Last updated: March 10, 2026

## Why this exists

Use this note so teachers, operations, and external reporting use the same terms.

Without this contract, dashboards can be technically correct but interpreted differently across teams.

## Canonical event definitions

### `artifact_submitted`

Meaning:
- A student successfully submitted an artifact for a material.

Emission rule:
- One event per successful submission.
- Multiple submissions can produce multiple `artifact_submitted` events.

What it does **not** mean:
- It does not mean quality mastery.
- It does not mean a full class session was completed.

### `session_completed`

Meaning:
- A student is counted as having completed a class session/module for rollup purposes.

Emission rules:
- Automatically once per student+module on first successful artifact in that module.
- Manually by teacher via `Mark session completed` for offline/sessionless completion paths (only if absent).

What it does **not** mean:
- It is not attendance telemetry.
- It is not a competency grade.

### `milestone_earned`

Meaning:
- A student completed a material-triggered engagement milestone.

Common triggers:
- checklist completed
- first non-empty reflection save
- first rubric save with score/feedback

What it does **not** mean:
- It does not imply certificate eligibility by itself.
- It does not imply graded mastery.

## Certificate semantics

### `eligible`

Meaning:
- Student has reached current class threshold policy:
  - `CLASSHUB_CERTIFICATE_MIN_SESSIONS`
  - `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`

Notes:
- Eligibility is threshold-based rollup logic, not a hidden scoring model.
- Eligibility can change as additional events are recorded.

### `issued`

Meaning:
- A `CertificateIssuance` record exists for that student+class.
- Issuance captures a signed snapshot of counts/thresholds at issue time.

Notes:
- Certificates may be re-issued in place for the same student+class.
- Issuance is an explicit teacher/admin action, not an automatic side effect of eligibility.

What `issued` does **not** mean:
- It does not guarantee current eligibility still matches the exact historical issue moment unless you inspect the issuance snapshot.

## Reporting language contract

When writing internal or external reports:

- Say: "eligible under current session/artifact thresholds."
- Say: "certificate issued/re-issued on <date>."
- Do not say: "AI graded mastery" or "behavior score."
- Do not imply hidden analytics beyond recorded outcome/certificate events.

## Operator checks

Use these to validate semantics operationally:

```bash
cd /srv/lms/app
bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden
```

```bash
cd /srv/lms/app
python3 scripts/check_test_inventory_coverage.py
```

For class-level review:
- `/teach/class/<id>/certificate-eligibility`
- `/teach/class/<id>/export-outcomes-csv`
- `/teach/class/<id>/export-summary-csv`

## Related docs

- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- [RUNBOOK.md](RUNBOOK.md)
- [DECISIONS.md](DECISIONS.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
