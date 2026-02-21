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

## Scope control
- Keep PRs narrow and explain what is explicitly out of scope.
- Do not introduce PII capture or new tracking fields.
- Do not add broad feature work under small-fix PRs.
- If a feature needs product decisions, open an issue first.
