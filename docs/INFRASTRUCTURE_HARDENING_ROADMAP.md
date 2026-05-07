# Infrastructure Hardening Roadmap

## Summary

This roadmap turns the current infrastructure review into a bounded next-step plan for the createMPLS deployment style:

- public LMS at `lms.creatempls.org`
- private model host
- Homework Helper as the only model client
- host-to-host tailnet for helper/model traffic only
- Headscale on a tiny Ubuntu VPS as the recommended control plane
- remote helper compute off by default, staff-only, class-scoped, and cost-aware

This is not a platform-expansion roadmap. It is a hardening roadmap for making the current architecture quieter, more honest, and less dependent on operator memory.

## What This Roadmap Is For

Use this page when deciding what to harden next in the remote helper compute chain.

The current repo already has:

- strong public/private boundary discipline
- good fallback behavior when remote compute is unavailable
- clear operator docs for the expected topology

The remaining work is mostly about making the system more self-calming:

- less drift between orchestration truth and runtime truth
- less cost leakage from forgotten remote leases
- more durable evidence when the remote path is helping or hurting
- less dependence on oral tradition for Headscale and bridge operations

## Hardening Order

Do this work in order. Earlier items reduce more real risk than later ones.

## Priority 1: Lease Governance

### Goal

Make expensive remote helper compute harder to leave on accidentally.

### Why This Comes First

This is the cheapest way to reduce both financial risk and operator anxiety.

### Required outcomes

- every remote helper lease has a mandatory TTL
- auto-stop is on by default
- `/teach` shows a clear `expires at` value
- staff have one obvious `Stop now` path
- createMPLS deployment default is max concurrent remote lease count of `1`

### Repo-facing work

- enforce lease expiry even when the UI is not revisited
- add one canonical class/session lease duration setting
- surface active lease countdown and stop affordance in `/teach/class/<id>`
- record explicit stop reason:
  - manual stop
  - TTL expiry
  - class end
  - idle stop

### Done looks like

- a class can activate remote compute, use it, and leave the page without creating surprise spend
- operator evidence can show why the remote backend stopped

## Priority 2: Honest Readiness

### Goal

Only call the remote path `ready` when it is actually usable for helper traffic.

### Why This Comes Second

The most likely production failure is state drift: provider says the backend exists, but helper traffic is still not truly ready.

### Required outcomes

`ready` means all of these are true:

- model endpoint is reachable from Homework Helper
- auth/token path is valid
- a warm probe request succeeds
- first-use latency is still within a bounded classroom budget

Anything weaker should remain `starting`, `degraded`, or `error`.

### Repo-facing work

- tighten the provider bridge contract around readiness semantics
- separate `instance exists` from `helper-ready`
- add one explicit warm-probe result to remote lease state
- keep helper routing remote only when lease state is `ready`
- preserve local/default fallback when readiness cannot be proven

### Done looks like

- staff do not see `ready` unless a real helper request would likely succeed
- remote activation failures degrade cleanly without confusing status language

## Priority 3: Minimal Durable Metrics

### Goal

Make the remote helper path diagnosable without introducing observability theater.

### Why This Comes Third

Once leases and readiness are honest, the next question is whether the feature is worth its cost and complexity.

### Required counters or evidence

- remote lease activations
- average time to ready
- fallback count by class/session
- degraded transitions
- provider unreachable events
- activations where remote compute was never actually used

### Repo-facing work

- add structured counters or append-only events for lease lifecycle milestones
- expose a small operator evidence view or export for active/recent remote sessions
- add one low-noise summary in `/teach` or operator evidence surfaces

Current status:

- helper remote lease state and per-class accounting are now durable in helper-owned Django tables, with cache retained only as a mirror for hot reads
- export/snapshot polish is now live in both `/teach` and the unattended `remote_compute_operator_watch.py` path

### Done looks like

- operators can answer whether remote compute is helping, failing, or wasting money without reading raw logs

## Priority 4: Provisioning Codification

### Goal

Turn more of the Headscale and remote bridge story into reproducible artifacts.

### Why This Comes Fourth

The architecture is already good. The remaining risk is operator drift around bootstrap, backup, restore, and enrollment steps.

### Required outcomes

- one canonical Headscale bootstrap path
- example systemd units where appropriate
- backup script or equivalent repeatable command path
- restore checklist validated against a blank VPS
- one canonical bridge/bootstrap env template

### Repo-facing work

- add `ops/headscale/` and bridge deployment artifacts only where they reduce ambiguity
- prefer narrow, auditable artifacts over broad automation claims
- rehearse restore against a fresh host and record the evidence

Current status:

- the repo now ships a narrow Headscale bundle in `ops/headscale/` for bootstrap, Compose/systemd, backup, and restore
- the next step is proving that bundle with a blank-VPS restore rehearsal and recording the evidence

### Done looks like

- replacing the Headscale VPS or bridge host does not require improvisation

## Priority 5: Bridge Idempotency And Audit Trail

### Goal

Make repeated activate/stop requests safe and auditable.

### Why This Comes Fifth

Once the lease lifecycle is real production behavior, duplicate clicks and repeated retries should not create backend chaos.

### Required outcomes

- duplicate activate requests do not create duplicate cost events
- duplicate stop requests are harmless
- audit trail records:
  - who requested the action
  - for which class
  - when it was requested
  - what outcome the bridge reported
  - when the backend actually turned off

### Repo-facing work

- tighten bridge request idempotency keys or equivalent request correlation
- persist lease lifecycle events with actor + class context
- expose enough audit detail for operator handoff and postmortems

### Done looks like

- operators can reconstruct a remote lease lifecycle without reading provider consoles first

## What Not To Do During This Hardening Pass

- do not route public browser traffic over the tailnet
- do not make the LMS depend on Headscale APIs
- do not broaden the tailnet into general office or site routing
- do not add Kubernetes, service mesh, or large observability stack complexity
- do not make remote GPU the default helper path

## Recommended Sequence

1. Finish lease governance.
2. Tighten honest readiness semantics.
3. Add a small operator evidence surface for remote lifecycle metrics.
4. Codify Headscale and bridge bootstrap/restore artifacts.
5. Add bridge idempotency and stronger lease audit trails.

## Two-Year Quiet-Durability Check

This roadmap is working if the repo can demonstrate all five of these:

1. One boring Headscale restore onto a replacement VPS.
2. One boring remote lease lifecycle from activate to stop.
3. Evidence that fallback is graceful and relatively rare.
4. One small operator view showing active lease, expiry, backend mode, and recent fallbacks.
5. Fewer critical steps that depend on one maintainer remembering them from memory.

## Related Docs

- [CURRENT_STATE.md](CURRENT_STATE.md)
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- [HEADSCALE_CONTROL_PLANE.md](HEADSCALE_CONTROL_PLANE.md)
- [PRIVATE_LLM_BACKEND.md](PRIVATE_LLM_BACKEND.md)
- [REMOTE_HELPER_COMPUTE_CONTROL.md](REMOTE_HELPER_COMPUTE_CONTROL.md)
- [RUNBOOK.md](RUNBOOK.md)
- [MAINTENANCE_RISK_REGISTER.md](MAINTENANCE_RISK_REGISTER.md)
