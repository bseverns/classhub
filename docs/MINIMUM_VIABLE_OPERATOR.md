# Minimum Viable Operator

This is the minimum skill floor for safely operating ClassHub in production.
It is intentionally short. If an operator cannot do these items, they are not yet ready to own production alone.

Last updated: March 11, 2026

## Required access

- SSH access to the production host
- read access to `compose/.env` source of truth
- ability to run Docker Compose commands
- ability to read artifacts under `artifacts/stability/<date>/`

## Must-do checks (no code changes required)

Run from `/srv/lms/app`:

```bash
bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden
bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical
python3 scripts/check_runtime_policy_lock.py --profile baseline --env-file compose/.env
```

Release-cycle closeout command:

```bash
make stability-cycle-closeout STABILITY_RELEASE_DATE=<YYYY-MM-DD> SMOKE_COMPOSE_MODE=prod TELEMETRY_WINDOW_DAYS=7
```

## Must understand (plain language)

- Student auth is class-code + display-name; no student password database in MVP.
- Staff access can be strict (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`) or fallback (`0`); production should be strict unless an approved exception exists.
- Certificates are threshold/event signals, not transcript-grade assertions.
- Restore confidence is evidence-backed (`restore_rehearsal_*` artifacts), not assumed.

## Must be able to answer quickly

- What changed in the last release?
- Where is the latest operator scorecard?
- Is org-boundary mode strict right now?
- When was restore rehearsal last run, and did it pass?
- Who approves fallback-policy exceptions?

## Escalate immediately when

- `check_runtime_policy_lock.py --profile release` fails during closeout
- restore rehearsal fails or artifacts are missing
- smoke/a11y checks fail on a release candidate
- staff access scope does not match expected org boundaries
- policy fallback (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`) is active without written approval

## Evidence paths to know

- `artifacts/stability/<date>/operator_scorecard.md`
- `artifacts/stability/<date>/EVIDENCE_INDEX.md`
- `artifacts/stability/<date>/restore_rehearsal_summary.md`
- `artifacts/stability/<date>/telemetry/summary.md`
- `docs/ORG_BOUNDARY_POLICY_AUDIT.md` evidence table

## If this page feels too advanced

Start here in order:

1. [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md)
2. [RUNBOOK.md](RUNBOOK.md)
3. [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
