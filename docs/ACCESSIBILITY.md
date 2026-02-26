# Accessibility

## Summary
This page covers the practical accessibility checks for this stack, including the automated smoke gate used in CI.

## What to do now
1. Run stack smoke first (`bash scripts/system_doctor.sh --smoke-mode golden`).
2. Run accessibility smoke (`bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers`).
3. Treat any `critical` accessibility finding as a release blocker.

## Verification signal
`scripts/a11y_smoke.sh` ends with `[a11y] PASS` and CI `stack-smoke` shows `Run accessibility smoke` passing.

## Scope and policy

- Scanner stack: Playwright + axe-core.
- Default threshold: `critical` impact findings fail the run.
- Routes scanned:
  - `/`
  - `/teach`
  - `/teach/lessons`
  - `/teach/class/<id>` (when fixture class exists)
  - `/teach/class/<id>/certificate-eligibility` (when fixture class exists)

## Local run

From repo root:

```bash
bash scripts/system_doctor.sh --smoke-mode golden
bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers
```

Optional stricter/lower thresholds:

```bash
bash scripts/a11y_smoke.sh --fail-impact serious
bash scripts/a11y_smoke.sh --fail-impact moderate
```

## Script options

```bash
bash scripts/a11y_smoke.sh --help
```

Important options:

- `--compose-mode <prod|dev>`
- `--base-url <url>`
- `--class-name <name>`
- `--teacher-username <name>`
- `--fail-impact <minor|moderate|serious|critical>`
- `--timeout-ms <ms>`
- `--install-browsers`

## Environment variables used

- `A11Y_BASE_URL`
- `A11Y_CLASS_ID`
- `A11Y_TEACHER_SESSION_KEY`
- `A11Y_FAIL_IMPACT`
- `A11Y_TIMEOUT_MS`

The wrapper script mints a temporary teacher session key from the running stack and resolves class id from smoke fixtures.

## CI integration

`stack-smoke` runs accessibility smoke after golden smoke fixture setup.

Workflow:

- `.github/workflows/stack-smoke.yml`

## Failure handling

1. Re-run locally to confirm reproducibility:
   - `bash scripts/a11y_smoke.sh --compose-mode prod --install-browsers`
2. Fix template/JS semantics first for the specific failing selector.
3. Re-run a11y smoke and baseline smoke before merge.
4. If a failure is intentional and temporary, capture justification in PR notes and open a follow-up ticket.

## Notes for this project

- Student and teacher flows remain no-inline-JS/no-inline-CSS guarded in CI.
- Accessibility checks are scoped to core classroom workflows first to keep gate signal stable and actionable.
