# Class Hub One-Pager

## Summary
Class Hub is a self-hosted, classroom-first learning platform with a separate Homework Helper service for guided hints and a deliberately bounded private-compute path.

## What to do now
1. Share this page for quick project context.
2. Pair it with `docs/PUBLIC_OVERVIEW.md` and `docs/TRY_IT_LOCAL.md`.
3. Use the blurbs and architecture page for shorter channels.

## Verification signal
A reader should understand the system scope, deployment shape, and privacy stance in under five minutes.

## What it is
- Django-based class hub for lesson delivery and teacher workflows.
- Separate helper service routed under `/helper/*`.
- Self-hosted stack using Caddy, Postgres, Redis, and optional Ollama.
- A boundary-conscious architecture where AI is treated as leased infrastructure rather than ambient platform logic.

## Who it is for
- Schools and programs wanting local operational control.
- Teams that prefer low-complexity, inspectable infrastructure.

## Key features
- Student join by class code + pseudonym display name (no student password accounts in the current release).
- Plain-language trust page (`/trust`) and student self-service data controls (`/student/my-data`).
- Multi-lingual UI support on the bounded family/student tranche (`en`, `es`, `so`, and provisional `ksw` pending native-speaker review).
- Portable course content through file-first authoring, coursepack builds, static registry publishing/import, and print-friendly HTML handouts with simple PDF fallback downloads.
- Student home centered on `This week`, `Course links`, and `Account` so first actions are obvious.
- Artifact-first student workflow: portfolio history at `/student/portfolio` and student opt-in + teacher-moderated gallery sharing at `/student/gallery`.
- Progressive disclosure in student UI (collapsed modules/helper/forms) to reduce overload.
- Teacher/admin auth with OTP support and teacher self-service profile updates.
- Organization-aware staff access with optional hard org boundary mode.
- Invite-only enrollment controls with expiring/seat-capped invite links.
- Lesson release controls, upload dropboxes, and privacy-safe export tooling.
- Help-first facilitation board prioritizing “I’m stuck” signals and upload friction without ranking students.
- Outcomes and certificate eligibility/issuance workflows for teacher reporting.
- Safe fallback site modes for operational incidents.
- Automated accessibility smoke checks for core student/teacher routes.

## Deployment summary
- Local demo: Docker Compose (`Caddyfile.local`).
- Public deployment: domain Caddy template with TLS and deployment guardrails.
- Serious private-helper path: public LMS + private model host + helper-only server-to-server boundary.
- Operations playbooks in `docs/DAY1_DEPLOY_CHECKLIST.md` and `docs/RUNBOOK.md`.

## Privacy and safety stance
- Minimal student identity model.
- No student surveillance scoring.
- No helper prompt archive.
- Browsers never talk directly to the model host.
- Student artifacts are teacher-only by default unless explicitly published by the student and approved by staff.
- Explicit retention and cleanup operations.
- Per-class retention presets (`erase_after_7_days`, `keep_for_semester`, `keep_until_student_deletes`) applied by existing prune jobs.
- Hardened download and no-store patterns on sensitive routes.
- Export and certificate/report surfaces avoid helper prompt content by design.
- UI density can be configured by cohort (`compact` / `standard` / `expanded`) without changing privacy boundaries.

## Try it locally
- `docs/TRY_IT_LOCAL.md`

## What is unusual
- The LMS does not dissolve into the AI path.
- Expensive remote helper compute stays off by default and is only activated for bounded staff-led class windows.
- Degradation to local/default helper behavior is part of the architecture contract, not a hidden edge case.

## Evidence links
- `docs/PRIVATE_LLM_BACKEND.md`
- `docs/REMOTE_HELPER_COMPUTE_CONTROL.md`
- `docs/EVIDENCE_REMOTE_COMPUTE.md`
- `press/conference_packet.md`

## Policy references (for claims review)
- `docs/ORG_BOUNDARY_EXPLAINER.md`
- `docs/RBAC_GUIDE.md`
- `docs/RISK_AND_DATA_POSTURE.md`
