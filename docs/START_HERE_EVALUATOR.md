# Start Here: Evaluator (Non-Technical)

## Summary
Use this page if you are reviewing ClassHub fit and do not need to inspect implementation details first.

## What to do now
1. Read [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) for the product and trust posture.
2. Read [CURRENT_STATE.md](CURRENT_STATE.md) for what is shipping now.
3. Read [FEATURE_MATURITY.md](FEATURE_MATURITY.md) for what is live now, optional, or still planned.
4. Run the guided local walkthrough in [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md) with your technical lead.
5. For a compact visual evidence packet, use `press/evaluator_quick_pack.md`.
6. Optional technical evidence export: ask your technical lead to run `bash scripts/demo_data_lifespan_evidence.sh --base-url <DOMAIN> --cookie-file <SESSION_COOKIE_FILE>`.

## Verification signal
Within 30 minutes, you can answer: what is live, what is optional, and what is still roadmap-only.

## Fast evaluation path (30-45 minutes)

| Time | Goal | Where to look |
|---|---|---|
| 10 min | Understand classroom model and privacy posture | [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md), [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) |
| 10 min | Validate current shipped scope | [CURRENT_STATE.md](CURRENT_STATE.md), [FEATURE_MATURITY.md](FEATURE_MATURITY.md) |
| 10 min | Watch core teacher/admin workflow live | `/teach`, `/teach/class/<id>`, `/teach/lessons` |
| 5-15 min | Confirm operational readiness + evidence export path | [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md), [RUNBOOK.md](RUNBOOK.md), `/teach/data-lifespan` |

## Operator demo script (privacy evidence)
You can skip this section if you are a non-technical reviewer.  
Use this command with an authenticated teacher/admin/superuser cookie file:

```bash
bash scripts/demo_data_lifespan_evidence.sh \
  --base-url https://YOUR_DOMAIN \
  --cookie-file classhub_teach_cookie.txt \
  --out-dir /tmp/classhub_evidence_demo
```

## Questions to ask during a live review
- Which optional features are turned on in this deployment?
- Which workflows are admin-only versus available to regular teachers?
- Which helper behaviors are defaults versus local custom settings?
- Which items are still planned and not part of near-term deployment?

## If you only have 10 minutes
1. Read [CURRENT_STATE.md](CURRENT_STATE.md).
2. Read [FEATURE_MATURITY.md](FEATURE_MATURITY.md).
3. Ask your technical lead to open `/teach` and show:
   - class assignment flow,
   - organization role/membership controls,
   - advanced permission tools and whether approval queue is enabled,
   - `/teach/data-lifespan` export (`JSON` or `CSV`) and helper knowledge-source status panel.

## Related docs
- [START_HERE.md](START_HERE.md)
- [DOCS_MAP.md](DOCS_MAP.md)
- [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md)
- [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md)
- [SECURITY.md](SECURITY.md)
