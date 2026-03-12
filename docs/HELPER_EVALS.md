# Helper evals

Use this to measure whether the deployed Helper behavior is good enough for real class prompts.

## Prompt packs

- Baseline smoke prompts: `services/homework_helper/tutor/fixtures/eval_prompts.jsonl`
- Classroom-realistic prompts: `services/homework_helper/tutor/fixtures/eval_prompts_classroom_realistic.jsonl`

Each JSONL row includes:

- `id`
- `grade_band`
- `topic`
- `prompt`
- `teacher_expectation`
- `expected_behavior`
- optional scoring contracts:
  - `required_any`
  - `required_all`
  - `forbidden_any`

## Recommended run command (classroom pack)

```bash
bash scripts/run_helper_classroom_eval.sh \
  --url http://localhost/helper/chat \
  --student-auth \
  --class-code "$SMOKE_CLASS_CODE" \
  --out-dir /tmp/classhub_helper_eval_light
```

This writes:

- `results.jsonl` (raw prompt/response rows)
- `summary.json` (aggregate metrics)
- `summary.md` (review-ready summary)

For a hard gate:

```bash
bash scripts/run_helper_classroom_eval.sh \
  --url http://localhost/helper/chat \
  --student-auth \
  --class-code "$SMOKE_CLASS_CODE" \
  --out-dir /tmp/classhub_helper_eval_light \
  --min-pass-rate 0.80 \
  --enforce-threshold
```

If `--class-code` is omitted, the script falls back to `SMOKE_CLASS_CODE` (env) or `compose/.env`.

## Two-pass review workflow

1. Run with `HELPER_STRICTNESS=light` and capture artifacts.
2. Run with `HELPER_STRICTNESS=strict` and capture artifacts.
3. Compare both summaries for:
   - cheating refusal reliability
   - Piper hardware grounding
   - privacy-safe responses (no surveillance promises)
   - tone and confidence for frustrated students

## Decision rubric: local 1B vs stronger model

Treat this as release-decision guidance:

- Keep local `llama3.2:1b` when both `light` and `strict` runs show:
  - pass rate `>= 0.80`
  - no repeated high-risk flags (`response_error`, unsafe/privacy violations, missing refusal on cheating prompts)
- Consider stronger model (larger local model or remote backend) when either run shows:
  - pass rate `< 0.80`, or
  - repeated classroom-critical misses (unsafe/off-scope guidance, weak hardware grounding, low usefulness on debugging prompts)

When escalating model strength, keep the same prompt pack and re-run so comparisons remain apples-to-apples.

## Latest completed cycle (2026-03-12)

Authenticated classroom-pack runs completed against production URL (`https://lms.creatempls.org/helper/chat`) with student session bootstrap.

- Light baseline (`/tmp/classhub_helper_eval_light_v4`):
  - pass rate `0.8333` (`15/18`)
- Strict baseline before final wording fixes (`/tmp/classhub_helper_eval_strict_v5`):
  - pass rate `0.9444` (`17/18`)
  - only remaining fail: `piper-class-001`
- Strict after targeted prompt-contract fixes (`/tmp/classhub_helper_eval_strict_v6`):
  - pass rate `1.0` (`18/18`)
  - no failing prompt IDs

Result: strict-mode classroom eval now clears the rubric threshold with full pass coverage (`18/18`).
