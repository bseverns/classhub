# Stack Claims And Evidence

## Summary
Use this table when preparing a talk, evaluator packet, or institutional handoff.

It separates:

- claims the repo can defend now,
- the evidence source for each claim,
- and the overclaims to avoid.

| Claim you can make | Evidence source | Do not overclaim |
| --- | --- | --- |
| The public LMS stays public while the model host stays private. | `docs/ARCHITECTURE.md`, `docs/PRIVATE_LLM_BACKEND.md` | Do not imply browser traffic uses the tailnet. |
| Homework Helper is the only runtime component that crosses the private compute boundary. | `docs/PRIVATE_LLM_BACKEND.md`, helper routing code, `docs/REMOTE_HELPER_COMPUTE_CONTROL.md` | Do not imply teachers or students talk to the provider directly. |
| Remote helper compute is off by default, staff-only, class-scoped, and bounded. | `docs/REMOTE_HELPER_COMPUTE_CONTROL.md`, `docs/FEATURE_MATURITY.md`, teacher/admin tests | Do not describe it as ambient or always-on AI capacity. |
| `ready` means helper-side warm verification passed, not just provider optimism. | `docs/REMOTE_HELPER_COMPUTE_CONTROL.md`, `docs/EVIDENCE_REMOTE_COMPUTE.md`, helper tests | Do not imply instance boot alone is enough. |
| The classroom stays usable when the special path fails. | chat fallback tests, degraded-state routing behavior, `press/failure_degradation_matrix.md` | Do not imply the remote path never fails. |
| Remote lease usage is now exportable and accountable. | `/teach/class/<id>/export-helper-remote-snapshot`, `docs/EVIDENCE_REMOTE_COMPUTE.md` | Do not present repo-level docs as live production billing data. |
| Headscale is recommended as a narrow control plane, not a request proxy. | `docs/HEADSCALE_CONTROL_PLANE.md`, `ops/headscale/README.md` | Do not call it a general office VPN or an app runtime dependency. |
| The repo supports recovery and replacement better than a one-off hobby deployment. | `docs/DISASTER_RECOVERY.md`, `docs/RUNBOOK.md`, `ops/headscale/`, `ops/llm-server/README.md` | Do not claim zero-touch disaster recovery. |

## Measured now

- lease activations
- requested duration
- time spent in `starting`, `ready`, and `degraded`
- manual and auto-stop counts
- remote-routed request count
- local fallback count
- approximate leased minutes
- optional approximate cost estimate with operator pricing input
- recent lease sessions and reason-coded events

## Still thin

- rich alerting
- broad trend dashboards
- provider bridge automation depth
- field reliability numbers across long time windows
