# End-to-End Reporting Rehearsal

Use this playbook to run and record the Risk R3 reporting rehearsal.

Last updated: March 10, 2026

## Scope

This rehearsal validates the full operator path:
- student join
- artifact submission
- session completion rollup
- outcomes export
- certificate eligibility and issuance

Use this during the stability freeze and quarterly operations reviews.

## Preconditions

- Deployment is healthy:
  - `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`
- A rehearsal class exists with at least one module/material.
- A teacher/admin account is available for `/teach`.
- Certificate thresholds are known:
  - `CLASSHUB_CERTIFICATE_MIN_SESSIONS`
  - `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`

## Rehearsal Procedure

### 1) Capture threshold settings

```bash
cd /srv/lms/app
grep -E '^CLASSHUB_CERTIFICATE_MIN_(SESSIONS|ARTIFACTS)=' compose/.env
```

### 2) Student join + submit

Manual checks:
1. Join rehearsal class from `/join` with a test display name.
2. Open one material and submit one artifact.
3. Confirm teacher queue shows the submission.

### 3) Session completion path

Manual checks:
1. Open `/teach/class/<id>/certificate-eligibility`.
2. Confirm the student appears in eligibility rows.
3. If needed for offline-path validation, use `Mark session completed`.

### 4) Export path

Manual checks:
1. From `/teach/class/<id>/certificate-eligibility`, export outcomes CSV.
2. Export summary CSV.
3. Save both outputs under `artifacts/stability/<YYYY-MM-DD>/`.

### 5) Certificate path

Manual checks:
1. Identify at least one eligible student.
2. Issue or re-issue certificate.
3. Download PDF or TXT certificate and store evidence path.

### 6) Semantics review

Manual checks:
1. Compare observed behavior with [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md).
2. Record any ambiguous wording or interpretation drift.
3. Open stabilization-only follow-up issues for copy/docs gaps.

## Evidence Record Template

Fill one row per rehearsal run.

| Rehearsal date | Deployment | Reviewer(s) | Class id/code | Thresholds (`sessions/artifacts`) | Student sample | Outcomes export path | Summary export path | Certificate issued? | Semantics drift found? | Follow-up ticket(s) | Next review date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | prod | names | `<id>/<code>` | `X/Y` | `display_name` | `artifacts/stability/...` | `artifacts/stability/...` | yes/no | yes/no | issue refs | YYYY-MM-DD |

## Done Criteria

Rehearsal is complete only when:
- full join -> submit -> export -> issue flow is exercised
- export and certificate evidence paths are recorded
- semantics review is recorded against [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md)
- next review date is set

## Escalation

- If exports fail or data is inconsistent with UI rollups: escalate to Ops Director + Maintainer before next release.
- If certificate eligibility behavior is unclear to operators: block release sign-off until wording/docs are corrected.
- If semantics drift is found between teams (ops/fundraising/teachers): review and re-approve [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md).

## Related docs

- [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)
- [RUNBOOK.md](RUNBOOK.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [STABILITY_ISSUES.md](STABILITY_ISSUES.md)
