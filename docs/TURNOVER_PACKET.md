# Turnover Packet (v1)

This is the operational handoff packet for keeping ClassHub stable during maintainer transitions.

Last updated: March 10, 2026

## Purpose

Use this document when:
- a new maintainer takes over operations
- on-call ownership changes
- leadership asks for current operational readiness evidence

Outcomes:
- a new maintainer can run core checks in under 60 minutes
- first-week confidence checks are explicit and repeatable
- owner/backup/cadence responsibilities are visible in one place

## Access + Prerequisites

Before running anything, confirm:
- repo path on server: `/srv/lms/app`
- access to secrets source of truth for `compose/.env`
- docker access on target host
- access to release evidence folder `artifacts/stability/<date>/`

Primary references:
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)

## 60-Minute Safe Takeover Path

Run in order.

### 0-10 minutes: orientation

1. Confirm current deployment host and repo location.
2. Confirm who currently owns production secrets and server SSH.
3. Read:
   - [RUNBOOK.md](RUNBOOK.md)
   - [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)

### 10-30 minutes: baseline runtime confidence

```bash
cd /srv/lms/app
bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden
```

```bash
cd /srv/lms/app
bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical
```

### 30-45 minutes: restore and retention confidence

```bash
cd /srv/lms/app
bash scripts/backup_restore_rehearsal.sh --compose-mode prod
```

```bash
cd /srv/lms/app
bash scripts/retention_maintenance.sh --dry-run
```

### 45-60 minutes: policy and boundary posture

1. Confirm current `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` value in runtime env.
2. Confirm teacher/admin access posture in `/teach`.
3. Record policy check output in [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md).
4. Confirm last evidence pack location and scorecard:

```bash
cd /srv/lms/app
ls -1 artifacts/stability | tail -n 3
```

```bash
cd /srv/lms/app
cat artifacts/stability/<YYYY-MM-DD>/operator_scorecard.md
```

## First-Week Confidence Path

### Day 1

- Run `make smoke-full` on production profile.
- Confirm latest release evidence pack exists.
- Confirm restore rehearsal output is stored and reviewable.

### Day 2-3

- Walk top teacher workflows from [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md).
- Verify no drift between docs and current `/teach` behavior.
- Record friction items as stabilization-only tickets (copy/order/clarity).

### Day 4-5

- Review org boundary posture and staff memberships with Ops Director.
- Review outcome/certificate semantics with Executive Director.
- Confirm next monthly and quarterly rituals are calendared.

## Command Checklist

Run from `/srv/lms/app`.

### Release sign-off

- `make stability-evidence STABILITY_RELEASE_DATE=<YYYY-MM-DD> SMOKE_COMPOSE_MODE=prod`
- `python3 scripts/check_test_inventory_coverage.py`

### Monthly operations

- `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode golden`
- `bash scripts/a11y_smoke.sh --compose-mode prod --fail-impact critical`
- `bash scripts/retention_maintenance.sh --dry-run`

### Quarterly survivability

- `bash scripts/backup_restore_rehearsal.sh --compose-mode prod`
- `bash scripts/kiosk_resilience_check.sh --non-interactive`

### Incident triage baseline

- `bash scripts/system_doctor.sh --compose-mode prod --smoke-mode basic`
- `cd compose && docker compose ps`
- `cd compose && docker compose logs --tail=200 classhub_web helper_web caddy`

## Owner + Backup Matrix

| Responsibility | Primary role | Backup role | Artifact/evidence path |
| --- | --- | --- | --- |
| Release evidence generation | Maintainer | Secondary maintainer | `artifacts/stability/<date>/operator_scorecard.md` |
| Restore rehearsal execution | Ops Director | Engineering manager | `artifacts/stability/<date>/restore_rehearsal.log` |
| Retention health verification | Maintainer | Ops Director | `artifacts/stability/<date>/guardrails.log` + retention run output |
| Staff access + org boundary review | Ops Director | Executive Director | policy review notes + `/teach` admin checks |
| Final release sign-off | Executive Director | Ops Director | release scorecard + manual sign-off notes |

## Cadence Table

| Cadence | Required activity | Owner | Output |
| --- | --- | --- | --- |
| Per release | Run full stability evidence pack | Maintainer | `artifacts/stability/<date>/` folder |
| Monthly | Smoke + a11y + retention dry-run | Maintainer + Ops Director | monthly ops note with command outputs |
| Quarterly | Restore rehearsal + kiosk resilience | Ops Director | rehearsal logs + follow-up actions |
| Quarterly | Staff access and org-boundary review | Ops Director + Executive Director | access review notes + policy confirmation |

## Evidence Log Template

Use this for handoff notes and leadership review.

| Date | Operator | Command/run | Result | Artifact path | Follow-up needed |
| --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | name | `make stability-evidence ...` | PASS/FAIL | `artifacts/stability/<date>/operator_scorecard.md` | yes/no |

## Escalation Rules

- If restore rehearsal fails: freeze feature deploys until restore path is healthy.
- If smoke fails on release candidate: do not promote release.
- If org-boundary posture is unclear: escalate to Ops Director + Executive Director before staff access changes.
- If evidence artifacts are missing: release is not signed off.

## Related Docs

- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)
- [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md)
