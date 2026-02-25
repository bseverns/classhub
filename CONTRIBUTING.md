# Contributing

## Summary
Thanks for improving Class Hub. This guide keeps contributions small, reviewable, and aligned with classroom safety and operational reliability.

## What to do now
1. Pick a contribution lane below.
2. Follow local setup in `docs/DEVELOPMENT.md`.
3. Run checks and include docs updates in the same PR.

## Verification signal
A ready PR should include: passing checks, updated docs (when behavior/docs changed), and a clear scope statement.

## Contribution lanes

### 1) Docs lane
- Improve clarity, runbooks, onboarding, or examples.
- Preferred first contributions for new collaborators.

### 2) Classroom UX polish lane
- Small template/UI improvements that preserve existing route/flow behavior.
- Focus on readability, reduced confusion, and accessibility.

### 3) Ops/security lane
- Guardrails, deployment ergonomics, safety defaults, and diagnostics.
- Keep changes explicit and test/documentation backed.

## Setup
- Local setup and workflow: `docs/DEVELOPMENT.md`
- Architecture context: `docs/ARCHITECTURE.md`
- Design tradeoffs and constraints: `docs/DECISIONS.md`

## Before opening a PR
Run from repo root:

```bash
bash scripts/repo_hygiene_check.sh
ruff check services scripts
python3 scripts/check_frontend_static_refs.py
bash scripts/make_release_zip.sh /tmp/classhub_release_ci.zip
python3 scripts/lint_release_artifact.py /tmp/classhub_release_ci.zip
```

Run project tests in your target service environment:

```bash
# Class Hub
python3 services/classhub/manage.py test

# Homework Helper
python3 services/homework_helper/manage.py test
```

If you use Docker-first local dev, run equivalent checks via `docker compose exec`.

## Maintainer branch protection baseline
For repository admins, keep `main` protected with:

- Require pull requests before merge.
- Require at least 1 approving review.
- Require conversation resolution before merge.
- Require status checks to pass before merge.

Recommended required checks (by workflow job):

- `lint / ruff`
- `test-suite / release-artifact-check`
- `test-suite / classhub-tests`
- `test-suite / helper-tests`
- `migration-gate / classhub`
- `migration-gate / helper`
- `security / secret-scan`
- `security / dependency-audit`
- `security / sast-bandit`
- `stack-smoke / doctor`

## Scope control
- Keep PRs narrow and explain what is explicitly out of scope.
- Do not introduce PII capture or new tracking fields.
- Do not add broad feature work under small-fix PRs.
- If a feature needs product decisions, open an issue first.
