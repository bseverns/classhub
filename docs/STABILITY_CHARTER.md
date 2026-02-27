# Stability Charter

## Summary

For the next 30 days, ClassHub is in a stability freeze. The goal is to reduce long-term maintenance risk, simplify day-to-day operation, and make the system survivable under staff turnover.

This is not a feature freeze in name only. The default answer to new product ideas during this window is "not now."

## Freeze period

- Start: when this charter is adopted
- End: 30 calendar days later
- Scope: `services/classhub/`, `services/homework_helper/`, deployment scripts, smoke checks, and operator-facing docs

## What is allowed

Only work that makes the system more boring to operate is allowed.

### 1. UX smoothing

Small changes to existing screens are allowed when they:

- remove confusion from current teacher/admin flows
- reduce accidental misuse
- improve labels, warnings, sequencing, or progressive disclosure
- do not add a new route, workflow primitive, or data model

Examples:

- clearer copy in `/teach`
- more explicit warnings around destructive actions
- moving existing controls into a safer order

### 2. Docs clarity

Allowed when the change:

- shortens time-to-understanding for ED, OD, instructors, or maintainers
- replaces tribal knowledge with explicit checklists
- links to existing deep docs instead of duplicating them

### 3. Scenario testing

Allowed when the change:

- covers an already-supported workflow
- tightens smoke, restore, accessibility, permission, or handoff confidence
- adds tests for existing invariants

Examples:

- invite-only cohort smoke
- certificate eligibility/export path checks
- offboarding and org-boundary tests

### 4. Observability without surveillance

Allowed when the change:

- helps operators detect breakage or drift
- does not create new student profiling or AI transcript retention
- stays within existing privacy posture

Examples:

- better operator-facing notices
- health-check clarity
- backup/retention verification output

### 5. Hardening

Allowed when the change:

- reduces blast radius
- closes permission ambiguity
- strengthens append-only or deletion guardrails
- improves recovery or secret handling without adding new product behavior

## What is not allowed

During the freeze, do not ship:

- new product features
- new tabs, new major teacher workflows, or new role types
- new analytics primitives
- AI transcript retention or expanded helper memory
- new billing, CRM, gradebook, or surveillance capabilities
- schema changes unless a bug fix is truly unavoidable and smaller than the operational risk of leaving it alone

## Exception process

Exceptions must be rare.

Approve an exception only if all of the following are true:

1. The change fixes an active defect, security issue, data-loss risk, or staff-blocking operational failure.
2. The change is smaller than the risk of postponing it.
3. The change does not introduce a new primitive or long-term maintenance surface.
4. The change includes tests and doc updates where relevant.
5. The PR description explicitly says `Freeze exception` and explains why delay is riskier.

Required reviewers for a freeze exception:

- Maintainer
- Ops Director for operational changes
- Executive Director only when the change affects policy, risk, or public commitments

## Stability work categories

| Category | Goal | Allowed outputs |
| --- | --- | --- |
| UX smoothing | Reduce staff confusion in current flows | copy updates, control ordering, warnings, progressive disclosure |
| Docs clarity | Move operational knowledge out of people's heads | quickstarts, turnover docs, scenario playbooks, reviewer checklists |
| Scenario testing | Prove existing workflows still work | smoke additions, regression tests, permission tests, restore rehearsal |
| Observability (non-surveillance) | Detect failure and drift without profiling learners | health checks, status messages, operator verification steps |
| Hardening | Reduce accidental breakage or overreach | permission tightening, deletion guardrails, safer defaults, explicit policy checks |

## Reviewer checklist

Before approving a freeze-period change, ask:

1. Are we adding a new primitive, or only stabilizing an existing one?
2. Does this make the teacher portal easier to operate, or just more capable?
3. Are privacy boundaries unchanged or tighter?
4. Are we storing any new student or helper data? If yes, stop.
5. Does this reduce risk for staff turnover in two years?
6. Is there a smaller change that would achieve the same stability outcome?
7. Are tests and docs aligned with the change?

## End-of-freeze exit criteria

The freeze should only end when these are true:

- the top maintenance risks have named owners and recurring checks
- core teacher flows are documented in short operational language
- restore rehearsal, accessibility smoke, and retention checks are routine rather than ad hoc
- new contributors can identify what not to change without re-learning the entire codebase

## Related docs

- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
