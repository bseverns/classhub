# Teaching Playbook

This repository is intended to be both:
- an operating system for classroom delivery
- a teaching artifact for new maintainers

This playbook defines how to write documentation that teaches, not just records.

## Teaching objective

Every meaningful change should help a reader answer:

1. What changed?
2. Why did we choose this design?
3. How do I operate it safely?
4. How do I detect and recover from failure?

If docs only answer (1), they are notes.
If docs answer all four, they are curriculum.

## Audience model

Write for three audiences in this order:

1. On-call operator:
  - needs short, reliable actions under pressure.
2. New developer:
  - needs architecture boundaries and decision logic.
3. Future maintainer:
  - needs enough context to refactor safely months later.

When these needs conflict, favor operational clarity first.

## Documentation packet per feature

For each non-trivial feature, ship a documentation packet:

1. Architecture note:
  - where the boundary moved (service, route, model, auth surface).
2. Decision note:
  - why this choice was made and what was rejected.
3. Operator procedure:
  - exact commands and expected outputs.
4. Verification:
  - tests, smoke checks, and one manual scenario.
5. Failure mode:
  - most likely break and first recovery action.

Where each part should live:
- architecture note: [ARCHITECTURE.md](ARCHITECTURE.md) or [WHAT_WHERE_WHY.md](WHAT_WHERE_WHY.md)
- decision note: [DECISIONS.md](DECISIONS.md)
- operator procedure: [RUNBOOK.md](RUNBOOK.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- verification: [MERGE_READINESS.md](MERGE_READINESS.md) and test commands in context docs
- failure mode: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Writing style contract

Use these rules for all teaching docs:

1. Lead with intent:
  - first line should say what problem this page helps solve.
2. Name invariants:
  - state what must remain true even as implementation changes.
3. Show complete commands:
  - include working directory and executable command.
4. Show expected signals:
  - include what "healthy" looks like.
5. Add one anti-example:
  - show a common wrong assumption and correction.

## Example packet: Helper scope token hardening

Change summary:
- Class Hub signs helper scope metadata.
- Helper verifies signature server-side.
- Student requests without valid token are denied.

Boundary moved:
- trust moved from client-provided JSON fields to signed server token.

Decision rationale:
- students can tamper with browser requests, so unsigned scope is not trusted.

Operational impact:
- missing/invalid token events are expected logs in negative tests.

Verification:
```bash
cd /srv/lms/app/compose
docker compose up -d --build helper_web
docker compose exec -T helper_web python manage.py test tutor.tests.HelperChatAuthTests
```

Failure mode and recovery:
- symptom: repeated `current transaction is aborted` during helper tests.
- first action: validate helper event writes are best-effort and do not poison
  transaction state; then rerun helper test suite.
- reference: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Example packet: Dependency security upgrades

Change summary:
- dependency scan flags vulnerable package versions in CI.

Boundary moved:
- minimum safe dependency version became part of release criteria.

Decision rationale:
- predictable security posture is easier than ad-hoc emergency patching.

Operational impact:
- pull requests can fail on `pip-audit` even when functional tests pass.

Verification:
```bash
cd /srv/lms/app
pip-audit -r services/classhub/requirements.txt --progress-spinner off
```

Recovery pattern:
1. bump dependency in pinned requirements.
2. rebuild image.
3. rerun service tests and security scan.
4. update docs if behavior changed across versions.

## Anti-patterns to avoid

1. "Works on my machine" steps:
  - missing `cd` context and environment assumptions.
2. Explanation-only docs:
  - no executable commands or verification.
3. Procedure-only docs:
  - no rationale, so future refactors regress intent.
4. Hidden failure cases:
  - no mention of likely breakpoints.
5. Orphan docs:
  - page not linked from [START_HERE.md](START_HERE.md) or [index.md](index.md).

## Maintainer review ritual

Before merging:

1. Run through modified docs as if you were new to the repo.
2. Copy/paste each new command in a clean shell context.
3. Confirm one "what", one "why", one "how", and one "verify" statement exists.
4. Ensure at least one failure mode is documented for each new operational flow.
5. Link the change from a navigational page:
  - [START_HERE.md](START_HERE.md) for pathing
  - [index.md](index.md) for policy/contract

## Change log discipline

If the change modifies behavior or operational posture:

1. add/update entry in [DECISIONS.md](DECISIONS.md).
2. archive superseded details in `docs/decisions/archive/` when needed.
3. keep active decisions concise and linked to the deeper procedure docs.
