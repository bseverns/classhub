# Helper evals

We keep a small, human-reviewable eval set to track quality across grade bands
and strictness modes.

## Prompt set

Default prompts:

- `services/homework_helper/tutor/fixtures/eval_prompts.jsonl`

Each line is JSON with fields:

- `id`
- `grade_band`
- `topic`
- `prompt`
- `expected_behavior`

## Run the eval script

```bash
python scripts/eval_helper.py \
  --url http://localhost/helper/chat \
  --out /tmp/helper_eval_results.jsonl
```

Notes:
- The script sleeps between requests by default to avoid rate limits.
- Use `--limit` for quick smoke checks.

## Review workflow

1) Run once with `HELPER_STRICTNESS=light`.
2) Flip to `HELPER_STRICTNESS=strict` and run again.
3) Compare responses for policy adherence and grade-appropriateness.
