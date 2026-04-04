# Docs Truth Mechanism

## Summary
This page explains the narrow machine-checkable docs spine used to keep high-signal status and security posture claims aligned.

## What to update first
1. Update `docs/_registry/runtime_contracts.json` when a shipped status or repo default posture changes.
2. Update the canonical docs that mirror those claims:
   - [CURRENT_STATE.md](CURRENT_STATE.md)
   - [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
   - [SECURITY.md](SECURITY.md)
   - [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md)
3. Run `python3 scripts/check_docs_truth.py`.

## Verification signal
`python3 scripts/check_docs_truth.py` exits with code `0`.

## Scope

The registry is intentionally small. It tracks only:
- selected feature statuses that are easy to misstate,
- a few policy-sensitive runtime defaults,
- short operator-facing notes that previously drifted across multiple docs.

It is not a full docs build system and it is not meant to replace narrative docs.

## Files

- Registry: `docs/_registry/runtime_contracts.json`
- Drift guard: `scripts/check_docs_truth.py`
- Operator snapshot: `scripts/security_posture_snapshot.py`

## Maintenance rule

- Update the registry first.
- Then update the docs that repeat the claim.
- If the claim is only operator-local deployment state in `compose/.env`, do not rewrite product docs.
- If the repo-shipped default changes, update the registry, docs, and `docs/DECISIONS.md` in the same change.
