# Start Here

## Summary
This is the canonical docs landing page. Use it to pick the shortest path for your role.

Evaluating whether this fits your org? Start with [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md).

## What to do now
1. Pick your role from the table below.
2. Open only the listed starting pages.
3. Use the common URLs/commands section once the stack is running.

## Verification signal
You should be able to pick a role path in under 30 seconds and identify the exact next doc to open.

## Things you need to install first

If your school or org already hosts ClassHub for you, you may not need to install anything beyond a browser.

| Role | Install first | Notes |
|---|---|---|
| Teacher / school staff (using an existing ClassHub site) | Modern web browser (Chrome, Edge, Firefox, or Safari) | For 2FA-enabled teacher/admin accounts, also install an authenticator app on your phone. |
| Evaluator / decision-maker | Modern web browser | Use this with [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) and [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md). |
| Operator / admin (self-hosting) | Docker Engine, Docker Compose v2, Git, Bash, curl | See [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) for full server setup. |
| Developer | Same as Operator/admin, plus Python 3.12 + pip (recommended) | Most app work still runs in Docker; Python is mainly for local tooling/docs tasks. |

Quick check for Operator/Developer machines:

```bash
docker --version
docker compose version
git --version
bash --version
curl --version
```

```mermaid
flowchart TD
  A[Start Here] --> B{Your role}
  B -->|Evaluator| C[PUBLIC_OVERVIEW]
  C --> D[TRY_IT_LOCAL]
  B -->|Teacher/Staff| E[NON_DEVELOPER_GUIDE]
  E --> F[TEACHER_PORTAL]
  B -->|Operator/Admin| G[DAY1_DEPLOY_CHECKLIST]
  G --> H[SECURITY + RUNBOOK]
  B -->|Developer| I[DEVELOPMENT]
  I --> J[ARCHITECTURE + DECISIONS]
```

## Quick picks (by role)

| Role | Start here | Then read |
|---|---|---|
| Evaluator / decision-maker | [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md) | [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md), [SECURITY.md](SECURITY.md) |
| Teacher / school staff | [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md) | [TEACHER_PORTAL.md](TEACHER_PORTAL.md) |
| Operator / admin | [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md) | [SECURITY.md](SECURITY.md), [RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Developer | [DEVELOPMENT.md](DEVELOPMENT.md) | [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md) |

## Core docs map

### Classroom use
- [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md)
- [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
- [COURSE_AUTHORING.md](COURSE_AUTHORING.md)
- [TEACHER_HANDOFF_CHECKLIST.md](TEACHER_HANDOFF_CHECKLIST.md)

### Operations
- [DAY1_DEPLOY_CHECKLIST.md](DAY1_DEPLOY_CHECKLIST.md)
- [SECURITY.md](SECURITY.md) (public-domain posture and reporting)
- [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md) (field-level data lifecycle + deletion controls)
- [SECURITY_BASELINE.md](SECURITY_BASELINE.md) (edge vs app ownership)
- [RUNBOOK.md](RUNBOOK.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)

### Engineering
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [OPENAI_HELPER.md](OPENAI_HELPER.md)
- [HELPER_POLICY.md](HELPER_POLICY.md)
- [REQUEST_SAFETY.md](REQUEST_SAFETY.md)
- [HELPER_EVALS.md](HELPER_EVALS.md)

### Design rationale
- [DECISIONS.md](DECISIONS.md)
- [decisions/archive/2026-02.md](decisions/archive/2026-02.md)

## Common URLs

- Student join: `/`
- Student class view: `/student`
- Teacher portal: `/teach`
- Admin login: `/admin/login/`
- Edge health: `/healthz`
- Class Hub upstream health: `/upstream-healthz` (when `CADDY_EXPOSE_UPSTREAM_HEALTHZ=1`)
- Helper health: `/helper/healthz`

## Common commands

- Local demo path: [TRY_IT_LOCAL.md](TRY_IT_LOCAL.md)
- Full health check: `bash scripts/system_doctor.sh`
- Guardrailed deploy: `bash scripts/deploy_with_smoke.sh`

## If you are overwhelmed

Read one page only:
- Evaluator: [PUBLIC_OVERVIEW.md](PUBLIC_OVERVIEW.md)
- Teacher/staff: [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md)
- Operator: [RUNBOOK.md](RUNBOOK.md)
- Developer: [DEVELOPMENT.md](DEVELOPMENT.md)
