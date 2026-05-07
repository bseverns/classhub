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
- `Scaffold (inactive)`: config/code seam exists, but operators should not treat it as a live feature.
- `RFC`: design direction only; not a committed runtime feature.

## Configuration matrix (high-signal toggles)

| Setting | Default | Scope | Why it matters |
|---|---|---|---|
| `CLASSHUB_PROGRAM_PROFILE` | `secondary` | ClassHub + Helper behavior defaults | Baseline pacing + helper policy defaults. |
| `DJANGO_CSP_MODE` | `report-only` in shipped env examples (`relaxed` only as code fallback when unset) | Browser hardening rollout | Keeps strict CSP visible in telemetry while full enforcement completes staged acceptance checks. |
| `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED` | `0` | Student shell constraints | Enables kiosk route allowlist + focused student navigation shell. |
| `CLASSHUB_STUDENT_KIOSK_DEFAULT` | `0` | Student shell default mode | Forces kiosk mode on by default unless toggled off per device. |
| `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` | `1` in production presets (`0` in local/dev preset) | ClassHub access control | Controls whether staff without active org membership can access classes. |
| `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED` | `0` | RBAC evaluator behavior | Enables module-range scoped grant enforcement. |
| `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED` | `0` | RBAC mutation workflow | Routes RBAC writes into approval queue instead of immediate apply. |
| `CLASSHUB_TELEMETRY_DATABASE_URL` + `CLASSHUB_TELEMETRY_WRITE_MODE` + `CLASSHUB_TELEMETRY_READ_MODE` | URL unset / `off` / `core` | Telemetry split rollout controls | Reserved for staged telemetry DB split rollout; non-default modes require explicit parity/rollback validation. |
| `CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED` + `CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED` | `0` / `0` | Staff-only paid remote helper compute | Keeps expensive remote helper compute off by default and requires explicit operator acknowledgement before staff can request it for live class windows. |
| `HELPER_CONFIG_FILE` | unset | Helper config layering | Enables YAML-backed helper runtime config. |
| `HELPER_STRICTNESS` / `HELPER_SCOPE_MODE` / `HELPER_TOPIC_FILTER_MODE` | profile-driven when unset | Helper policy stance | Explicit env overrides profile defaults. |

## Feature maturity table

| Capability | Maturity | Toggle / contract | Verification |
|---|---|---|---|
| Student join via class code + display name | Live (default) | No feature flag | `GET /` and join flow succeeds in smoke checks. |
| Teacher portal class workflows (`/teach`, `/teach/class/<id>`, `/teach/lessons`) | Live (default) | Staff auth + 2FA policy | Teacher portal tests: `hub.tests.TeacherPortalTests`. |
| Teacher SSO (Google) | Live (flagged) | `CLASSHUB_TEACHER_SSO_ENABLED=1` + `CLASSHUB_TEACHER_SSO_PROVIDERS=google` | `hub.tests.test_teacher_admin_auth` plus Google callback/config tests pass and `/teach/login` renders the Google option. |
| Teacher SSO (Microsoft/custom OIDC) | Scaffold (inactive) | Config parses for `microsoft` / `oidc_custom`, but start/callback routes still return explicit "not active yet" notices. | Treat as non-live until real callback exchange is implemented and docs move it out of scaffold status. |
| Classroom kiosk PWA shell | Live (flagged) | `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED=1` | Kiosk route guard tests + `bash scripts/kiosk_resilience_check.sh --class-code <CODE>`. |
| Facilitator CLI (`hubctl`) teacher API controls | Live (default) | Session auth + OTP contract reused from `/teach/login` | `python -m unittest discover -s tools/hubctl/tests` |
| Organization boundaries (membership + role templates) | Live (default) | `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` controls fallback behavior | Cross-org class visibility tests in `test_teacher_admin_portal.py`. |
| RBAC scoped grants | Live (flagged) | `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1` | RBAC simulation + scoped grant tests pass. |
| RBAC delegated approvals | Live (flagged) | `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1` | Pending queue + review actions visible in `/teach` RBAC tools. |
| RBAC policy import/export | Live (default) | Superuser RBAC tools scope (`/teach` advanced policy mode) | `/teach/rbac/policy/export` + import validation checks. |
| Helper policy strictness/scope/topic filtering | Live (default, profile-driven) | Env override > helper YAML > profile default | `/helper/chat` policy response behavior matches expected strictness. |
| Helper YAML config layering | Live (default, optional) | `HELPER_CONFIG_FILE` path (optional) | Helper engine config-source tests in `tutor.tests.test_engine`. |
| Staff-only remote helper compute control | Live (flagged) | `CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED=1` + `CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED=1` | `/teach/class/<id>` shows the bounded control to policy-capable staff, recent lease sessions/events and cost-risk state are staff-visible, helper internal remote-compute tests pass, `ready` requires a warm probe, class-scoped JSON/CSV evidence export shows lease/routing/fallback totals, and unattended operator watch artifacts can be captured via `python3 scripts/remote_compute_operator_watch.py`. |
| Async/self-paced sequencing workflows | RFC | See `ASYNC_SELF_PACED_RFC.md` | No runtime SLA yet; treat as roadmap only. |
| Telemetry DB split | RFC / staged plan | `CLASSHUB_TELEMETRY_DATABASE_URL` + `CLASSHUB_TELEMETRY_WRITE_MODE` + `CLASSHUB_TELEMETRY_READ_MODE`; see `TELEMETRY_DB_SPLIT_PLAN.md` | Phase 1 Slice 0/1/2/3/4/5/6 scaffolding is shipped and Slice 7 release-cycle evidence capture is complete (`artifacts/stability/2026-03-10/telemetry/` parity + strict smoke + rollback drill). Final write-mode cutover gates remain intentionally deferred. |

## Recommended rollout sequence (RBAC + helper)
1. Keep `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=0` and `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=0`.
2. Validate org memberships and class assignments first.
3. Enable `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1` in a staging/pilot org.
4. Validate simulation + scoped grant behavior for real teacher/admin accounts.
5. Enable `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1` only when two-person approval flow is staffed.

## Remote helper hardening sequence

For the remote helper compute path, the current posture is:

1. lease governance is live in bounded form (`TTL`, idle-stop, explicit stop path, expiry display, unused-activation accounting)
2. honest readiness semantics are live (`ready` only after helper-side warm/probe success)
3. small durable operator metrics are live (activations, time-to-ready, fallbacks, degraded transitions, leased minutes, optional approximate cost)
4. bridge idempotency/correlation is now live in bounded form (duplicate same-class activate/deactivate requests are no-op safe and the bridge receives explicit control-request/idempotency metadata)
5. unattended remote-compute webhook alerts are now available in bounded form; the next hardening priorities remain provisioning codification depth and blank-VPS restore evidence

## Related docs
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [EVIDENCE_REMOTE_COMPUTE.md](EVIDENCE_REMOTE_COMPUTE.md)
- [INFRASTRUCTURE_HARDENING_ROADMAP.md](INFRASTRUCTURE_HARDENING_ROADMAP.md)
- [RBAC_GUIDE.md](RBAC_GUIDE.md)
- [PROGRAM_PROFILES.md](PROGRAM_PROFILES.md)
- [OPENAI_HELPER.md](OPENAI_HELPER.md)
- [ASYNC_SELF_PACED_RFC.md](ASYNC_SELF_PACED_RFC.md)
- [TELEMETRY_DB_SPLIT_PLAN.md](TELEMETRY_DB_SPLIT_PLAN.md)
