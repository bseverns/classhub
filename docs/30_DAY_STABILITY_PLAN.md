# 30-Day Stability Plan

## Summary

This is a four-week stability plan for ClassHub. It does not add features. It reduces operational ambiguity, trims maintenance risk, and proves the existing system can survive ordinary staff turnover.

## Week 1: Freeze, inventory, and simplify the teacher portal entry path

### Objectives

- establish the freeze rules
- identify the current top teacher/admin flows that actually matter
- reduce first-contact confusion in the teacher portal without adding anything new

### Concrete tasks

- Adopt [STABILITY_CHARTER.md](STABILITY_CHARTER.md) and use it in review.
- Inventory the top 10 teacher tasks performed through `/teach`.
- Walk the current `/teach` entry path with one instructor and one ops person.
- Remove or reorder confusing copy in the existing portal where the same meaning is repeated.
- Review destructive teacher actions and confirm warnings are explicit and proportionate.
- Confirm `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` policy for the live deployment and write it down in the ops packet.

### Acceptance criteria

- reviewers are using the freeze checklist in PRs
- there is one agreed list of core teacher tasks
- `/teach` has a clearer start path without adding routes or controls
- org boundary policy is written, not assumed

### Done means...

- a new staff member can identify where to start in `/teach` in under 2 minutes
- the team can state whether org strict mode is on or off without checking chat history
- no feature work was merged under the label of "cleanup"

## Week 2: Stabilize outcomes, certificates, and reporting language

### Objectives

- align staff understanding of outcomes and certificates with the real code paths
- make reporting semantics boring and repeatable
- reduce the chance that fundraising, ops, and teaching staff tell different stories

### Concrete tasks

- Review the current outcomes flow in `/teach/class/<id>/certificate-eligibility`.
- Verify the configured values of `CLASSHUB_CERTIFICATE_MIN_SESSIONS` and `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`.
- Create one internal note that defines what counts as `session_completed`, `artifact_submitted`, and certificate issuance.
- Rehearse the full path: join -> submission -> mark completion -> export outcomes CSV -> issue certificate.
- Make any doc-only clarifications needed so the same terms are used everywhere.

### Acceptance criteria

- one canonical semantics note exists and is shared with ops + fundraising
- export and certificate flows are rehearsed end to end
- no one needs maintainer interpretation to explain what a certificate means

### Done means...

- a staff member can explain certificate eligibility in plain language in under 60 seconds
- the class summary and outcomes export are known, named artifacts in reporting workflows
- threshold values are recorded in the operator handoff packet

## Week 3: Rehearse scenarios and survival rituals

### Objectives

- turn important failure cases into routine drills
- verify that retention, restore, and accessibility checks are operational, not aspirational
- reduce dependence on one maintainer's memory

### Concrete tasks

- Run `bash scripts/backup_restore_rehearsal.sh --compose-mode prod` and record the result.
- Run `bash scripts/system_doctor.sh --smoke-mode golden`.
- Run `bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers`.
- Verify retention automation status and document whether `classhub-retention.timer` is enabled.
- Rehearse common scenarios with ops and one instructor:
  - invite link full/expired
  - helper offline
  - staff member leaves
  - org boundary confusion
- Record what was unclear and fix the docs, not just the meeting notes.

### Acceptance criteria

- restore rehearsal completed or blocked with a documented reason
- accessibility smoke and golden smoke both pass or have explicit remediation tickets
- retention status is known
- common scenarios have named owner responses

### Done means...

- the team can answer "when did we last test restore?" with a date
- the team can answer "does accessibility smoke pass?" with evidence
- the team can answer "who handles offboarding and access review?" without guessing

## Week 4: Pilot observation and turnover hardening

### Objectives

- observe real staff use without adding surveillance
- convert observations into boring operational fixes
- finalize the turnover packet for the next maintainer and ops lead

### Concrete tasks

- Observe one real or simulated teacher session using note-taking only, not new analytics.
- Record where teachers hesitate in the current flow.
- Make doc or copy fixes for the highest-friction steps only.
- Build the turnover packet around access, deploy, smoke, restore, retention, and reporting.
- Confirm which commands are automated and which require human review.
- Schedule recurring rituals for the next quarter.

### Acceptance criteria

- one pilot observation write-up exists with concrete friction notes
- the turnover packet is complete enough for a new maintainer to start safely
- the recurring ritual calendar exists and has named owners

### Done means...

- teacher hesitation points are documented in plain language
- a replacement maintainer has a 60-minute starting path and a one-week confidence path
- the next quarter's restore, accessibility, and security checks are scheduled

## Plan guardrails

- no schema changes unless delaying them is riskier than shipping them
- no new product primitives
- no surveillance observation; use direct staff notes and rehearsal outcomes instead
- every stability task should reduce support burden, regression risk, or handoff time

## Related docs

- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md)
