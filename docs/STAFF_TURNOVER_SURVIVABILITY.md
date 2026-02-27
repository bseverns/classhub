# Staff Turnover Survivability

## Summary

This document is the two-year resilience blueprint for keeping ClassHub operational through staff turnover. The point is not to eliminate human judgment. The point is to make sure the critical judgment is documented, rehearsed, and not trapped in one person's head.

## If the maintainer disappears tomorrow

Do these first, in order:

1. Identify the current deployment owner and the person holding server access.
2. Confirm the location of the repo, the production host, backups, and the password manager entries for env secrets.
3. Read these docs in order:
   - [RUNBOOK.md](RUNBOOK.md)
   - [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
   - [SECURITY.md](SECURITY.md)
   - [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
4. Run the lowest-risk confidence checks:
   - `bash scripts/system_doctor.sh --smoke-mode golden`
   - `bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers`
5. Verify current backups exist before changing anything.
6. Confirm who can currently access `/teach` and whether `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` is the intended value.
7. Do not ship new features until restore rehearsal, smoke, and staff access review are understood.

## New maintainer onboarding

### First 60 minutes

The new maintainer should be able to:

- identify the two-service architecture (`classhub` + `homework_helper`)
- find the production env/secrets source of truth
- run smoke checks without editing application code
- explain the privacy boundary: no surveillance analytics, no helper prompt archive
- locate the docs for restore, retention, accessibility, and teacher operations

### First day

The new maintainer should be able to:

- run `system_doctor` and read the result without help
- run `backup_restore_rehearsal.sh` or shadow it with ops
- identify the current org-boundary policy and staff-role model
- trace the certificate/outcomes path from teacher UI to code and docs
- review recent deploy and smoke history

### First week

The new maintainer should be able to:

- handle a routine deploy safely
- verify retention automation status
- offboard or onboard a teacher with ops using the documented process
- explain the top five maintenance risks and current freeze or stability posture
- update docs and tests for a small hardening change without widening scope

## Minimum recurring rituals

These rituals must survive personnel changes.

### Monthly

- run smoke checks on the current stack
- review staff access and org-boundary policy
- verify recent backups exist
- review whether retention automation is healthy

### Quarterly

- run full restore rehearsal: `bash scripts/backup_restore_rehearsal.sh --compose-mode prod`
- run accessibility smoke: `bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers`
- run security posture review against current deployment settings
- review certificate threshold values and reporting semantics with ops

### Before each release or significant deploy

- run `bash scripts/system_doctor.sh --smoke-mode golden`
- confirm no privacy boundary changed unintentionally
- verify docs touched by the change still match the code

## What knowledge must live in docs

The following knowledge is too important to leave in someone's head:

- where production env secrets live
- how to restore from zero and what values must match pre-incident policy
- how org access actually works, including strict mode vs fallback mode
- what counts as an outcome event and what certificate issuance means
- how retention is enforced and how deletion guardrails work
- which checks are required before deploy and after incident recovery
- how to onboard, offboard, and hand off teacher accounts safely
- what the helper does not retain or expose

## What to automate

Automate anything that is repetitive, objective, and safer when run consistently.

Keep automated:

- smoke checks where scripts already exist
- accessibility smoke where scripts already exist
- retention maintenance scheduling
- backup creation where scripts already exist
- CI guardrails that catch template, view-budget, or routing regressions

## What to keep manual

Keep manual anything that requires judgment, policy confirmation, or stakeholder context.

Keep manual:

- deciding whether org strict mode should be enabled for a deployment
- offboarding decisions that affect access timing and staff transitions
- interpreting pilot observations from instructors
- deciding whether a restore is necessary versus a simpler fix
- freeze exceptions and scope decisions
- external reporting claims about outcomes or certificates

## Turnover packet contents

Keep a lightweight turnover packet in a shared location outside any one person's laptop. It should contain:

- production host and access ownership
- current `compose/.env` source-of-truth location
- backup locations and restore rehearsal date
- current staff access policy and org strict-mode value
- current certificate threshold values
- last known-good deploy command and smoke command sequence
- links to the current runbook, recovery, accessibility, and teacher portal docs
- open operational risks that are still being tolerated on purpose

## Red flags that survivability is slipping

- only one person knows how to run restore rehearsal
- deploy steps are copied from chat instead of docs
- staff access problems are resolved ad hoc without policy review
- reporting semantics differ depending on who explains them
- smoke checks are skipped because "nothing changed"
- docs describe the happy path but not the recovery path

## Related docs

- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [RUNBOOK.md](RUNBOOK.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- [ACCESSIBILITY.md](ACCESSIBILITY.md)
