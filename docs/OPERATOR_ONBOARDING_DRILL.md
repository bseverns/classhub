# Operator Onboarding Drill

## Summary

Use this drill to verify that a new operator can run the stack’s core health checks, find the right docs, and produce a short evidence log without relying on oral tradition.

This is an onboarding and survivability drill, not a product demo.

## What to do now

1. Pick a date-stamped evidence directory.
2. Run the commands below in order.
3. Fill in the evidence log template at the end of this page.

Recommended bootstrap:

```bash
python3 scripts/init_operator_onboarding_drill.py --operator "<name>" --environment "<env-label>"
```

That command creates the dated evidence directory, pre-fills `operator_onboarding_log.md`, and stubs the files the operator is expected to fill during the drill.
It also creates `turnover_drill_log_row.md`, a paste-ready dated row for [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md).

If you want the generator to append the row directly into the canonical log:

```bash
python3 scripts/init_operator_onboarding_drill.py \
  --operator "<name>" \
  --environment "<env-label>" \
  --next-drill-date YYYY-MM-DD \
  --append-turnover-log
```

## Drill steps

| Step | Expected command | Expected signal | Where to paste evidence |
| --- | --- | --- | --- |
| 1. Run system doctor | `bash scripts/system_doctor.sh` | Ends without fatal errors; helper/local smoke lane is understandable | `operator_onboarding_doctor.log` |
| 2. Run smoke | `bash scripts/smoke_check.sh --strict` | Health endpoints and core flows pass, or failures are clearly named | `operator_onboarding_smoke.log` |
| 3. Export operator remote-compute snapshot | `DJANGO_DEBUG=1 DJANGO_SECRET_KEY=test-secret .venv_test/bin/python services/classhub/manage.py export_remote_compute_operator_snapshot` or production equivalent inside `classhub_web` | JSON includes `status`, `aggregate_signal`, and recent class rows | `remote_compute_operator_snapshot.json` |
| 4. Capture retention evidence | `bash scripts/retention_health_snapshot.sh --compose-mode prod --out artifacts/stability/$(date +%F)/operator_onboarding_drill/retention_health.log` | Timer state, recent logs, and dry-run output are visible in one file | `retention_health.log` |
| 5. Find token rotation reference | Open [SECRET_ROTATION.md](SECRET_ROTATION.md) | Operator can point to the exact secret section needed for the current scenario | Record the section heading used |
| 6. Explain current remote-compute state | Read [EVIDENCE_REMOTE_COMPUTE.md](EVIDENCE_REMOTE_COMPUTE.md) and the exported snapshot | Operator can explain `quiet`, `calm`, `watch`, `attention`, `unavailable` without guessing | One short paragraph in the log |
| 7. Identify degraded-helper triage path | `bash scripts/check_llm_backend.sh --probe-chat` plus [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [RUNBOOK.md](RUNBOOK.md), and [REMOTE_HELPER_COMPUTE_CONTROL.md](REMOTE_HELPER_COMPUTE_CONTROL.md) | Operator can say whether the remote path is degraded and whether local/default helper remains available | `degraded_helper_triage.md` |
| 8. Find class-scoped remote helper export path | `/teach/class/<id>/export-helper-remote-snapshot?format=json` or `csv` | Operator can point to the class-scoped export path without exposing provider internals | Record example URL or class id used |
| 9. Name the canonical truth docs when claims conflict | [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md) and [DOCS_TRUTH_MECHANISM.md](DOCS_TRUTH_MECHANISM.md) | Operator can explain which docs win and why | One short paragraph in the log |

## Notes for the operator

- The remote helper path is optional and bounded. Do not describe a degraded remote path as a full classroom outage if local/default helper remains available.
- If the snapshot shows `attention`, say “needs operator attention,” not “class is broken.”
- If the snapshot shows `unavailable`, treat that as a status-path problem first, not as proof that the helper lane is down.
- Use [RUNBOOK.md](RUNBOOK.md) for command flow, [SECRET_ROTATION.md](SECRET_ROTATION.md) for trust-boundary secrets, and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for failure classification.

## Evidence log template

If you do not use `python3 scripts/init_operator_onboarding_drill.py`, copy this into `artifacts/stability/<date>/operator_onboarding_drill/operator_onboarding_log.md` and fill it in.

```md
# Operator Onboarding Drill Log

- Date:
- Operator:
- Host:
- Environment:

## Step 1 — System doctor
- Command:
- Result:
- Evidence file:

## Step 2 — Smoke
- Command:
- Result:
- Evidence file:

## Step 3 — Remote-compute operator snapshot
- Command:
- Aggregate signal:
- What it means:
- Evidence file:

## Step 4 — Retention evidence
- Command:
- Timer state:
- Dry-run result:
- Evidence file:

## Step 5 — Token rotation lookup
- Secret involved:
- Correct doc section:
- Rotation impact in one sentence:

## Step 6 — Current remote-compute state explanation
- Current signal level:
- Students affected?
- What should staff do now?

## Step 7 — Degraded-helper triage
- Probe command:
- Outcome:
- Is local/default helper still available?
- Next operator action:

## Step 8 — Class-scoped export path
- Example class id:
- Export URL or command:

## Step 9 — Canonical docs when claims conflict
- Which docs are canonical here:
- Why:

## Operator got stuck here
- Step:
- Symptom:
- What was unclear:
- What should become a calmer artifact:
```

## Related docs

- [START_HERE.md](START_HERE.md)
- [RUNBOOK.md](RUNBOOK.md)
- [SECRET_ROTATION.md](SECRET_ROTATION.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [EVIDENCE_REMOTE_COMPUTE.md](EVIDENCE_REMOTE_COMPUTE.md)
- [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md)
