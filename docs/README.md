# Documentation Hub

This repository treats documentation as product surface area, not an afterthought.
The goal is twofold:

1. Ship a reliable tool.
2. Teach how and why it works.

If code is the machine, docs are the operator console and training curriculum.

## Documentation architecture

This repo uses four complementary doc types:

1. Tutorial:
  - step-by-step onboarding for people who are new to the system.
  - primary pages: `docs/START_HERE.md`, `docs/LEARNING_PATHS.md`.
2. How-to:
  - task-focused run instructions for people solving a specific problem.
  - primary pages: `docs/RUNBOOK.md`, `docs/TROUBLESHOOTING.md`.
3. Reference:
  - factual descriptions of interfaces, routes, and behavior constraints.
  - primary pages: `docs/ARCHITECTURE.md`, `docs/REQUEST_SAFETY.md`.
4. Explanation:
  - rationale and tradeoffs behind design choices.
  - primary page: `docs/DECISIONS.md`.

Use this split deliberately when writing docs:
- if someone asks "what do I do now?", write how-to/tutorial.
- if someone asks "what is true?", write reference.
- if someone asks "why this way?", write explanation.

## How to use this docs set

Start from intent, not from file names:

- I need to run the system:
  - `docs/START_HERE.md`
  - `docs/DAY1_DEPLOY_CHECKLIST.md`
  - `docs/RUNBOOK.md`
  - `docs/TROUBLESHOOTING.md`
- I need to understand architecture:
  - `docs/ARCHITECTURE.md`
  - `docs/WHAT_WHERE_WHY.md`
  - `docs/REQUEST_SAFETY.md`
  - `docs/OPENAI_HELPER.md`
- I need to reason about tradeoffs and policy:
  - `docs/DECISIONS.md`
  - `docs/HELPER_POLICY.md`
  - `docs/SECURITY.md`
- I need a structured learning path:
  - `docs/LEARNING_PATHS.md`
- I need to maintain docs quality and teach through changes:
  - `docs/TEACHING_PLAYBOOK.md`

## Documentation contract

For any material technical feature, documentation should answer four questions:

1. What is it?
2. Why does it exist?
3. How do I operate or change it?
4. How do I verify it works?

This repo encodes that contract as:

- What:
  - `docs/ARCHITECTURE.md`
  - `docs/WHAT_WHERE_WHY.md`
- Why:
  - `docs/DECISIONS.md`
  - `docs/HELPER_POLICY.md`
- How:
  - `docs/DEVELOPMENT.md`
  - `docs/RUNBOOK.md`
  - `docs/COURSE_AUTHORING.md`
- Verify:
  - `docs/MERGE_READINESS.md`
  - `docs/HELPER_EVALS.md`
  - CI workflows under `.github/workflows/`

## Definition of done for documentation

A feature is not "done" until all conditions are true:

1. Operator can deploy or roll it back using documented commands.
2. Developer can explain why the change exists and where boundaries moved.
3. Reviewer can verify behavior with explicit checks.
4. New maintainer can recover from at least one realistic failure mode.

If any of these are missing, the feature is implementation-complete but not
delivery-complete.

## Authoring standard for new docs content

When adding or editing docs, follow this structure:

1. Context:
  - one paragraph stating scope and boundary.
2. Invariants:
  - what must always remain true.
3. Procedure:
  - exact commands with working directory assumptions.
4. Verification:
  - expected output or health signal.
5. Failure modes:
  - common errors and direct recovery actions.

## Style standard

- Prefer concrete examples over abstract advice.
- Include full commands, not partial snippets.
- State required working directory explicitly.
- Include "why this step exists" where non-obvious.
- Avoid silent assumptions about environment (local vs server, debug vs production).

## Documentation review checklist

Before merge, verify:

1. New behavior is reflected in docs and examples.
2. Links in `docs/START_HERE.md` remain valid.
3. Commands are copy/paste safe (no placeholder syntax that breaks shells).
4. Security-sensitive guidance remains explicit (proxy trust, secrets, 2FA, TLS).
5. At least one "verify" command is present for any new operational flow.

## Worked example pattern

When documenting a change, include one concise worked example in this shape:

1. Change:
  - "Helper now ignores unsigned scope fields."
2. Why:
  - "Prevents students from tampering with client-provided helper scope."
3. Operation impact:
  - "Student requests without valid scope token now fail with policy response."
4. Verification:
```bash
cd /srv/lms/app/compose
docker compose exec -T helper_web python manage.py test tutor.tests.HelperChatAuthTests
```
5. Failure mode:
  - "If tests fail with DB transaction-aborted errors, see `docs/TROUBLESHOOTING.md`."

## Suggested reading order for new contributors

1. `docs/START_HERE.md`
2. `docs/WHAT_WHERE_WHY.md`
3. `docs/ARCHITECTURE.md`
4. `docs/LEARNING_PATHS.md`
5. `docs/RUNBOOK.md`
6. `docs/DECISIONS.md`
7. `docs/TEACHING_PLAYBOOK.md`
