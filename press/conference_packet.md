# Conference Packet

## Summary
This is the shortest rigorous field guide for presenting ClassHub as infrastructure rather than product theater.

The intended audience is:

- technical peers,
- educators,
- institutional evaluators,
- and operators who need to understand why the boundary choices matter.

## Core thesis

ClassHub is a boundary-conscious educational stack that treats AI as leased infrastructure rather than ambient platform logic.

That choice keeps the public classroom experience calm while private compute stays bounded, accountable, and replaceable.

## Problem statement

Many edtech + AI stacks blur too many responsibilities together:

- public browser traffic and model traffic share the same mental model,
- expensive compute becomes the default path,
- failure in the special path becomes failure in the classroom,
- and operator reality is replaced by “trust us” architecture copy.

ClassHub responds by making the AI path narrow on purpose.

## Design patterns

- Public LMS stays public.
- Browsers never talk directly to the model host.
- Homework Helper is the only component that crosses the private compute boundary.
- Headscale remains control plane only.
- Remote compute stays off by default, staff-only, class-scoped, and time-bounded.
- Only `ready` allows remote helper routing.
- Remote failure degrades to local/default helper behavior instead of taking down the classroom flow.

## What is measured vs what is aspirational

Measured now:

- durable remote lease sessions and events
- requested duration, ready/degraded time, leased minutes, remote route counts, fallback counts
- readiness probe timestamps and last readiness-block reason
- teacher/admin JSON and CSV export of class-scoped remote-compute evidence
- auto-stop and unused-activation accounting

Still aspirational or deployment-local:

- live site uptime statistics
- mature alerting thresholds and paging
- provider-agnostic real cost accounting beyond operator-supplied pricing assumptions
- fully automated external bridge provisioning

## Evidence you can point to

- Canonical boundary docs: `docs/ARCHITECTURE.md`, `docs/PRIVATE_LLM_BACKEND.md`, `docs/HEADSCALE_CONTROL_PLANE.md`
- Remote lease contract: `docs/REMOTE_HELPER_COMPUTE_CONTROL.md`
- Remote evidence layer: `docs/EVIDENCE_REMOTE_COMPUTE.md`
- Operator drill/docs: `docs/RUNBOOK.md`, `docs/DAY1_DEPLOY_CHECKLIST.md`, `docs/DISASTER_RECOVERY.md`
- Reproducible Headscale control-plane bundle: `ops/headscale/`
- Remote bridge seam: `ops/remote-helper-compute/README.md`

## What is unusual here

- AI is treated as leased infrastructure, not the default center of the product.
- The public LMS does not dissolve into the private model path.
- The control plane is explicitly separated from the data plane.
- Degradation behavior is part of the architecture claim, not an afterthought.
- The repo contains operator artifacts, evidence exports, and recovery material, not just feature code.

## Tradeoffs accepted

- More explicit seams instead of one “smart” integrated runtime
- Staff-visible operational controls instead of magical auto-scaling narratives
- Narrow bridge contracts instead of provider lock-in
- Small-system observability first, not a metrics cathedral
- Some remaining reliance on operator discipline while the bridge/provisioning story matures

## What other institutions can learn

- Keep the public classroom experience independent from expensive AI infrastructure.
- Make the model boundary explicit and server-side only.
- Treat readiness as earned, not assumed.
- Design graceful fallback before scaling stories.
- Record enough evidence to explain costs, readiness, and degradation after a class day.

## Use with

- `press/stack_claims_and_evidence.md`
- `press/stage_safe_claims.md`
- `press/failure_degradation_matrix.md`
- `press/architecture.md`
- `press/screenshots/SHOTLIST.md`
