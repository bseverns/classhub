# Ops Cadence Checklist

Use this checklist for recurring stability operations.

Last updated: March 10, 2026

## Purpose

This document standardizes monthly and quarterly operations so evidence is:
- command-backed
- reviewable
- not dependent on one maintainer's memory

Store run outputs under `artifacts/stability/<YYYY-MM-DD>/` where possible.

## Monthly Checklist

### 1) Runtime health + smoke

```bash
cd /srv/lms/app
bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden
```

Expected:
- `[doctor] ALL CHECKS PASSED`

Evidence:
- `artifacts/stability/<date>/system_doctor.log`

### 2) Accessibility smoke

```bash
cd /srv/lms/app
bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical
```

Expected:
- `[a11y] PASS`

Evidence:
- `artifacts/stability/<date>/a11y_smoke.log`

### 3) Retention health dry-run

```bash
cd /srv/lms/app
bash scripts/retention_maintenance.sh --dry-run
```

Expected:
- command exits `0`
- output clearly shows matched/skipped/deletion candidate counts

Evidence:
- retention dry-run output attached to monthly ops note

### 4) Staff access + org-boundary posture

Manual checks:
- Confirm current `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` runtime value.
- Confirm `/teach` warning posture matches expected policy.
- Confirm recent org membership/class-assignment changes were intentional.
- Record results using [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md).

Evidence:
- monthly access-review note (date, reviewer, decision)

## Quarterly Checklist

### 1) Full restore rehearsal

```bash
cd /srv/lms/app
bash scripts/backup_restore_rehearsal.sh --compose-mode prod
```

Expected:
- rehearsal finishes with explicit success output

Evidence:
- `artifacts/stability/<date>/restore_rehearsal.log`

### 2) Kiosk resilience drill

```bash
cd /srv/lms/app
bash scripts/kiosk_resilience_check.sh --non-interactive
```

Expected:
- report generated and reviewed for open failures/actions

Evidence:
- kiosk resilience report path or attached log

### 3) Reporting semantics review

Manual checks:
- Review [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md) with Ops + ED.
- Confirm threshold policy (`CLASSHUB_CERTIFICATE_MIN_SESSIONS`, `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`) for next cycle.
- Run one full join -> submit -> export -> certificate issue rehearsal using [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md).

Evidence:
- dated semantics review note with approvers
- one evidence row in [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)

## Per-Release Checklist

Preferred:

```bash
cd /srv/lms/app
make stability-evidence STABILITY_RELEASE_DATE=<YYYY-MM-DD> SMOKE_COMPOSE_MODE=prod
```

Expected:
- scorecard generated at `artifacts/stability/<date>/operator_scorecard.md`

If running from a non-docker local workstation:

```bash
cd /srv/lms/app
make stability-evidence STABILITY_RELEASE_DATE=<YYYY-MM-DD> STABILITY_SKIP_DOCKER_CHECKS=1
```

## Evidence Log Template

| Date | Cadence | Operator | Run command | Result | Artifact path | Follow-up |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | monthly / quarterly / release | name | `...` | PASS / FAIL | `artifacts/stability/...` | yes/no |

## Escalation Rules

- Failed restore rehearsal: pause feature deploys until corrected and re-run.
- Failed smoke/a11y on release candidate: do not ship.
- Retention dry-run anomalies (unexpected high deletes): escalate to Ops Director before live prune.
- Missing evidence artifacts: cadence run is incomplete.

## Related docs

- [RUNBOOK.md](RUNBOOK.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [TURNOVER_PACKET.md](TURNOVER_PACKET.md)
- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
