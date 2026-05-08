# CSP Strict Migration Plan

## Summary

This page explains the current CSP rollout posture, the remaining blockers to strict enforcement, and the safest path from today’s repo defaults to a boring strict deployment.

It exists so operators can answer four questions quickly:

1. What mode are we in right now?
2. What does strict actually mean here?
3. What is still blocking a full strict flip?
4. How do we verify movement without improvising?

## Current posture

There are four distinct layers to keep separate:

| Layer | Current posture |
| --- | --- |
| Repo-shipped env examples | `DJANGO_CSP_MODE=report-only` |
| Django code fallback when unset | `relaxed` |
| Recommended production posture today | `report-only` until deployment-specific violations are understood, then `strict` |
| Intended end state | `strict` enforced CSP without inline script allowance and without the temporary inline-style canary |

Important:

- `report-only` is the repo-shipped deployment default, not the final security target.
- `relaxed` is a code fallback for unset configuration, not the recommended production posture.
- `strict` is the intended end state.

## Mode semantics

| Mode | What it does | When to use it |
| --- | --- | --- |
| `relaxed` | Enforced relaxed CSP plus strict report-only CSP | Local/debug fallback only when the env setting is absent |
| `report-only` | Strict report-only CSP only, with no enforced CSP header | Transitional deployment posture while gathering violation evidence |
| `strict` | Strict enforced CSP | Production posture once acceptance checks are stable |

## Transitional canary

A narrow strict canary is still allowed:

- `DJANGO_CSP_MODE=strict`
- explicit `DJANGO_CSP_POLICY`
- `script-src 'self'`
- temporary `style-src 'unsafe-inline'`

This is acceptable only as a controlled transition window after inline scripts are gone but before all inline-style cleanup is finished.

## Remaining blockers to full strict

1. Deployment-specific report-only noise still needs to be understood before a broad strict flip.
2. Some deployments may still need the temporary inline-style canary even after scripts are locked down.
3. External embed and asset-origin allowances must stay explicit:
   - `youtube-nocookie.com`
   - any separate asset/media origins
4. Operators need a repeatable way to distinguish:
   - repo example posture,
   - code fallback,
   - current deployment posture,
   - strict target posture.

## Guardrails already in place

- `scripts/check_no_inline_template_js.py`
- `scripts/check_no_inline_template_css.py`
- `scripts/check_csp_runtime_contract.py`
- CSP mode tests in both Django services
- Docs-truth guard for the current posture wording

These reduce the chance of silently drifting backward while the rollout remains staged.

## Verification steps

Use these in order:

1. Confirm the configured posture:

```bash
python3 scripts/security_posture_snapshot.py --env-file compose/.env
python3 scripts/check_csp_runtime_contract.py --env-file compose/.env
```

2. Confirm the shipped docs and runtime contract still agree:

```bash
python3 scripts/check_docs_truth.py
```

3. Confirm the live app headers on the target deployment:

```bash
curl -I https://lms.creatempls.org/
curl -I https://lms.creatempls.org/helper/healthz
```

4. If canarying `strict`, verify:
   - `script-src` does not allow `'unsafe-inline'`
   - report-only overrides do not weaken the target policy
   - classroom-critical pages still load cleanly

## Movement plan

1. Keep repo defaults at `report-only` while staged acceptance checks remain the policy.
2. Keep blocking inline JS/CSS regressions in CI.
3. Use the strict-script canary only when a deployment needs temporary inline-style allowance.
4. Remove temporary `style-src 'unsafe-inline'` once style cleanup is complete.
5. Flip the production deployment to plain `strict` only after the acceptance checks stay clean and the operator can explain the change in one sentence.

## Out of scope

- This page does not claim the repo is already strict by default.
- This page does not change live deployment env values by itself.
- This page does not replace deployment-specific CSP violation review.

## Related docs

- [SECURITY.md](SECURITY.md)
- [SECURITY_BASELINE.md](SECURITY_BASELINE.md)
- [DOCS_TRUTH_MECHANISM.md](DOCS_TRUTH_MECHANISM.md)
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
