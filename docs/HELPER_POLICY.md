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

Or use profile defaults:

```dotenv
CLASSHUB_PROGRAM_PROFILE=elementary
```

When helper env vars are unset, profile defaults apply:
- `elementary`: strictness/scope/topic filter default to `strict`
- `secondary` and `advanced`: default to `light` + `soft` scope/topic filtering

Explicit helper env vars always override profile defaults. See [PROGRAM_PROFILES.md](PROGRAM_PROFILES.md).

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

Use rate limit envs to protect shared helper capacity:

- `HELPER_RATE_LIMIT_PER_MINUTE`
- `HELPER_RATE_LIMIT_PER_IP_PER_MINUTE`

## Scope mode (lesson focus)

Set `HELPER_SCOPE_MODE` in `compose/.env`:

- `soft`: lesson-first answers with gentle redirects
- `strict`: refuse off-topic requests and ask the student to rephrase
