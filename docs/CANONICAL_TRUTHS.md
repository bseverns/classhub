# Canonical Truths

## Summary
This page is the single index for “source of truth” decisions across docs.
When two docs overlap, use the canonical doc listed here first.

## What to do now
1. Find your policy area in the table.
2. Read the canonical doc before reading supporting docs.
3. If you find a conflict, treat the canonical doc as correct and open a docs fix.

## Verification signal
For any policy question, you should be able to name one canonical doc in under 30 seconds.

## Canonical policy map

| Policy area | Canonical doc | Supporting docs |
|---|---|---|
| What is shipped on `main` right now | [CURRENT_STATE.md](CURRENT_STATE.md) | [FEATURE_MATURITY.md](FEATURE_MATURITY.md), [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) |
| High-signal runtime/default-status registry | [DOCS_TRUTH_MECHANISM.md](DOCS_TRUTH_MECHANISM.md) | `docs/_registry/runtime_contracts.json`, [CURRENT_STATE.md](CURRENT_STATE.md), [FEATURE_MATURITY.md](FEATURE_MATURITY.md), [SECURITY.md](SECURITY.md) |
| Why a product/architecture decision exists | [DECISIONS.md](DECISIONS.md) | `docs/decisions/archive/` |
| Feature maturity and rollout posture | [FEATURE_MATURITY.md](FEATURE_MATURITY.md) | [CURRENT_STATE.md](CURRENT_STATE.md), [DECISIONS.md](DECISIONS.md) |
| Runtime lock profile expectations (baseline vs release) | [RUNTIME_LOCK_PROFILES.md](RUNTIME_LOCK_PROFILES.md) | [RUNBOOK.md](RUNBOOK.md), `scripts/check_runtime_policy_lock.py` |
| Security deployment posture and reporting path | [SECURITY.md](SECURITY.md) | [SECURITY_BASELINE.md](SECURITY_BASELINE.md), [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) |
| Plain-language risk and data posture for families | [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) | [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md), [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) |
| Field-level retention and deletion semantics | [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md) | [RUNBOOK.md](RUNBOOK.md), [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) |
| Organization boundary semantics | [ORG_BOUNDARY_EXPLAINER.md](ORG_BOUNDARY_EXPLAINER.md) | [ORG_BOUNDARY_POLICY_AUDIT.md](ORG_BOUNDARY_POLICY_AUDIT.md), [RBAC_GUIDE.md](RBAC_GUIDE.md) |
| RBAC capability model and policy workflows | [RBAC_GUIDE.md](RBAC_GUIDE.md) | [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md), [TEACHER_PORTAL.md](TEACHER_PORTAL.md) |
| Teacher top-task choreography and day-of-class priorities | [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md) | [TEACHER_PORTAL.md](TEACHER_PORTAL.md), [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md) |
| Operator commands and incident response flow | [RUNBOOK.md](RUNBOOK.md) | [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [COMMON_SCENARIOS.md](COMMON_SCENARIOS.md) |
| Minimum operator skill floor | [MINIMUM_VIABLE_OPERATOR.md](MINIMUM_VIABLE_OPERATOR.md) | [RUNBOOK.md](RUNBOOK.md), [TURNOVER_PACKET.md](TURNOVER_PACKET.md) |
| Recovery and restore procedure | [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) | [REPORTING_REHEARSAL.md](REPORTING_REHEARSAL.md), [RESTORE_REHEARSAL_LOG.md](RESTORE_REHEARSAL_LOG.md) |
| Stability/release evidence expectations | [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md) | [RELEASING.md](RELEASING.md), `artifacts/stability/<date>/EVIDENCE_INDEX.md` |
| Localization coverage and expansion contract | [LOCALIZATION.md](LOCALIZATION.md) | [CURRENT_STATE.md](CURRENT_STATE.md), `scripts/check_i18n_family_visible_contract.py` |
