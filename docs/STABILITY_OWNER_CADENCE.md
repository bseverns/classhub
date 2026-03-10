# Stability Owner + Cadence Tracker

This document is the governance tracker for the five maintenance risks in the stability register.

Last updated: March 10, 2026

## Purpose

Use this file to make ownership and review cadence explicit:
- who owns each risk
- who is backup owner
- when the next review is due
- where evidence is stored

## Risk Ownership Matrix

| Risk ID | Risk title | Primary owner role | Backup owner role | Cadence | Next review date | Evidence location |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Teacher portal surface area | Maintainer + Ops Director | Teacher Lead | Monthly | 2026-04-10 | `artifacts/stability/<date>/operator_scorecard.md` + teacher walkthrough notes |
| R2 | Org boundary fallback drift | Ops Director | Executive Director | Monthly | 2026-04-10 | [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md) |
| R3 | Outcomes/certificate semantic drift | Ops Director | Executive Director | Monthly | 2026-04-10 | [OUTCOME_SEMANTICS.md](OUTCOME_SEMANTICS.md) review notes + [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md) evidence row |
| R4 | Retention/recovery ritual drift | Ops Director + Maintainer | Engineering manager | Monthly retention, quarterly restore | 2026-04-10 (monthly), 2026-06-10 (quarterly) | `artifacts/stability/<date>/restore_rehearsal.log` + `artifacts/stability/<date>/retention_health.log` |
| R5 | Turnover survivability dependence | Executive Director + Ops Director + Maintainer | Secondary maintainer | Quarterly | 2026-06-10 | [TURNOVER_PACKET.md](TURNOVER_PACKET.md) drill notes |

## Review Run Template

Use one row per review cycle.

| Date | Risk IDs reviewed | Reviewer(s) | Result | Follow-up actions | Due date | Evidence path |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | R1,R2 | names/roles | pass / concerns | short list | YYYY-MM-DD | `artifacts/stability/...` |

## Completion Rule For Issue 1

Issue 1 is complete when:
- every risk in [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md) has:
  - primary owner role
  - backup owner role
  - cadence
  - next review date
- this tracker is referenced from active stability docs

## Related docs

- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [STABILITY_ISSUES.md](STABILITY_ISSUES.md)
- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
