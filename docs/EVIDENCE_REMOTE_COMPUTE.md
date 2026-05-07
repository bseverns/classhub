# Remote Compute Evidence

## Summary
This page is the canonical evidence layer for the bounded remote helper compute path.

It answers a narrow question:

- what does the repo now measure about remote helper leases,
- what does that evidence support,
- and what is still design intent rather than measured field evidence.

This is not a live uptime report for one deployment.
It is the repo-level evidence contract for how the system is expected to behave and what operators can export or inspect.

## Core claim

ClassHub treats AI as leased infrastructure rather than ambient platform logic.

In practice that means:

- the public LMS stays public,
- browsers never talk directly to the model host,
- Homework Helper is the only component that crosses the private compute boundary,
- remote compute stays off by default,
- and the expensive path is only used when a bounded class-scoped lease is actually `ready`.

## What is measured now

The helper now persists remote-compute lease evidence as durable server-side records.

Per class and per lease session, the repo now measures:

- lease activations
- requested duration
- time spent in `starting`
- time spent in `ready`
- time spent in `degraded`
- manual stop count
- auto-stop count
- remote-routed request count
- local fallback count after remote attempt
- approximate leased minutes consumed
- optional approximate cost estimate via `HELPER_REMOTE_COMPUTE_ESTIMATED_USD_PER_HOUR`
- readiness probe timestamps and last readiness-block reason
- recent transition/fallback events with compact reason codes
- duplicate same-class activate/deactivate requests that were intentionally absorbed as bounded no-op control actions

The evidence intentionally excludes student prompt bodies and raw provider credentials.

## Where the evidence lives

Durable helper models:

- `RemoteComputeLeaseRecord`
- `RemoteComputeClassMetric`
- `RemoteComputeLeaseSession`
- `RemoteComputeLeaseEvent`

Helper internal staff/operator endpoints:

- `/helper/internal/remote-compute-status`
- `/helper/internal/remote-compute-evidence`

Teacher/admin export surface:

- `/teach/class/<id>/export-helper-remote-snapshot?format=json`
- `/teach/class/<id>/export-helper-remote-snapshot?format=csv`
- `/teach/class/<id>` remote-compute panel with recent lease sessions, recent events, and a simple cost-risk state

## What `ready` means now

`ready` is intentionally stricter than provider optimism.

The current helper contract is:

1. provider accepted activation or health refresh
2. helper can reach the configured remote backend path
3. configured auth works
4. a real warm chat probe succeeds
5. the response shape is usable enough for helper trust
6. the warm probe completes within `HELPER_REMOTE_COMPUTE_READY_MAX_SECONDS`

If any of that fails, the lease stays out of `ready`.

## Fallback evidence

The repo now treats graceful degradation as a first-class property.

When remote execution fails during an active lease:

- the helper records a structured fallback event,
- the lease moves to `degraded`,
- the current request retries on the local/default path,
- and the degraded lease no longer keeps routing remote traffic.

Common reason-code classes include:

- `auth_error`
- `timeout`
- `warmup_failed`
- `malformed_response`
- `upstream_unavailable`
- `provider_off_reconciled`
- `idle_timeout`
- `lease_expired`

## Lease governance evidence

Lease governance is now more than a UI label.

The repo records:

- requested lease duration
- explicit expiry timestamps
- explicit manual stops
- auto-stops from lease expiry
- auto-stops from idle timeout
- unused activations where the remote lease was activated but never actually routed traffic

That makes the remote path more accountable in both cost and operations terms.

## What operators can show

An operator can now produce a class-scoped snapshot that shows:

- current lease state
- who requested it
- when it was requested
- when it expires
- whether helper is actually using the remote backend
- aggregate activation / routing / fallback counts
- aggregate starting / ready / degraded time
- approximate leased minutes
- optional approximate cost estimate
- recent lease sessions
- recent transition/fallback events
- whether the current lease looks bounded, unused, degraded, or close to expiry from a staff cost-risk perspective
- a derived trend state plus low-noise warning flags for fallback rate, provider reachability, lease waste, and slow warm-up

That is enough to support a technical talk or evaluator review without exposing provider internals.

## What this makes more defensible

The repo can now support these claims with durable artifacts:

- remote helper compute is bounded and class-scoped
- `ready` is not provider optimism alone
- the classroom stays usable when the special path fails
- expensive remote capacity can be accounted for after the fact
- the private model path remains replaceable because the evidence sits at the helper boundary, not inside a provider SDK

## What remains thin

The repo still does not claim:

- long-term real-world uptime statistics
- a full alerting/metrics platform
- automated webhook/pager delivery for every derived warning signal
- a mesh/service-identity architecture
- zero-touch provisioning of every external bridge/provider component
- globally valid cost estimates across providers without operator-supplied pricing assumptions

This is evidence-building infrastructure, not observability theater.

## Related docs

- [REMOTE_HELPER_COMPUTE_CONTROL.md](REMOTE_HELPER_COMPUTE_CONTROL.md)
- [PRIVATE_LLM_BACKEND.md](PRIVATE_LLM_BACKEND.md)
- [RUNBOOK.md](RUNBOOK.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
