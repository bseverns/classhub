# Stage-Safe Claims

## Summary
These are the claims a speaker can safely make on stage using the repo as evidence.

## Safe claims

- ClassHub keeps the public LMS public and the model host private.
- Browsers never talk directly to the model host.
- Homework Helper is the only component that crosses the private compute boundary.
- Headscale remains control plane only; it does not proxy request traffic.
- Remote helper compute stays off by default and is only requested by staff for bounded class windows.
- Only `ready` allows remote helper routing.
- A provider saying “boot started” is not enough to count as `ready`.
- When the special path fails, the helper degrades and the classroom can keep moving on the local/default path.
- The remote lease now produces durable accounting and exportable evidence.
- The GPU/model host is treated as replaceable compute rather than the source of truth.

## Claims to avoid

- “Students talk directly to the model.”
- “The browser uses the tailnet.”
- “Remote GPU is the default helper path.”
- “Headscale is serving the LMS.”
- “The repo proves high uptime in production.”
- “The system has full cloud-grade observability.”
- “Cost accounting is exact without operator pricing inputs.”

## Best pairing

Use this page together with:

- `press/stack_claims_and_evidence.md`
- `docs/EVIDENCE_REMOTE_COMPUTE.md`
- `press/failure_degradation_matrix.md`
