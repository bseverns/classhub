# Helper policy

This doc describes the tutoring stance and the strictness switch. The canonical
prompt behavior is captured in:

- `services/homework_helper/tutor/fixtures/policy_prompts.md`

## Strictness switch

Set in `compose/.env`:

```
HELPER_STRICTNESS=light
# or
HELPER_STRICTNESS=strict
```

### Light (default)

- May provide direct answers when appropriate.
- Always explain reasoning and include a check-for-understanding question.
- Refuse clear cheating requests.

### Strict

- No final answers for graded work.
- Provide hints, steps, and clarifying questions instead.

## Notes for curriculum teams

- If a unit is assessment-heavy, flip to `strict`.
- For open-ended exploration, keep `light` but require reasoning in every answer.

## Ops note

On CPU-only servers, use the helper queue settings in `compose/.env` to cap
concurrency and avoid timeouts.

## Scope mode (lesson focus)

Set `HELPER_SCOPE_MODE` in `compose/.env`:

- `soft`: lesson-first answers with gentle redirects
- `strict`: refuse off-topic requests and ask the student to rephrase
