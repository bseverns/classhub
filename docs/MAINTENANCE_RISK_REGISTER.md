# Maintenance Risk Register

## Summary

This register names the five highest long-term maintenance risks visible in the current ClassHub repo. Each risk is grounded in the current code or docs, not hypothetical future scope.

## Risk 1: Teacher portal surface area is broad and expensive to keep coherent

- Risk title: Teacher portal complexity exceeds what one maintainer should hold in their head
- Evidence:
  - `/teach` and related routes aggregate many staff workflows in one surface: [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
  - `teach_home` assembles class list, profile, teacher invites, org admin, submissions, and template generation in one view: `services/classhub/hub/views/teacher_parts/content_home.py`
  - baseline shell sizes remain tracked: `services/classhub/templates/teach_home.html` is 81 lines; `services/classhub/templates/teach_class.html` is 78 lines; `services/classhub/hub/views/teacher_parts/roster_class.py` is 80 lines after split, with extracted endpoint logic in `services/classhub/hub/views/teacher_parts/roster_class_dashboard.py` (148 lines) and `services/classhub/hub/views/teacher_parts/roster_class_controls.py` (295 lines)
  - root templates are slimmed, but complexity now lives in bounded section partials/builders: `services/classhub/templates/includes/teach_class/class_setup_roster_student_row.html` is 83 lines; `services/classhub/templates/includes/teach_class/support_board_card.html` is 102 lines; `services/classhub/hub/services/teacher_dashboard_sections/facilitator_support_builders.py` is 213 lines
  - size/function budgets are continuously guarded in CI via `scripts/check_view_size_budgets.py` and `scripts/check_view_function_budgets.py`
  - section-level budgets and decomposition contracts are guarded via `scripts/check_teach_class_section_budgets.py`, `scripts/check_teach_class_template_contract.py`, and `scripts/check_teacher_roster_service_contract.py`
- Failure mode:
  - Small edits in `/teach` create regressions in unrelated staff workflows.
  - New staff see too many controls at once and rely on informal coaching instead of the product.
  - Maintainers become reluctant to simplify because the surface feels fragile.
- Leading indicators:
  - repeat questions about where to start in `/teach`
  - PRs that touch many teacher portal files for a single workflow
  - increased reliance on docs to explain UI that should already be obvious
- Mitigation plan:
  - freeze new teacher portal primitives for 30 days
  - allow only copy, control-order, warning, and progressive-disclosure changes
  - keep one short "top 10 teacher tasks" list and rehearse those paths only
  - add scenario tests around the existing teacher flows before any deeper refactor
- Owner role: Maintainer + Ops Director
- Cadence: Monthly

## Risk 2: Org boundary behavior is policy-sensitive and can be weakened by fallback mode

- Risk title: Staff access can drift if org boundary fallback is enabled
- Evidence:
  - production-safe default is strict (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`): `services/classhub/config/settings.py`
  - local/dev presets keep fallback mode available (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`): `compose/.env.example.local`
  - if staff have no active memberships and strict mode is off, they retain global class access: `services/classhub/hub/services/org_access.py:48-55`, `:122-127`, `:140-150`
  - docs describe this as legacy fallback: [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [SECURITY.md](SECURITY.md), [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md)
- Failure mode:
  - a newly created or half-offboarded staff account can see more classes than expected
  - ops assumes org boundaries are strict when deployment settings still allow fallback access
  - partner/org trust is weakened by access ambiguity rather than a code exploit
- Leading indicators:
  - staff can see classes outside their expected organization
  - repeated questions about why assignment and access are different things
  - production `.env` values differ from the intended org policy
- Mitigation plan:
  - pick one org boundary policy per deployment and document it in the ops handoff
  - review `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` during each quarterly restore rehearsal
  - add explicit operator-facing warnings/checklists wherever the policy is discussed
  - record each monthly boundary review using [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md)
  - do not add new role semantics until the current boundary model is operationally boring
- Owner role: Ops Director
- Cadence: Monthly

## Risk 3: Outcomes and certificate semantics are still policy-sensitive for staff interpretation

- Risk title: Reporting semantics can drift from staff expectations
- Evidence:
  - eligibility is derived from append-only `StudentOutcomeEvent` rows: `services/classhub/hub/services/teacher_dashboard_sections/outcomes_rollup.py`
  - dashboard snapshot and certificate eligibility now share the same section service stack (`outcomes_rollup.py` + `outcomes_snapshot.py`), reducing technical count drift risk
  - offline session completion is a manual staff action: `services/classhub/hub/views/teacher_parts/roster_outcomes.py:65-118`
  - certificate thresholds come from env settings and are explained in docs, not in one operator-owned checklist: [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [DECISIONS.md](DECISIONS.md)
- Failure mode:
  - teachers and reporting stakeholders interpret certificates as competency grades instead of event-threshold signals
  - offline completions are missed or duplicated in practice
  - exports and certificates remain technically consistent but operationally misunderstood
- Leading indicators:
  - repeated questions about why attendance and certificate eligibility do not always align
  - duplicate manual session-completion actions increase
  - certificate conversations require maintainer interpretation rather than doc lookup
- Mitigation plan:
  - keep one canonical explanation of what triggers outcomes and what certificate issuance means
  - treat export and certificate flows as scenario tests, not just code paths
  - validate thresholds during pilot setup and before reporting cycles
  - avoid expanding outcome types during the freeze
- Owner role: Ops Director
- Cadence: Monthly

## Risk 4: Retention and recovery depend on operator rituals staying alive

- Risk title: Data retention and disaster recovery are only as good as the routines that run them
- Evidence:
  - retention requires explicit manual or systemd timer setup: [RUNBOOK.md](RUNBOOK.md)
  - disaster recovery requires a large set of env values to be restored correctly, including org boundary and certificate thresholds: [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)
  - event deletion is guarded correctly in code, but only retention workflows can legally remove those rows: `services/classhub/hub/models.py:401-488`, `services/classhub/hub/management/commands/prune_student_events.py:105-106`
- Failure mode:
  - retention jobs stop running and nobody notices until disk pressure or policy drift appears
  - backup files exist but restore assumptions are stale
  - a real incident reveals that the team knows how to back up, but not how to recover confidently
- Leading indicators:
  - no recent record of `backup_restore_rehearsal.sh`
  - no evidence that `classhub-retention.timer` is enabled or healthy
  - emergency recovery depends on a single person remembering missing env settings
- Mitigation plan:
  - make restore rehearsal quarterly and visible to ops leadership
  - make retention status part of the recurring ops checklist
  - keep one canonical "what must be restored" list current
  - prefer one-command rehearsals over bespoke shell sessions
- Owner role: Ops Director + Maintainer
- Cadence: Quarterly for restore, monthly for retention verification

## Risk 5: Survivability still depends on cross-document memory and a single technical translator

- Risk title: Staff turnover will be painful unless operational knowledge is standardized now
- Evidence:
  - essential procedures live across multiple docs: [RUNBOOK.md](RUNBOOK.md), [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md), [ACCESSIBILITY.md](ACCESSIBILITY.md), [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
  - dual-service behavior and helper boundaries depend on env and internal endpoints: [OPENAI_HELPER.md](OPENAI_HELPER.md), [SECURITY.md](SECURITY.md), [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md)
  - onboarding/offboarding instructions exist, but the repo still assumes a reader can synthesize many moving parts quickly: [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [TEACHER_HANDOFF_CHECKLIST.md](TEACHER_HANDOFF_CHECKLIST.md)
- Failure mode:
  - a new maintainer can follow commands but still lacks the judgment to know what is critical, optional, or dangerous
  - ops and leadership rely on one person to translate policy into deployment settings
  - institutional memory decays faster than the docs are updated
- Leading indicators:
  - recurring questions that start with "where is that documented?"
  - freeze exceptions justified by urgency rather than documented policy
  - onboarding takes more than a day before a maintainer can safely run smoke, restore rehearsal, and access review
- Mitigation plan:
  - standardize a turnover packet and recurring rituals
  - keep policy choices in docs, not in chat history or memory
  - make every critical ritual runnable by command, then documented in plain language
  - explicitly separate what must be automated from what must stay manual and reviewed
- Owner role: Executive Director + Ops Director + Maintainer
- Cadence: Quarterly

## Related docs

- [STABILITY_CHARTER.md](STABILITY_CHARTER.md)
- [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md)
- [STAFF_TURNOVER_SURVIVABILITY.md](STAFF_TURNOVER_SURVIVABILITY.md)
- [STABILITY_OWNER_CADENCE.md](STABILITY_OWNER_CADENCE.md)
- [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md)
- [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md)
- [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md)
