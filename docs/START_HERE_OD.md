# Start Here: Ops Director

## What ClassHub is

ClassHub is an operations-friendly learning hub for running cohorts, managing staff access by `Organization`, controlling enrollment, exporting outcomes, and rehearsing recovery from backups.

## What ClassHub is not

- It is not a hands-off SaaS with opaque admin controls.
- It is not a student identity provider.
- It is not a substitute for ops discipline around backups, restore drills, and role assignment.

## 5-minute overview

1. Staff authenticate in `/teach`.
2. Superusers can manage organizations and staff memberships in the teacher portal.
3. Teachers can set `Enrollment mode` to `Open`, `Invite only`, or `Closed`.
4. Invite links can expire and enforce seat caps.
5. Ops can rely on exports, backup/restore rehearsal, and documented smoke checks.

## What success looks like

- The right staff can access the right classes without sharing accounts.
- Invite-only cohorts can open and close cleanly.
- Routine reporting is export-driven, not screenshot-driven.
- Restore rehearsal is documented and repeatable.
- Incidents have a known path: troubleshoot, restore, verify, communicate.

## Where revenue can come from

ClassHub does not create revenue by itself. What it does do is make a few earned-income models easier to operate without adding a large admin burden:

- paid cohorts with controlled enrollment using `Invite link` + seat caps
- partner-funded classes where each `Organization` or cohort needs bounded staff access
- completion-based programs that need `Outcomes export` and `Certificate eligibility/issuance`
- repeat offerings where staff can reuse the same operating pattern instead of rebuilding from scratch

The operational question is not "Can the software sell?" It is "Can staff run a paid or sponsored program cleanly enough that the margin is not eaten by manual admin work?"

## Revenue-support signals to watch

- time from cohort announcement to first successful student join
- number of invite/support issues per cohort
- staff time spent on roster cleanup and closeout reporting
- time to produce completion evidence for a partner or payer
- certificate issuance rate for programs that promise a completion artifact

## Risks avoided

- Avoids broad staff access when org boundaries are configured and reviewed.
- Avoids storing more student identity data than the workflow needs.
- Avoids silent data loss by requiring backups and recovery rehearsal.
- Avoids helper data sprawl by not storing helper prompt content.

## What to review next

- Daily and weekly operating procedures: [RUNBOOK.md](RUNBOOK.md)
- Teacher portal permissions, org access, and exports: [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- Revenue-oriented program framing: [PROGRAM_LIFECYCLE.md](PROGRAM_LIFECYCLE.md), [START_HERE_FUNDRAISING.md](START_HERE_FUNDRAISING.md)
- Restore and recovery process: [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
- Security baseline and staff/org boundary controls: [SECURITY.md](SECURITY.md)
- Common break/fix playbooks: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
