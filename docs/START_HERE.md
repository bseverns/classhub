# Start Here

## Summary
This is the canonical role router for the docs. Use it to choose the shortest path, then use [DOCS_MAP.md](DOCS_MAP.md) only when you need the full reference index.

## If you are overwhelmed

Read one page only:

- Board member: [START_HERE_BOARD.md](START_HERE_BOARD.md)
- Evaluator: [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md)
- Teacher or assistant: [TEACHER_DOCS_JOURNEY.md](TEACHER_DOCS_JOURNEY.md)
- Running class tomorrow: [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md)
- Operator: [CURRENT_STATE.md](CURRENT_STATE.md), then [RUNBOOK.md](RUNBOOK.md)
- Developer: [DEVELOPMENT.md](DEVELOPMENT.md)

## What to do now

1. Pick your role from the table below.
2. Open only the listed starting page.
3. Use common URLs and commands only if you are operating or testing a live site.

## Verification signal
You should be able to pick one role path in under 30 seconds.

## Quick picks by role

| Role | Start here | Then read |
|---|---|---|
| Board member | [START_HERE_BOARD.md](START_HERE_BOARD.md) | [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md), [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) |
| Evaluator / decision-maker | [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md) | [CURRENT_STATE.md](CURRENT_STATE.md), [FEATURE_MATURITY.md](FEATURE_MATURITY.md) |
| Executive Director | [START_HERE_ED.md](START_HERE_ED.md) | [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md), [LEGAL_AND_PARTNER_NOTES.md](LEGAL_AND_PARTNER_NOTES.md) |
| Ops Director | [START_HERE_OD.md](START_HERE_OD.md) | [CURRENT_STATE.md](CURRENT_STATE.md), [RUNBOOK.md](RUNBOOK.md), [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) |
| Fundraising | [START_HERE_FUNDRAISING.md](START_HERE_FUNDRAISING.md) | [PROGRAM_LIFECYCLE.md](PROGRAM_LIFECYCLE.md), [RISK_AND_DATA_POSTURE.md](RISK_AND_DATA_POSTURE.md) |
| Instructor / assistant | [START_HERE_INSTRUCTOR.md](START_HERE_INSTRUCTOR.md) | [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md), [COMMON_SCENARIOS.md](COMMON_SCENARIOS.md) |
| Teacher / school staff | [TEACHER_DOCS_JOURNEY.md](TEACHER_DOCS_JOURNEY.md) | [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md), [LESSON_OVERRIDES.md](LESSON_OVERRIDES.md), [TEACHER_PORTAL.md](TEACHER_PORTAL.md) |
| Operator / admin | [CURRENT_STATE.md](CURRENT_STATE.md) | [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md), [RUNBOOK.md](RUNBOOK.md), [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) |
| Developer | [DEVELOPMENT.md](DEVELOPMENT.md) | [ARCHITECTURE.md](ARCHITECTURE.md), [CONTRIBUTING_DOCS.md](CONTRIBUTING_DOCS.md), [DECISIONS.md](DECISIONS.md) |

## Things you need to install first

If your school or org already hosts ClassHub for you, you may not need to install anything beyond a browser.

| Role | Install first | Notes |
|---|---|---|
| Teacher / school staff using an existing ClassHub site | Modern web browser | For 2FA-enabled teacher/admin accounts, also install an authenticator app on your phone. |
| Evaluator / board / decision-maker | Modern web browser | Pair the docs with a short live walkthrough. |
| Operator / admin self-hosting | Docker Engine, Docker Compose v2, Git, Bash, curl | See [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) for full server setup. |
| Developer | Same as operator/admin, plus Python 3.12 + pip | Most app work still runs in Docker; Python is mainly for local tooling and docs tasks. |

Optional quick check for operator/developer machines:

```bash
docker --version
docker compose version
git --version
bash --version
curl --version
```

## Common URLs

- Student join: `/`
- Student class view: `/student`
- Trust boundaries page: `/trust`
- Student data controls: `/student/my-data`
- Student portfolio + gallery: `/student/portfolio`, `/student/gallery`
- Teacher portal: `/teach`
- Admin login: `/admin/login/`
- Edge health: `/healthz`
- Class Hub upstream health: `/upstream-healthz` when `CADDY_EXPOSE_UPSTREAM_HEALTHZ=1`
- Helper health: `/helper/healthz`

## Technical quick commands

These are optional unless you are installing, testing, or operating a server.

- Local demo path: [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md)
- Guided one-command bootstrap:

```bash
bash scripts/quickstart_stack.sh --yes --mode local --with-admin --admin-username admin --admin-email admin@example.org
```

The command prints generated admin and authenticator credentials once; store them before closing the terminal.

- Deploy-time config gate:

```bash
python3 scripts/operator_preflight.py --env-file compose/.env
```

- Full health check:

```bash
bash scripts/system_doctor.sh
```

- Facilitator CLI quick check:

```bash
PYTHONPATH=tools/hubctl python -m hubctl classes list
```

- Guardrailed deploy:

```bash
bash scripts/deploy_with_smoke.sh
```

## Full reference map

Use [DOCS_MAP.md](DOCS_MAP.md) when you need the complete index.
Use [CANONICAL_TRUTHS.md](CANONICAL_TRUTHS.md) when two docs appear to disagree.
