# Org Boundary Policy Audit

Use this document to run and record the monthly org-boundary posture review.

Last updated: March 10, 2026

## Scope

This audit verifies that deployment policy and runtime behavior match for:
- `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF`
- staff access boundary expectations in `/teach`

Policy intent:
- production default should be strict mode (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`) unless an approved transition exception is active.

## Audit Procedure

Run on the production host.

### 1) Capture configured value (`compose/.env`)

```bash
cd /srv/lms/app
grep '^REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=' compose/.env
```

### 2) Capture runtime value (inside Django settings)

```bash
cd /srv/lms/app/compose
docker compose exec -T classhub_web python manage.py shell -c "from django.conf import settings; print(int(bool(getattr(settings, 'REQUIRE_ORG_MEMBERSHIP_FOR_STAFF', False))))"
```

Expected output:
- `1` for strict mode
- `0` only when an approved migration exception is active

### 3) Verify UI boundary signal

Manual check:
1. Sign in to `/teach` as a superuser.
2. Confirm warning banner behavior:
   - strict mode `1`: warning is not shown.
   - fallback mode `0`: warning is shown:
     - `Org-boundary warning: strict org membership mode is currently off...`

### 4) Confirm staff access sample

Manual check:
- test at least one non-superuser staff account with expected org membership scope.
- confirm class visibility matches intended org boundaries.

## Evidence Record Template

Fill one row per audit run.

| Audit date | Deployment | Reviewer | Approver | Intended policy value | Configured value (`.env`) | Runtime value | UI warning state | Exception approved? | Exception owner | Exception end date | Next review date | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-10 | prod | ben | ben | `1` | `1` | `1` | hidden | no | n/a | n/a | 2026-04-10 | Strict mode confirmed. Ben memberships (`createMPLS` teacher, `testorg` owner) resolved class visibility after scoping classes. UI move workflow produced `class.organization.set` audit events for class `2` at `2026-03-10T20:40:29Z` and `2026-03-10T20:40:41Z`. |
| YYYY-MM-DD | prod | name | name | `1` | `1` | `1` | hidden/shown | yes/no | name | YYYY-MM-DD | YYYY-MM-DD | brief notes |

## Acceptance Criteria

Audit is complete only when:
- configured and runtime values are recorded
- warning-banner state is recorded
- reviewer + approver names are recorded
- next review date is explicitly set

## Escalation

- If configured and runtime values differ: stop release sign-off, fix env/runtime drift, re-run audit.
- If fallback mode (`0`) is active without recorded approval: escalate to Ops Director + Executive Director immediately.
- If staff sample access does not match expected org scope: treat as policy/control incident and pause non-emergency deploys.

## Related docs

- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [ORG_BOUNDARY_EXPLAINER.md](ORG_BOUNDARY_EXPLAINER.md)
- [RUNBOOK.md](RUNBOOK.md)
- [OPS_CADENCE_CHECKLIST.md](OPS_CADENCE_CHECKLIST.md)
