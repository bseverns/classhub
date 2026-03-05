# Start Here: Evaluator (Non-Technical)

## Summary
Use this page if you are reviewing ClassHub fit and do not need to inspect implementation details first.

## What to do now
1. Read [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) for the product and trust posture.
2. Read [CURRENT_STATE.md](CURRENT_STATE.md) for what is shipping now.
3. Read [FEATURE_MATURITY.md](FEATURE_MATURITY.md) for flags, rollout readiness, and RFC boundaries.
4. Run the guided local walkthrough in [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md) with an operator.

## Verification signal
Within 30 minutes, you can answer: what is live, what is flag-gated, and what is roadmap-only.

## Fast evaluation path (30-45 minutes)

| Time | Goal | Where to look |
|---|---|---|
| 10 min | Understand classroom model and privacy posture | [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md), [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) |
| 10 min | Validate current shipped scope | [CURRENT_STATE.md](CURRENT_STATE.md), [FEATURE_MATURITY.md](FEATURE_MATURITY.md) |
| 10 min | Watch core teacher/admin workflow live | `/teach`, `/teach/class/<id>`, `/teach/lessons` |
| 5-15 min | Confirm operational readiness path | [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md), [RUNBOOK.md](RUNBOOK.md) |

## Questions to ask during a live review
- Which features are enabled here by non-default flags?
- Which workflows are superuser-only versus teacher/admin role-scoped?
- Which behaviors are profile defaults versus explicit helper env overrides?
- Which items are still RFC status and not part of near-term deployment?

## If you only have 10 minutes
1. Read [CURRENT_STATE.md](CURRENT_STATE.md).
2. Read [FEATURE_MATURITY.md](FEATURE_MATURITY.md).
3. Ask the operator to open `/teach` and show:
   - class assignment flow,
   - organization role/membership controls,
   - RBAC tool visibility and whether approval queue is enabled.

## Related docs
- [START_HERE.md](START_HERE.md)
- [DOCS_MAP.md](DOCS_MAP.md)
- [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md)
- [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md)
- [SECURITY.md](SECURITY.md)
