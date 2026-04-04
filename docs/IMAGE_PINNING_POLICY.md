# Image Pinning Policy

## Summary
This page records the current image-pinning posture and the intentionally deferred steps.

## Current enforced posture

- Compose runtime images must use exact version tags or digests.
- `:latest` is blocked in committed compose/env config.
- Floating major/minor-style runtime tags are blocked for the shipped Compose image pins.
- Security CI scans the built Class Hub and Homework Helper images with Trivy.

Guardrails:
- `python3 scripts/check_no_latest_tags.py`
- `.github/workflows/security.yml`

## Intentionally deferred

- Full digest pinning for every shipped Compose image.
- Digest pinning for app Dockerfile base images.

Those steps are still desirable, but they are deferred until:
1. there is a documented operator refresh cadence for digest updates,
2. deploy/smoke guidance covers digest refresh and rollback cleanly,
3. the repo can land the change without turning routine upgrades into guesswork.

## Operator note

Exact version tags are the minimum accepted posture for shipped Compose images today.
When the repo moves to full digest pinning, this page and `docs/_registry/runtime_contracts.json` should change in the same patch.
