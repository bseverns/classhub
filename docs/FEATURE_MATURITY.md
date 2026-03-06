# Feature Maturity + Rollout Flags

## Summary
This page is the quick contract for what is production-ready now, what is feature-flagged, and what is still RFC-only.

## What to do now
1. Check the maturity table below before enabling or demoing a feature.
2. Set only the required flags in `compose/.env`.
3. Run the listed verification step after each flag change.

## Verification signal
An operator can explain each enabled non-default flag in one sentence and show one passing verification check per flag.

## Maturity labels
- `Live (default)`: expected to run in standard deployments without extra rollout gating.
- `Live (flagged)`: shipped but intentionally gated behind a feature flag for controlled rollout.
- `RFC`: design direction only; not a committed runtime feature.

## Configuration matrix (high-signal toggles)

| Setting | Default | Scope | Why it matters |
|---|---|---|---|
| `CLASSHUB_PROGRAM_PROFILE` | `secondary` | ClassHub + Helper behavior defaults | Baseline pacing + helper policy defaults. |
| `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED` | `0` | Student shell constraints | Enables kiosk route allowlist + focused student navigation shell. |
| `CLASSHUB_STUDENT_KIOSK_DEFAULT` | `0` | Student shell default mode | Forces kiosk mode on by default unless toggled off per device. |
| `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` | `0` | ClassHub access control | Controls whether staff without active org membership can access classes. |
| `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED` | `0` | RBAC evaluator behavior | Enables module-range scoped grant enforcement. |
| `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED` | `0` | RBAC mutation workflow | Routes RBAC writes into approval queue instead of immediate apply. |
| `HELPER_CONFIG_FILE` | unset | Helper config layering | Enables YAML-backed helper runtime config. |
| `HELPER_STRICTNESS` / `HELPER_SCOPE_MODE` / `HELPER_TOPIC_FILTER_MODE` | profile-driven when unset | Helper policy stance | Explicit env overrides profile defaults. |

## Feature maturity table

| Capability | Maturity | Toggle / contract | Verification |
|---|---|---|---|
| Student join via class code + display name | Live (default) | No feature flag | `GET /` and join flow succeeds in smoke checks. |
| Teacher portal class workflows (`/teach`, `/teach/class/<id>`, `/teach/lessons`) | Live (default) | Staff auth + 2FA policy | Teacher portal tests: `hub.tests.TeacherPortalTests`. |
| Classroom kiosk PWA shell | Live (flagged) | `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED=1` | Kiosk route guard tests + `bash scripts/kiosk_resilience_check.sh --class-code <CODE>`. |
| Facilitator CLI (`hubctl`) teacher API controls | Live (default) | Session auth + OTP contract reused from `/teach/login` | `python -m unittest discover -s tools/hubctl/tests` |
| Organization boundaries (membership + role templates) | Live (default) | `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` controls fallback behavior | Cross-org class visibility tests in `test_teacher_admin_portal.py`. |
| RBAC scoped grants | Live (flagged) | `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1` | RBAC simulation + scoped grant tests pass. |
| RBAC delegated approvals | Live (flagged) | `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1` | Pending queue + review actions visible in `/teach` RBAC tools. |
| RBAC policy import/export | Live (default) | Owner/admin/superuser capability scope | `/teach/rbac/policy/export` + import validation checks. |
| Helper policy strictness/scope/topic filtering | Live (default, profile-driven) | Env override > helper YAML > profile default | `/helper/chat` policy response behavior matches expected strictness. |
| Helper YAML config layering | Live (default, optional) | `HELPER_CONFIG_FILE` path (optional) | Helper engine config-source tests in `tutor.tests.test_engine`. |
| Async/self-paced sequencing workflows | RFC | See `ASYNC_SELF_PACED_RFC.md` | No runtime SLA yet; treat as roadmap only. |
| Telemetry DB split | RFC / staged plan | See `TELEMETRY_DB_SPLIT_PLAN.md` | Plan-level checks only until migration phases execute. |

## Recommended rollout sequence (RBAC + helper)
1. Keep `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=0` and `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=0`.
2. Validate org memberships and class assignments first.
3. Enable `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1` in a staging/pilot org.
4. Validate simulation + scoped grant behavior for real teacher/admin accounts.
5. Enable `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1` only when two-person approval flow is staffed.

## Related docs
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [RBAC_GUIDE.md](RBAC_GUIDE.md)
- [PROGRAM_PROFILES.md](PROGRAM_PROFILES.md)
- [OPENAI_HELPER.md](OPENAI_HELPER.md)
- [ASYNC_SELF_PACED_RFC.md](ASYNC_SELF_PACED_RFC.md)
- [TELEMETRY_DB_SPLIT_PLAN.md](TELEMETRY_DB_SPLIT_PLAN.md)
