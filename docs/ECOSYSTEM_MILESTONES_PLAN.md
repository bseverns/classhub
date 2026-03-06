# Ecosystem Milestones Plan (Q2-Q3)

## Summary
This plan turns external evaluation suggestions into a concrete, scoped implementation track for net-new platform value.

Targets:
1. `hubctl` facilitator CLI (terminal-first operator workflows),
2. classroom kiosk PWA (tablet-first student shell),
3. privacy/AI ops evidence dashboard v2 (`/teach/data-lifespan` + RAG status).

## What to do now
1. Deliver Milestone 1 first (`hubctl`) for fastest operator value.
2. Start Milestone 2 only after Milestone 1 auth/session contract is stable.
3. Deliver Milestone 3 after Milestone 2 so dashboard language includes both kiosk and helper evidence.

## Verification signal
At the end of this plan, an operator can:
- run core teacher actions from terminal,
- run student sessions in a stable tablet shell,
- export auditable retention + RAG posture evidence from the UI.

## Current baseline (already live)
- Teacher headless APIs exist under `/api/v1/teacher/*`.
- Student upload offline queue/retry is already live (IndexedDB + reconnect/manual flush flow).
- Local curriculum-only pgvector RAG is available behind `HELPER_RAG_ENABLED=1`.
- Data lifespan dashboard is live at `/teach/data-lifespan`.

This plan focuses on what is still missing: productized clients + stronger operator evidence surfaces.

## Milestone 1: Facilitator CLI (`hubctl`)

### Goal
Enable teacher/admin operators to execute common class controls without opening the web UI.

Status (March 6, 2026): Initial MVP shipped in `tools/hubctl/` with CI-backed unit tests.

### Scope (MVP)
- `hubctl classes list`
- `hubctl class lock <id>` and `unlock <id>`
- `hubctl class rotate-code <id>`
- `hubctl class set-enrollment <id> <open|invite_only|closed>`
- `hubctl class roster <id>`
- `hubctl class submissions <id> --limit N`

### Task checklist
- [x] Create `tools/hubctl/` package scaffold.
- [x] Implement API client for existing teacher endpoints.
- [x] Implement auth/session bootstrap flow (documented, no bypass of existing policy).
- [x] Add human-readable and `--json` output mode.
- [x] Add exit-code contract for automation (0 success, non-zero typed failures).
- [x] Add tests for command parsing + API error handling.
- [x] Add operator docs with examples and failure troubleshooting.

### Acceptance criteria
- Commands honor existing RBAC/permission boundaries.
- Operators can lock/rotate/set-enrollment from terminal in <30 seconds.
- CI validates `hubctl` parsing + API contract behavior.

### Effort estimate
- Build: 4-6 engineering days
- Hardening + docs: 1-2 days
- Total: 1.5 weeks

## Milestone 2: Classroom Kiosk PWA

### Goal
Provide an installable, low-distraction tablet shell for student join, lesson launch, and artifact submission.

Status (March 6, 2026): Complete for MVP. Kiosk route allowlist, installable shell, operator rollout notes, and reproducible network-resilience + tablet QA checklists are now in place.

### Scope (MVP)
- Installable PWA wrapper for `/`, `/student`, upload routes.
- Service worker + manifest tuned for classroom shell behavior.
- Reuse existing upload queue reliability path (no duplicate queue implementation).
- Minimal UI mode switch for kiosk-safe navigation.

### Task checklist
- [x] Define kiosk route allowlist and navigation constraints.
- [x] Add installable manifest + icon set + service worker registration guardrails.
- [x] Wire shell navigation to existing student auth/session contract.
- [x] Validate queue/retry behavior from unstable network scenarios.
- [x] Add tablet QA matrix (iPadOS Safari, Chrome Android tablet minimum).
- [x] Add deployment/operator notes for classroom rollout.

### Acceptance criteria
- Student can complete join -> lesson -> upload flow in PWA shell.
- Brief connectivity interruptions do not lose work.
- Installability and offline recovery behavior are documented and reproducible.

### Effort estimate
- Build: 6-8 engineering days
- Cross-device QA + docs: 2-3 days
- Total: 2 weeks

## Milestone 3: Privacy + AI Ops Evidence v2

### Goal
Turn privacy/RAG posture from static claims into exportable, operator-visible evidence.

### Scope (v2 extension)
- Extend `/teach/data-lifespan` with trend summaries and snapshot export.
- Add RAG status panel:
  - enabled/disabled state,
  - last curriculum index build time,
  - indexed chunk counts by reference source,
  - explicit "student data excluded from index" statement.

### Task checklist
- [ ] Add retention trend rows (recent prune runs, overdue counts).
- [ ] Add CSV/JSON snapshot export endpoint for data-lifespan page.
- [ ] Add helper-side RAG index status query contract.
- [ ] Surface RAG status in classhub dashboard panel.
- [ ] Add audit event for snapshot exports.
- [ ] Update runbook and evaluator docs with demonstration script.

### Acceptance criteria
- Operator can produce a one-page evidence export in under 2 minutes.
- Dashboard shows current retention posture and RAG grounding status.
- Reviewers can verify RAG is curriculum-only without reading code.

### Effort estimate
- Build: 4-6 engineering days
- Data validation + docs: 1-2 days
- Total: 1.5 weeks

## Sequencing and dependencies
- Milestone 1 -> Milestone 2 -> Milestone 3 (recommended order).
- Milestone 2 depends on stable auth/session contract patterns documented in Milestone 1.
- Milestone 3 depends on final wording from Milestones 1-2 for evaluator-facing evidence framing.

## Risks and mitigations
- Risk: auth/session drift across UI/API/CLI.
  - Mitigation: codify one documented auth contract and reuse integration tests.
- Risk: kiosk behavior differs by tablet browser.
  - Mitigation: explicit minimum support matrix and smoke checklist.
- Risk: dashboard claims diverge from runtime reality.
  - Mitigation: snapshot exports generated from live query paths only, with audit stamps.

## Rollout checkpoints
- Checkpoint A (after Milestone 1): operator pilot with two terminal-first instructors.
- Checkpoint B (after Milestone 2): one classroom pilot on tablet hardware.
- Checkpoint C (after Milestone 3): evaluator demo pack updated with evidence screenshots/exports.

## Related docs
- [API.md](API.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [FEATURE_MATURITY.md](FEATURE_MATURITY.md)
- [OPENAI_HELPER.md](OPENAI_HELPER.md)
- [RUNBOOK.md](RUNBOOK.md)
- [TEACHER_PORTAL.md](TEACHER_PORTAL.md)
