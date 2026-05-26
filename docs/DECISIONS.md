# Decisions (active)

This file tracks current live decisions and constraints.
Historical implementation logs and superseded decisions are archived by month in `docs/decisions/archive/`.

## Active Decisions Snapshot

- [Auth model: student access](#auth-model-student-access)
- [Identity SSO expansion path](#identity-sso-expansion-path)
- [Trust primitives: student data controls](#trust-primitives-student-data-controls)
- [Offline upload queue for intermittent networks](#offline-upload-queue-for-intermittent-networks)
- [Student kiosk shell mode](#student-kiosk-shell-mode)
- [Database workload split roadmap](#database-workload-split-roadmap)
- [Telemetry endpoint addressing policy](#telemetry-endpoint-addressing-policy)
- [Execution sequencing: 30/60/90 reliability-first plan](#execution-sequencing-306090-reliability-first-plan)
- [Artifact-first sharing defaults](#artifact-first-sharing-defaults)
- [Program profiles for cohort age bands](#program-profiles-for-cohort-age-bands)
- [Stability freeze and change budget](#stability-freeze-and-change-budget)
- [Decision ownership and review cadence](#decision-ownership-and-review-cadence)
- [Organization boundary and staff roles](#organization-boundary-and-staff-roles)
- [Org boundary deployment policy](#org-boundary-deployment-policy)
- [Class assignments and teacher-first class ordering](#class-assignments-and-teacher-first-class-ordering)
- [Syllabus compilation scratch export](#syllabus-compilation-scratch-export)
- [Paid cohort enrollment controls](#paid-cohort-enrollment-controls)
- [Service boundary: Homework Helper separate service](#service-boundary-homework-helper-separate-service)
- [Helper engine modularization seam](#helper-engine-modularization-seam)
- [Helper view helper split seam](#helper-view-helper-split-seam)
- [Helper chat request/deps split seam](#helper-chat-requestdeps-split-seam)
- [Helper tests package split seam](#helper-tests-package-split-seam)
- [ClassHub tests package split seam](#classhub-tests-package-split-seam)
- [Student join service seam](#student-join-service-seam)
- [Student home and upload service seam](#student-home-and-upload-service-seam)
- [Teacher shared helpers split seam](#teacher-shared-helpers-split-seam)
- [Teacher roster class service seam](#teacher-roster-class-service-seam)
- [Teacher roster class export split seam](#teacher-roster-class-export-split-seam)
- [Teacher class endpoint split seam](#teacher-class-endpoint-split-seam)
- [Teacher materials endpoint split seam](#teacher-materials-endpoint-split-seam)
- [Teacher students endpoint split seam](#teacher-students-endpoint-split-seam)
- [Teacher invites endpoint split seam](#teacher-invites-endpoint-split-seam)
- [Teacher support endpoint split seam](#teacher-support-endpoint-split-seam)
- [Teacher org endpoints split seam](#teacher-org-endpoints-split-seam)
- [Teacher account endpoints split seam](#teacher-account-endpoints-split-seam)
- [Teacher home context split seam](#teacher-home-context-split-seam)
- [Teacher SSO endpoint split seam](#teacher-sso-endpoint-split-seam)
- [Teacher landing update helper seam](#teacher-landing-update-helper-seam)
- [Teacher RBAC endpoint split seam II](#teacher-rbac-endpoint-split-seam-ii)
- [Teacher RBAC helper split seam](#teacher-rbac-helper-split-seam)
- [Teacher roster code/reorder helper seam](#teacher-roster-codereorder-helper-seam)
- [Shared zip export helper seam](#shared-zip-export-helper-seam)
- [Routing mode: local vs domain Caddy configs](#routing-mode-local-vs-domain-caddy-configs)
- [Cookie secure flags follow transport mode](#cookie-secure-flags-follow-transport-mode)
- [Authoring template lesson slug convention](#authoring-template-lesson-slug-convention)
- [Documentation as first-class product surface](#documentation-as-first-class-product-surface)
- [Registry-backed docs truth spine (2026-04-04)](#registry-backed-docs-truth-spine-2026-04-04)
- [Teacher docs journey layering](#teacher-docs-journey-layering)
- [Public docs plain-language default](#public-docs-plain-language-default)
- [Spanish/Somali localization parity](#spanishsomali-localization-parity)
- [Feature maturity ledger and evaluator quickstart](#feature-maturity-ledger-and-evaluator-quickstart)
- [Docs Mermaid readability defaults](#docs-mermaid-readability-defaults)
- [Secret handling: env-only secret sources](#secret-handling-env-only-secret-sources)
- [Operator profile white-labeling](#operator-profile-white-labeling)
- [Compose env dollar escaping](#compose-env-dollar-escaping)
- [Request safety and helper access posture](#request-safety-and-helper-access-posture)
- [Observability and retention boundaries](#observability-and-retention-boundaries)
- [Deployment guardrails](#deployment-guardrails)
- [Guided stack bootstrap wrapper](#guided-stack-bootstrap-wrapper)
- [Accessibility smoke gate](#accessibility-smoke-gate)
- [Accessibility runtime contract](#accessibility-runtime-contract)
- [View wildcard import guardrail](#view-wildcard-import-guardrail)
- [CI speed and signal quality](#ci-speed-and-signal-quality)
- [Non-root Django runtime containers](#non-root-django-runtime-containers)
- [Compose least-privilege flags](#compose-least-privilege-flags)
- [Pinned infrastructure images + latest-tag CI guard](#pinned-infrastructure-images-latest-tag-ci-guard)
- [Container image scanning + immutable-ready pin policy (2026-04-04)](#container-image-scanning-immutable-ready-pin-policy-2026-04-04)
- [CSP rollout modes](#csp-rollout-modes)
- [CSP acceptance-check guardrail (2026-04-04)](#csp-acceptance-check-guardrail-2026-04-04)
- [CSP strict flip hold (2026-02-24 to 2026-03-02)](#csp-strict-flip-hold-2026-02-24-to-2026-03-02)
- [Glass theme static assets](#glass-theme-static-assets)
- [Helper widget static assets](#helper-widget-static-assets)
- [Helper widget error transparency](#helper-widget-error-transparency)
- [Helper response language contract](#helper-response-language-contract)
- [Helper conversation memory](#helper-conversation-memory)
- [Helper conversation compaction + class reset control](#helper-conversation-compaction-and-class-reset-control)
- [Coursepack validation gate](#coursepack-validation-gate)
- [Overview-derived coursepack scaffolds](#overview-derived-coursepack-scaffolds)
- [Coursepack authoring SDK and registry path](#coursepack-authoring-sdk-and-registry-path)
- [Redirect target validation](#redirect-target-validation)
- [Lesson file path containment](#lesson-file-path-containment)
- [Untrusted token validation without regex](#untrusted-token-validation-without-regex)
- [Error-response redaction](#error-response-redaction)
- [Signal wiring and RAG SQL identifier hardening](#signal-wiring-and-rag-sql-identifier-hardening)
- [Teacher authoring templates](#teacher-authoring-templates)
- [Syllabus export access and backups](#syllabus-export-access-and-backups)
- [Teacher UI comfort mode](#teacher-ui-comfort-mode)
- [Teacher portal complexity budget](#teacher-portal-complexity-budget)
- [Teacher unified class workspace](#teacher-unified-class-workspace)
- [Teacher inline lesson images](#teacher-inline-lesson-images)
- [Helper scope signing](#helper-scope-signing)
- [Helper event ingestion boundary](#helper-event-ingestion-boundary)
- [Edge block for internal endpoints](#edge-block-for-internal-endpoints)
- [Helper grounding for Piper hardware](#helper-grounding-for-piper-hardware)
- [Helper lesson citations](#helper-lesson-citations)
- [Helper local curriculum RAG](#helper-local-curriculum-rag)
- [Helper YAML config layering](#helper-yaml-config-layering)
- [Helper uses a provider abstraction for private LLM backends (2026-03-28)](#helper-uses-a-provider-abstraction-for-private-llm-backends-2026-03-28)
- [Hosted OpenAI Responses now uses the shared provider layer (2026-04-11)](#hosted-openai-responses-now-uses-the-shared-provider-layer-2026-04-11)
- [Private Ollama remains the active remote path; vLLM stays swap-ready (2026-03-28)](#private-ollama-remains-the-active-remote-path-vllm-stays-swap-ready-2026-03-28)
- [Bounded remote helper compute lease control (2026-04-08)](#bounded-remote-helper-compute-lease-control-2026-04-08)
- [Production transport hardening](#production-transport-hardening)
- [Content parse caching](#content-parse-caching)
- [Admin access 2FA](#admin-access-2fa)
- [Teacher onboarding invites + 2FA](#teacher-onboarding-invites-and-2fa)
- [Teacher route 2FA enforcement](#teacher-route-2fa-enforcement)
- [Facilitator CLI auth/session contract](#facilitator-cli-authsession-contract)
- [Staff auth POST throttling](#staff-auth-post-throttling)
- [Lesson asset delivery hardening](#lesson-asset-delivery-hardening)
- [Optional separate asset origin](#optional-separate-asset-origin)
- [Upload content validation](#upload-content-validation)
- [Deployment timezone by environment](#deployment-timezone-by-environment)
- [Migration execution at deploy time](#migration-execution-at-deploy-time)
- [Teacher daily digest + closeout workflow](#teacher-daily-digest-and-closeout-workflow)
- [Submission query composite indexes](#submission-query-composite-indexes)
- [Module/material prefetch contract for roster and UI density](#modulematerial-prefetch-contract-for-roster-and-ui-density)
- [Student portfolio export](#student-portfolio-export)
- [Checklist, reflection, and rubric material types](#checklist-reflection-and-rubric-material-types)
- [Outcome events and certificate rollups](#outcome-events-and-certificate-rollups)
- [Outcomes and certificate semantics contract](#outcomes-and-certificate-semantics-contract)
- [Automated retention maintenance](#automated-retention-maintenance)
- [Release verdict: 2026-02-21 hardening/polish push](#release-verdict-2026-02-21-hardeningpolish-push)
- [Test gap triage policy](#test-gap-triage-policy)
- [Performance triage policy](#performance-triage-policy)

## Archive Index

- [decisions/archive/2026-02.md](decisions/archive/2026-02.md)
- [decisions/archive/2026-01.md](decisions/archive/2026-01.md)

## Release verdict: 2026-02-21 hardening/polish push

**Current decision:**
- Treat the 2026-02-21 hardening/polish push as deploy-ready.
- Keep `/teach` strict-smoke credential/session setup as an operational prerequisite, not a code blocker.
- Keep the observed server timeout in this validation window classified as expected/non-regression until new evidence shows user-facing impact.

**Verification evidence (server run):**
- `classhub` targeted tests passed: `hub.tests.StudentDataControlsTests` + `hub.tests.TeacherPortalTests` (22 tests, OK).
- `helper` targeted tests passed: `tutor.tests.HelperChatAuthTests` (27 tests, OK).
- Smoke checks passed for `/healthz`, `/helper/healthz`, `/join`, and `/helper/chat`.
- Remaining strict-smoke failure was `/teach` login path using static credentials, consistent with OTP/session setup mismatch rather than application regression.

**Why this remains active:**
- Keeps the release record honest about what is truly green vs what is environment configuration debt.
- Preserves an auditable boundary between product regressions and operator prerequisites.

## Test gap triage policy

**Current decision:**
- Treat analyzer-reported "missing tests" findings as triage input, not automatic work.
- First confirm whether coverage already exists in adjacent integration/service tests.
- Add new tests only for uncovered behavior branches or for pure helper logic that materially improves regression detection.

**Why this remains active:**
- Prevents duplicate low-signal tests when the behavior is already covered elsewhere.
- Keeps test additions focused on real risk: boundary conditions, fallback behavior, and append-only/retention guards.

## Performance triage policy

**Current decision:**
- Take bounded micro-optimizations when they are low-risk and local:
  - use set-backed membership for deduping untrusted lists,
  - cache repeated manifest loads within a single resolution pass,
  - prefer retry-on-constraint for token allocation over preflight existence checks.
- Do not rewrite bounded loops that intentionally preserve per-target error handling or cross-database behavior unless profiling shows real pressure.

**Why this remains active:**
- Keeps the codebase responsive to easy wins without obscuring correctness-focused control flow.
- Avoids churn from analyzer suggestions that ignore small bounded loops or backend-split write semantics.

## Helper uses a provider abstraction for private LLM backends (2026-03-28)

**Current decision:**
- Keep `tutor/views.py` and `tutor/engine/*` as the HTTP and orchestration boundary.
- Add a provider layer under `tutor/llm/*` for concrete private backend integrations.
- Route current Ollama calls through that provider layer, while keeping the higher-level helper endpoint contract unchanged.
- Prefer generic `LLM_*` env names for new deploys, while continuing to honor legacy helper/Ollama env names.

**Why this remains active:**
- Preserves the existing tested helper flow instead of introducing a parallel, unused abstraction.
- Makes later swaps to vLLM or another private OpenAI-compatible server a contained provider change rather than a helper endpoint rewrite.
- Keeps privacy/logging controls and health probing in one auditable place.

## Hosted OpenAI Responses now uses the shared provider layer (2026-04-11)

**Current decision:**
- Keep `LLM_BACKEND=openai` as the operator-facing hosted OpenAI setting.
- Normalize that backend name to `openai_responses` internally.
- Route hosted OpenAI calls and healthchecks through `tutor/llm/*` instead of a separate direct runtime implementation.
- Continue honoring `OPENAI_*` envs, while also accepting generic `LLM_*` aliases where appropriate.

**Why this remains active:**
- Removes the split between the helper provider layer and the hosted OpenAI path.
- Makes backend naming, health probes, and retry behavior consistent across Ollama, hosted OpenAI, and OpenAI-compatible servers.
- Reduces drift risk between docs, runtime behavior, and operator tooling.

## Private Ollama remains the active remote path; vLLM stays swap-ready (2026-03-28)

**Current decision:**
- Treat private remote Ollama over a host-to-host tailnet as the active first-pass deployment target.
- Keep vLLM artifacts documented and ready, but position them as the next swap path rather than the current required runtime.
- Require remote-backend acknowledgement and a direct helper-container connectivity check before full smoke.
- Keep the GPU node loopback-bound and tailnet-only; browsers never reach it directly.
- For createMPLS-style production deployments, recommend Headscale on a tiny Ubuntu VPS as the control plane behind that private path while keeping the app runtime control-plane-agnostic.

**Why this remains active:**
- Matches the current operator reality: the deployment is already using an Ollama distribution.
- Preserves a boring, low-change path to a private remote model host now, without foreclosing a later move to a cleaner OpenAI-compatible endpoint.
- Keeps the GPU host replaceable and least-privilege by default.

## Bounded remote helper compute lease control (2026-04-08)

## Django upload header bypass patch level (2026-05-13)

**Current decision:**
- Pin ClassHub to `Django==5.2.14` or newer patch releases on the `5.2.x` line.
- Do not treat `FILE_UPLOAD_MAX_MEMORY_SIZE` as a sufficient standalone control.
- Require request body size limits at the web server/edge layer (Caddy or upstream proxy) for defense in depth.

**Why this remains active:**
- `Django==5.2.13` is in the affected advisory range for ASGI upload requests with missing or understated `Content-Length`.
- Patch-level upgrade removes the known bypass class in supported branches.
- Edge request-size limits prevent oversized body abuse even when app-layer checks are bypassed or misconfigured.

**Current decision:**
- Keep remote helper compute off by default.
- Add a staff-only, class-scoped activation lease so teachers/admins can enable expensive remote compute for a bounded live-session window.
- Gate the capability with `CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED=1` plus explicit paid-usage acknowledgement via `CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED=1`.
- Use an explicit remote-compute state model (`off`, `requested`, `starting`, `ready`, `degraded`, `stopping`, `error`) and only route helper traffic remotely when the class state is `ready`.
- Treat `ready` as a helper-verified state, not just a provider-declared state:
  - helper must confirm the remote backend is reachable with the configured auth/model path,
  - helper must complete a warm chat probe,
  - helper only promotes to `ready` when that probe stays within `HELPER_REMOTE_COMPUTE_READY_MAX_SECONDS`.
- Keep provider credentials and orchestration APIs server-side behind helper internal control endpoints.
- Keep provider integration behind a small replaceable server-side adapter seam (`thunder_webhook` / generic webhook), not inside view/template logic.
- Keep student/browser traffic on the public LMS path; the remote compute control is never a student-facing affordance.
- If the remote path errors during an active lease, fall back to local/default helper compute for the request.
- Persist the active remote lease and per-class accounting in helper-owned Django tables, with cache used only as a hot-read mirror.
- Reconcile durable remote lease state on helper start via a management command before gunicorn boots, so cold-cache restarts do not wait for a teacher page refresh to normalize expired or degraded leases.
- Expose a teacher-facing JSON/CSV remote-helper snapshot export from `/teach/class/<id>` so staff can preserve the current lease/accounting state outside the live dashboard card.
- Derive a low-noise operator trend summary from that class evidence so `/teach/class/<id>` and snapshot exports can flag waste, fallback rate, provider reachability, and slow warm-up without requiring raw log reads.
- Expose one aggregate helper-owned operator snapshot so `/teach/data-lifespan` can show active lease posture and recent class trend rows without making the LMS reach into helper tables directly.
- Keep lightweight operator accounting for the remote path:
  - activations,
  - average time to ready,
  - remote-routed chats,
  - fallbacks to local/default,
  - degraded transitions,
  - provider-unreachable events,
  - activations that never actually routed remotely.

**Why this remains active:**
- Makes expensive remote GPU capacity cost-aware without turning it into an always-on dependency.
- Preserves the public LMS boundary while still giving staff a practical session-time control.
- Keeps orchestration-specific details behind a small auditable seam instead of spreading provider logic through the app.
- Survives helper worker restarts and cold-cache boots without forgetting whether a lease is still active or whether recent remote usage was worth the cost.

## Auth model: student access

**Current decision:**
- Students join with class code + display name.
- Same-device rejoin can use a signed HTTP-only device hint cookie.
- Cross-device rejoin uses student return code.
- Teachers/admins authenticate with Django auth credentials.

**Why this remains active:**
- Keeps student friction low while limiting impersonation risk.
- Maintains minimal student PII collection in MVP.

## Identity SSO expansion path

**Current decision:**
- Keep current runtime auth posture unchanged:
  - students default to class code + display name (pseudonym-first),
  - teachers/admins continue on Django auth + OTP.
- Maintain a documented implementation path for future identity expansion at:
  - [IDENTITY_SSO_EXPANSION_PLAN.md](IDENTITY_SSO_EXPANSION_PLAN.md)
- Ship T0 provider/config scaffolding first (settings parsing + env validation + template keys), without enabling any SSO login route by default.
- Ship T1 UI/routing scaffold behind the same feature flag:
  - `/teach/login` provider buttons + guarded `/teach/sso/start/<provider>` and `/teach/sso/callback/<provider>` routes,
  - with explicit scaffold responses for providers not yet activated.
- Ship T2 Google callback flow:
  - real Google OIDC authorize/callback exchange with signed state + nonce validation,
  - pre-provisioned staff account mapping by email,
  - provider/domain guardrails and no-store auth redirects,
  - password fallback behavior controlled by `CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK`.
- Sequence identity work as:
  1. teacher SSO first (Google callback live, Microsoft/custom next),
  2. optional student school-account login only as opt-in per org/class,
  3. pseudonym-preserving display defaults remain enforced for classroom/public surfaces.

**Why this remains active:**
- Preserves low-friction, privacy-forward current behavior while still defining a concrete enterprise-auth path.
- Prevents ad-hoc auth changes by requiring a staged rollout with explicit security/privacy gates.

## Trust primitives: student data controls

**Current decision:**
- Keep a plain-language trust page at `/trust` linked from join and student pages.
- Treat class retention as a class-level preset (`erase_after_7_days`, `keep_for_semester`, `keep_until_student_deletes`) and apply it through existing prune commands rather than parallel cleanup systems.
- Default new classes to the most privacy-preserving preset that still supports active classes: `erase_after_7_days`.
- Keep student controls in `/student/my-data`:
  - student can rename display name at any time, with existing display-name safety checks,
  - student can export submissions,
  - deletion is policy-aware via `CLASSHUB_STUDENT_SELF_DELETE_MODE`:
    - `direct` (default): immediate deletion of student submissions/responses + related upload/artifact events,
    - `request`: log a deletion request event for staff follow-up.
- Support facilitation notes use structured staff-only tags (controlled vocabulary) instead of freeform notes by default:
  - `needs_extra_time`
  - `prefers_quiet`
  - `device_help`
- Support tags are class-bounded and permission-bounded:
  - only staff with class manage rights can add/remove,
  - tags are only shown in teacher class dashboard views.

**Why this remains active:**
- Gives students direct agency over identity/work without adding new PII collection.
- Keeps deletion semantics explicit and auditable for programs that require staff-mediated removal.
- Preserves a help-first, low-surveillance facilitation model with constrained metadata rather than narrative dossiers.

## Offline upload queue for intermittent networks

**Current decision:**
- Add a browser-local upload queue for the student upload workflow (`/material/<id>/upload`) using IndexedDB.
- Keep normal student authentication/session boundaries; queued uploads flush through session-scoped API endpoints:
  - `GET /api/v1/student/csrf`
  - `POST /api/v1/student/material/<id>/upload`
- Use low-bandwidth sync behavior:
  - immediate flush attempt on submit,
  - queue on transient failures/offline conditions,
  - retry on reconnect, manual retry button, and modest interval retries.
- Do not add high-frequency polling loops or new background telemetry.
- Keep queue state local to the browser/device and class session; no new student PII fields are introduced.

**Why this remains active:**
- Prevents student data loss when connectivity is unstable.
- Keeps classroom flow resilient in low-infrastructure deployments.
- Preserves privacy and minimal data collection while improving reliability.

## Student kiosk shell mode

**Current decision:**
- Add an optional kiosk shell mode for student-facing routes behind `CLASSHUB_STUDENT_KIOSK_PWA_ENABLED`.
- Kiosk mode can be toggled per device using `?kiosk=1` / `?kiosk=0` and persists in a cookie.
- When active, non-allowlisted student routes redirect to class flow entry (`/student` or `/`), preserving focus on:
  - join,
  - class home,
  - material upload and core lesson routes.
- Student templates expose an installable manifest (`/student-shell.webmanifest`) and register the existing upload sync service worker with secure-context guardrails.
- Keep teacher/admin routes outside kiosk route gating.

**Why this remains active:**
- Supports tablet/shared-device classrooms with lower navigation complexity.
- Keeps the resilient upload queue path intact while making the shell installable.
- Preserves operator control by making kiosk behavior explicit and reversible per deployment.

## Database workload split roadmap

**Current decision:**
- Keep one core transactional database as the source of truth for class/auth/material/submission workflows.
- Execute a phased telemetry split first:
  - isolate append-only, high-churn event workloads from core transactional paths,
  - use dual-write + read toggles for a near-zero-downtime migration,
  - require parity checks before any telemetry-only write mode.
- Do not split core submission/class metadata in Phase 1.

Execution runbook:
- [TELEMETRY_DB_SPLIT_PLAN.md](TELEMETRY_DB_SPLIT_PLAN.md)
- Telemetry split plan now includes execution-slice backlog, code touchpoint inventory, gate-based exit criteria, and operator verification commands for phased rollout ownership.
- Phase 1 Slice 0/1/2/3/4/5/6 scaffolding is now shipped: telemetry mode env guardrails (`off|dual|telemetry_only`, `core|telemetry`), optional telemetry DB registration in settings, telemetry router + dedicated `hub_telemetry` schema app, centralized dual-write service seams for student event/outcome emit points, telemetry-aware read abstraction for support/rollup/lifespan event queries, baseline split-write instrumentation counters/log fields, an idempotent `backfill_telemetry_events` management command, and a strict `check_telemetry_parity` management command for cutover gates are in place. Slice 7 operator evidence tooling (`scripts/telemetry_stabilization_evidence.sh`) is available for parity/smoke/rollback artifact capture; release-cycle sign-off is still required.

**Why this remains active:**
- Reduces blast radius from telemetry spikes and prune operations.
- Improves restore/recovery posture for core LMS operations.
- Preserves a reversible migration path via environment toggles.

## Telemetry endpoint addressing policy

**Current decision:**
- `CLASSHUB_TELEMETRY_DATABASE_URL` must target an established private telemetry database endpoint (private DNS or managed DB endpoint), not a public app URL.
- Keep internal helper/classhub callback URLs on private/container routing (for example `http://helper_web:8000/...` and `http://classhub_web:8000/...`), not public domain routes.
- Keep rollout posture aligned with the telemetry split runbook:
  - local/day-1: telemetry URL unset, `WRITE_MODE=off`, `READ_MODE=core`,
  - staging: private telemetry URL + `WRITE_MODE=dual` + parity-gated `READ_MODE` cutover,
  - production: private telemetry URL + `READ_MODE=telemetry`, default `WRITE_MODE=dual` until Gate D sign-off.

**Why this remains active:**
- Preserves edge hardening and internal endpoint isolation.
- Reduces accidental coupling to external routing and TLS edge behavior for service-to-service traffic.
- Keeps telemetry rollout reproducible across local, staging, and production.

## Execution sequencing: 30/60/90 reliability-first plan

**Current decision:**
- Adopt a concrete 30/60/90 execution sequence starting March 7, 2026, with dated checkpoints captured in [TELEMETRY_DB_SPLIT_PLAN.md](TELEMETRY_DB_SPLIT_PLAN.md).
- Prioritize work in this order:
  - Phase 1 telemetry stabilization evidence + SLO guardrails first,
  - strict organization-boundary rollout (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True`) second,
  - hotspot-first teacher portal service extraction third,
  - RBAC Phase 2 operator UX enablement after boundary hardening is stable.
- Keep Telemetry Phase 2 implementation blocked until explicit go/no-go review passes (no automatic start after Day 90).
- Treat helper RAG expansion beyond curriculum as opt-in only:
  - class-scoped,
  - staff-approved source set,
  - auditable source list in operator evidence artifacts.

Execution ownership and gates:
- 30-day checkpoint (April 6, 2026): first full telemetry evidence packet + rollback drill.
- 60-day checkpoint (May 6, 2026): consecutive green evidence windows and explicit write-mode sign-off (`dual` vs `telemetry_only`).
- 90-day checkpoint (June 5, 2026): approved Phase 2 design packet or documented deferral with next review date.

**Why this remains active:**
- Prevents migration churn from outrunning operational evidence.
- Keeps privacy boundary correctness ahead of ergonomics/features.
- Makes scale-up decisions falsifiable through dated checkpoints and SLO gates rather than intuition.

## Artifact-first sharing defaults

**Current decision:**
- Keep student artifact publishing opt-in and default OFF at artifact level:
  - uploads are private to student + staff unless the student explicitly publishes.
- Treat class gallery visibility as a two-part gate:
  - student publish intent (`is_published`),
  - teacher moderation approval (`is_gallery_shared`).
- Keep session-level gallery control at module scope (`Module.gallery_enabled`) so facilitators can disable a session wall without deleting work.
- Add student-facing artifact surfaces that preserve pseudonymous join:
  - `/student/portfolio` for "What I made" with lesson/date/station filters,
  - `/student/gallery` for session celebration, showing only published + approved artifacts.
- Keep process logging optional and non-judgmental:
  - optional `process_note` prompt ("What did you try? What did you change?")
  - sentence starters remain language-aware and editable via course-manifest starter overrides.

**Why this remains active:**
- Supports celebration/inspiration while keeping privacy and teacher judgment in control.
- Avoids ranking/leaderboard pressure and keeps feedback mechanics supportive.
- Preserves storage and retention controls by reusing existing submission + prune pipelines.

## Program profiles for cohort age bands

**Current decision:**
- Keep one platform and one data model across elementary, secondary, and advanced cohorts.
- Add `CLASSHUB_PROGRAM_PROFILE` (`elementary`, `secondary`, `advanced`) as a defaults layer only.
- Preserve explicit env override precedence:
  - profile defaults may set baseline behavior,
  - explicit env vars (`HELPER_STRICTNESS`, `HELPER_SCOPE_MODE`, `HELPER_TOPIC_FILTER_MODE`, `CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN`) always win.
- Use profile defaults to reduce pilot setup variance without adding new product primitives.

**Why this remains active:**
- Supports younger learners without forking operations or code paths.
- Keeps middle/high school behavior stable by default (`secondary`).
- Maintains privacy-forward posture while lowering operator misconfiguration risk.

## Stability freeze and change budget

**Current decision:**
- Adopt a 30-day stability freeze focused on survivability and maintenance risk reduction.
- During the freeze, allow only:
  - UX smoothing on existing workflows
  - docs clarity improvements
  - scenario testing and rehearsal coverage
  - observability/hardening work that adds no new product primitives
- Do not ship new features, new analytics primitives, or schema expansion unless delay is riskier than a minimal fix.
- Freeze exceptions require explicit justification (`Freeze exception`), smallest-change rationale, and named reviewer sign-off.

**Why this remains active:**
- Keeps scope pressure from eroding reliability during high-change periods.
- Makes maintenance debt visible and governable instead of implicit.

## Decision ownership and review cadence

**Current decision:**
- Every policy-level operational decision must have:
  - an owner role (`ED`, `OD`, `maintainer`, or shared ownership),
  - a review cadence (`monthly` or `quarterly`),
  - a linked artifact where the check happens (runbook, risk register, or rehearsal record).
- `MAINTENANCE_RISK_REGISTER.md` is the canonical list of currently accepted maintenance risks and owners.
- Policy choices that affect security/privacy/runtime behavior must be written in docs, not only PR/chat context.

**Why this remains active:**
- Prevents silent policy drift when contributors or staff roles change.
- Reduces single-maintainer dependency by making review ownership explicit.

## Organization boundary and staff roles

**Current decision:**
- Add first-class `Organization` and `OrganizationMembership` models in ClassHub.
- `Class.organization` is optional during rollout so existing data can migrate safely.
- Staff role choices are `owner`, `admin`, `teacher`, `viewer`.
- Superusers can manage organizations and org memberships directly in the teacher portal (`/teach`) without using Django admin.
- Teacher portal class visibility now uses org memberships when present:
  - superusers keep full visibility.
  - staff with no memberships keep legacy global class visibility.
  - staff with memberships are restricted to classes in their active org memberships.
- Optional hard boundary mode `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1` removes legacy fallback:
  - staff with no active org membership cannot list/access classes or create classes.
- Mutating class endpoints require manage roles (`owner`, `admin`, `teacher`) once memberships are present; `viewer` is read-only.

**Why this remains active:**
- Establishes a concrete multi-program boundary without forcing a one-shot data migration.
- Preserves backward compatibility for existing single-tenant deployments.
- Provides a clear path to paid cohort partitioning and partner-org separation.

## Org boundary deployment policy

**Current decision:**
- Keep `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0` only for transitional or low-risk deployments where org memberships are not fully established.
- For production programs with multiple organizations or partner boundaries, target `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`.
- Any deployment running `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0` must document:
  - why fallback remains necessary,
  - who approved the exception,
  - when the setting will be reviewed.
- Verify this setting during quarterly restore rehearsal and monthly staff-access review.

**Why this remains active:**
- Makes boundary posture a conscious operational policy instead of an inherited default.
- Prevents accidental over-broad staff class visibility as programs grow.

## Class assignments and teacher-first class ordering

**Current decision:**
- Add `ClassStaffAssignment` to represent teacher-to-class assignment within the classes they can already access.
- Keep org membership as the access boundary; assignments do not reduce org class visibility.
- Teacher-facing class lists (`/teach` and `/teach/lessons`) now rank assigned classes first.
- New classes created by non-superuser staff auto-create an active assignment for the creator.

**Why this remains active:**
- Preserves org-wide course/syllabus access while making daily “my classes” workflows faster.
- Gives a clean foundation for future per-class staffing controls without changing student auth/join UX.

## Syllabus compilation scratch export

**Current decision:**
- Teacher portal syllabus compilation (`/teach/import-syllabus-source`) is scratch-based and export-oriented.
- Uploaded `.md`, `.docx`, and `.zip` sources compile into a temporary working directory and return a downloadable coursepack ZIP.
- The teacher-facing flow does not mutate `CONTENT_ROOT`, overwrite repository course folders, or provision a class as a side effect.
- If staff lacks the current organization capability for this tool, syllabus compilation returns an error instead of opening a hidden content-write path.
- Zip syllabus imports now map lesson-support images by filename prefix (`01-...`, `02-...`) to matching sessions:
  - images are written into course content under `lesson_support_images/`,
  - generated lesson front matter includes `support_images`,
  - those files live inside the downloadable coursepack artifact rather than being written into the live curriculum tree by the web request.

**Why this remains active:**
- Preserves a file-first, Git-native curriculum model for self-hosted deployments.
- Keeps the teacher workflow useful without adding hidden in-image writes or mutable canonical content paths.
- Preserves supportive visual context from teacher-authored zip bundles inside the exported artifact without manual per-lesson asset re-upload.

## Paid cohort enrollment controls

**Current decision:**
- Each class has explicit `enrollment_mode`:
  - `open`: class code and invite links both accepted.
  - `invite_only`: only invite links can join.
  - `closed`: all new joins blocked.
- Teacher class dashboard now exposes an enrollment-mode control at class scope.
- Invite links remain optional and can still enforce expiry + seat caps.

**Why this remains active:**
- Supports paid cohort windows without forcing student login friction.
- Lets staff close enrollment cleanly while preserving active roster/session operations.

## Admin access 2FA

**Current decision:**
- Django admin uses OTP-verified superuser sessions by default in both services.
- `DJANGO_ADMIN_2FA_REQUIRED=1` is the expected production posture.
- OTP enrollment is provisioned operationally via `bootstrap_admin_otp` command.

**Why this remains active:**
- Reduces risk from password reuse/phishing against admin accounts.
- Preserves clear separation: teacher workflow in `/teach`, hardened ops workflow in `/admin`.

## Teacher onboarding invites and 2FA

**Current decision:**
- Superusers can create teacher staff accounts from `/teach` and trigger invite emails.
- Invite email carries a signed, expiring link to `/teach/2fa/setup`.
- `/teach/2fa/setup` provisions and confirms teacher TOTP devices via QR + manual secret fallback.
- Staff can self-manage their own teacher profile details (name/email/password) from `/teach` without using Django admin.
- SMTP remains environment-configured; local default is console backend for safe non-production testing.

**Why this remains active:**
- Removes CLI-only OTP provisioning friction during teacher onboarding.
- Keeps enrollment self-service while preserving short-lived, signed invite boundaries.

## Teacher route 2FA enforcement

**Current decision:**
- `/teach/*` now requires OTP-verified staff sessions by default (`DJANGO_TEACHER_2FA_REQUIRED=1`).
- `/teach/2fa/setup` and `/teach/logout` stay exempt so enrollment/recovery remains reachable.
- Middleware redirects unverified staff to `/teach/2fa/setup?next=<requested_teach_path>`.

**Why this remains active:**
- Teacher routes can rotate join codes, manage rosters, and access submissions; password-only is insufficient.
- Keeps teacher onboarding usable while enforcing stronger session posture on operational pages.

## Facilitator CLI auth/session contract

**Current decision:**
- `hubctl` reuses existing teacher web auth policy instead of creating a parallel token system.
- CLI session bootstrap runs through `/teach/login` and, when required, `/teach/2fa/setup`.
- Teacher API write calls stay CSRF-protected; CLI clients must carry session cookies + CSRF header.
- CLI command failures map to typed non-zero exit codes for automation safety (`auth`, `forbidden`, `not_found`, `rate_limited`, `network`).

**Why this remains active:**
- Avoids policy drift between browser and headless operator flows.
- Preserves existing OTP + audit boundaries while enabling terminal-first workflows.
- Keeps automation behavior predictable for scripts and runbooks.

## Staff auth POST throttling

**Current decision:**
- Cache-backed fixed-window throttling is enforced on:
  - `POST /admin/login/`
  - `POST /teach/2fa/setup`
- Limits are environment-tunable:
  - `CLASSHUB_AUTH_RATE_LIMIT_WINDOW_SECONDS`
  - `CLASSHUB_ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE`
  - `CLASSHUB_TEACHER_2FA_RATE_LIMIT_PER_MINUTE`
- Throttled responses return HTTP `429` with `Retry-After` and `no-store` caching.

**Why this remains active:**
- Adds explicit brute-force/backoff protection to staff authentication surfaces.
- Uses shared request-safety cache primitives so behavior remains consistent with existing rate-limit controls.

## Lesson asset delivery hardening

**Current decision:**
- Lesson assets are served as attachments by default.
- Inline rendering is restricted to allow-listed media/PDF MIME types only.
- Asset responses include `X-Content-Type-Options: nosniff`; inline responses include CSP sandbox.

**Why this remains active:**
- Reduces stored-XSS risk from HTML/script-like teacher uploads served on the LMS origin.
- Preserves inline behavior for expected classroom media types.

## Optional separate asset origin

**Current decision:**
- Set `CLASSHUB_ASSET_BASE_URL` to rewrite lesson media URLs (`/lesson-asset/*`, `/lesson-video/*`) to a separate origin.
- Markdown-rendered lesson links and teacher asset/video copy links both use this rewrite when configured.
- Leave `CLASSHUB_ASSET_BASE_URL` empty for same-origin behavior.

**Why this remains active:**
- Gives operators an incremental path to isolate uploaded media origin without changing teacher authoring flow.
- Keeps local/day-1 deployments simple while enabling stricter production hosting topologies.

## Upload content validation

**Current decision:**
- Extension checks remain, but uploads now include lightweight content checks before storage.
- `.sb3` uploads must be valid zip archives and include `project.json`.
- Magic-byte checks reject obvious extension/content mismatches for common file types.

**Why this remains active:**
- Reduces support churn from corrupted/mislabeled files.
- Adds cheap safety checks without introducing heavyweight scanning dependencies.

## Deployment timezone by environment

**Current decision:**
- Both services read `DJANGO_TIME_ZONE` (default `America/Chicago`) instead of hardcoding UTC.
- Operators set local classroom timezone in `compose/.env` (for example `America/Chicago`).

**Why this remains active:**
- Release-date gating uses `timezone.localdate()`, so deployment timezone must match classroom expectations.
- Prevents off-by-one-day release behavior around local midnight.

## Migration execution at deploy time

**Current decision:**
- Deploy/doctor/golden scripts explicitly run `manage.py migrate --noinput` for both services.
- Production defaults set `RUN_MIGRATIONS_ON_START=0`; local/dev can opt into boot-time migrations explicitly.

**Why this remains active:**
- Explicit migration steps are safer for multi-instance deployment workflows.
- Prevents migration races when multiple app containers start concurrently.

## Large upload reliability timeout

**Current decision:**
- Class Hub Gunicorn timeout is configurable via `CLASSHUB_GUNICORN_TIMEOUT_SECONDS` (default `1200`).
- Upload body limits remain controlled separately by `CLASSHUB_UPLOAD_MAX_MB` and `CADDY_CLASSHUB_MAX_BODY`.

**Why this remains active:**
- Classroom upload reliability is dominated by slow/shared Wi-Fi conditions.
- A low app worker timeout causes avoidable upload failures even when body limits are configured correctly.

## Service boundary: Homework Helper separate service

**Current decision:**
- Homework Helper remains a separate Django service.
- Routing is under `/helper/*` through Caddy.
- Helper policy, limits, and failure handling are isolated from Class Hub page delivery.

**Why this remains active:**
- Protects classroom materials from helper outages.
- Preserves independent scaling and policy controls as helper traffic grows.

## Helper engine modularization seam

**Current decision:**
- Keep `/helper/chat` as the single HTTP endpoint in `tutor/views.py`, but move backend/runtime internals into `tutor/engine/*`.
- Introduce an explicit backend interface contract (`BackendInterface`) plus callable adapters in `tutor/engine/backends.py`.
- Keep concrete backend provider implementations (`ollama_chat`, `openai_chat`, `mock_chat`) in `tutor/engine/backends.py`; `tutor/views.py` keeps thin compatibility shims only.
- Keep policy heuristics in dedicated engine modules (`tutor/engine/heuristics.py`, `reference.py`, `circuit.py`) and call them through thin view wrappers.
- Keep auth/session boundary checks and runtime request plumbing in engine modules (`tutor/engine/auth.py`, `runtime.py`) and call them via wrapper functions in `tutor/views.py`.
- Keep scope and configuration contracts explicit in engine modules:
  - `tutor/engine/context_envelope.py` for signed scope/context resolution,
  - `tutor/engine/runtime_config.py` for profile-aware policy defaults,
  - `tutor/engine/execution_config.py` for execution/runtime tuning defaults.
- Keep `tutor.views` helper function names stable as compatibility wrappers during extraction.
- Helper endpoint tests default to the real `/helper/chat` path with `HELPER_LLM_BACKEND=mock`; fault-injection tests patch engine-level seams (`tutor.engine.backends.*`) instead of view wrappers.

**Why this remains active:**
- Reduces change risk by preserving endpoint behavior and test patch targets while creating a clean seam for future streaming/new providers.
- Makes backend retry/circuit/reference code independently testable without expanding view-layer complexity.
- Keeps tests focused on runtime behavior while reducing brittle coupling to temporary view compatibility shims.

## Helper view helper split seam

**Current decision:**
- Keep `/helper/chat` in `tutor/views.py` as the stable endpoint and test patch surface.
- Move stable helper functions (redaction/env/runtime wrappers, reference loading, conversation memory adapters, helper event detail shaping) into `tutor/views_chat_helpers.py`.
- Keep patch-sensitive seams in `tutor/views.py` (for example `build_instructions`, `acquire_slot`, `time.sleep`, and auth table/session checks) so existing tests and operational monkeypatch targets remain unchanged.

**Why this remains active:**
- Reduces `tutor/views.py` size and complexity without forcing a broad test rewrite.
- Preserves backwards compatibility for current test patch targets while creating a clearer path for future endpoint splits.

## Helper chat request/deps split seam

**Current decision:**
- Keep `chat` in `tutor/views.py` as the stable HTTP boundary and patch target.
- Move request-shaping helpers (actor/client derivation, session id loading, rate-limit gate, payload parse) into `tutor/views_chat_request.py`.
- Move `ChatDeps` wiring into `tutor/views_chat_deps.py`, but pass patch-sensitive callables from `tutor/views.py` (`build_instructions`, reference loaders, backend wrappers) so existing tests keep patching `tutor.views.*`.
- Move backend/auth runtime internals into `tutor/views_chat_runtime.py`, while keeping compatibility wrappers in `tutor/views.py` (`_actor_key`, `_student_session_exists`, `_call_backend_with_retries`, etc.) so existing patch targets stay stable.

**Why this remains active:**
- Keeps the endpoint code focused on request/response flow while reducing nested branching inside `chat`.
- Preserves compatibility with current test monkeypatches and operational seams while continuing the gradual split of `tutor/views.py`.

## Helper tests package split seam

**Current decision:**
- Replace single-file `tutor/tests.py` with package-based tests under `tutor/tests/`.
- Split by feature area:
  - `test_chat_endpoint.py` for `/helper/chat` integration/auth behavior.
  - `test_access.py` for helper admin/session and security-header/CSP/site-mode behavior.
  - `test_events.py` for internal ClassHub event forwarding behavior.
  - `test_internal_reset.py` for helper internal reset endpoint behavior.
  - `test_engine.py` for engine/auth/backend/heuristics/runtime unit behavior.
  - `test_view_modules.py` for request/runtime helper module unit tests.
- Keep backwards-compatible test target imports via `tutor/tests/__init__.py` so `tutor.tests.HelperChatAuthTests` remains valid.

**Why this remains active:**
- Reduces single-file test gravity and makes targeted test runs/reviews cheaper.
- Preserves operator/CI command compatibility while improving test maintainability.

## ClassHub tests package split seam

**Current decision:**
- Replace single-file `hub/tests.py` with package-based tests under `hub/tests/`.
- Split by feature area:
  - `test_teacher_admin_portal.py`
  - `test_teacher_admin_auth.py`
  - `test_teacher_admin_release.py`
  - `test_student_ops.py`
  - `test_security_integration.py`
- Keep backwards-compatible test target imports via `hub/tests/__init__.py` so commands targeting `hub.tests.<ClassName>` remain valid.
- Add `scripts/test_teacher_admin.sh` as the canonical compose-backed runner for teacher/admin-focused ClassHub tests.

**Why this remains active:**
- Reduces monolithic test-file gravity in ClassHub and makes feature-specific test review/runs faster.
- Preserves existing CI/server invocation patterns while enabling incremental test-module refactors.

## Teacher auth view split seam

**Current decision:**
- Keep `hub/views/teacher_parts/auth.py` as a compatibility re-export module.
- Split teacher auth endpoints by concern:
  - `auth_login.py` for login/logout flow.
  - `auth_teacher_accounts.py` for superuser teacher account creation + onboarding invite.
  - `auth_teacher_2fa.py` for invite-token/session resolution and teacher 2FA setup/verification.
- Keep existing import surfaces and route wiring stable via re-exports from `teacher_parts/auth.py`.

**Why this remains active:**
- Reduces dense-function pressure and review overhead in one auth-heavy file.
- Preserves endpoint behavior and patch/import stability while enabling smaller, safer auth changes.

## Student join service seam

**Current decision:**
- Keep student view endpoints as I/O adapters and move join/session mechanics into dedicated service helpers in `hub/services/student_join.py`.
- Service layer now owns:
  - return-code + device-hint + name-match identity resolution,
  - student identity allocation with return-code collision retries,
  - signed device-hint cookie issue/clear behavior.
- `join_class` in `hub/views/student.py` keeps request parsing, locking/transaction boundaries, session mutation, response shaping, and event emission.

**Why this remains active:**
- Reduces “big file gravity” in student views while preserving endpoint behavior.
- Creates a stable seam for future join/auth policy changes without high-risk view rewrites.

## Student home and upload service seam

**Current decision:**
- Keep `student_home` and `material_upload` endpoints in `hub/views/student.py` as thin request/response adapters.
- Move release/access map assembly and submission rollup logic into `hub/services/student_home.py`.
- Move upload release-gate and upload validation/scan/persist orchestration into `hub/services/student_uploads.py`.
- Preserve existing upload patch targets in view tests by passing `scan_uploaded_file` and `validate_upload_content` from the view into the service call.

**Why this remains active:**
- Continues reducing “big file gravity” in `hub/views/student.py` without changing endpoint behavior.
- Makes student home and upload business rules independently testable and safer to iterate as policy evolves.

## Teacher shared helpers split seam

**Current decision:**
- Keep `from .shared import *` in teacher endpoint modules as a compatibility import seam.
- Split helper implementation by concern into:
  - `hub/views/teacher_parts/shared_auth.py` (staff/2FA/setup helpers),
  - `hub/views/teacher_parts/shared_tracker.py` (digest/tracker aggregations),
  - `hub/views/teacher_parts/shared_routing.py` (redirect/query/path helpers),
  - `hub/views/teacher_parts/shared_ordering.py` (ordering/title helpers).
- Keep `hub/views/teacher_parts/shared.py` as a re-export module so endpoint behavior and imports stay stable while implementation moves out of a single large file.

**Why this remains active:**
- Reduces “big file gravity” in teacher helper code without forcing a broad import rewrite in one pass.
- Creates clearer seams for future extraction into `hub/services/*` while preserving current endpoint contracts.

## Teacher roster class service seam

**Current decision:**
- Keep `hub/views/teacher_parts/roster_class.py` as the HTTP adapter layer.
- Move heavy dashboard data assembly and class-day submissions export archive construction into `hub/services/teacher_roster_class.py`.
- Keep audit logging, response shaping, and redirect/not-found behavior in the view layer.

**Why this remains active:**
- Reduces dense view-file pressure and function complexity without changing endpoint contracts.
- Creates explicit seams for further query optimization and targeted service-level tests.

## Teacher roster code/reorder helper seam

**Current decision:**
- Centralize class join-code allocation into `_next_unique_class_join_code(...)` in `hub/views/teacher_parts/shared_ordering.py`.
- Centralize directional order updates into `_apply_directional_reorder(...)` in `hub/views/teacher_parts/shared_ordering.py`.
- `hub/views/teacher_parts/roster.py` now calls these helpers for class create/reset/rotate and module/material move actions.

**Why this remains active:**
- Removes repeated collision-retry and reorder blocks from roster endpoints while preserving endpoint behavior.
- Keeps future changes to code generation or reorder semantics in one place instead of multiple view branches.

## Shared zip export helper seam

**Current decision:**
- Centralize ZIP export primitives in `hub/services/zip_exports.py`:
  - `temporary_zip_archive(...)`
  - `reserve_archive_path(...)`
  - `write_submission_file_to_archive(...)`
- Student portfolio export and teacher zip exports now call these shared helpers instead of duplicating low-level tempfile/zip write/fallback blocks.

**Why this remains active:**
- Reduces repeated archive-writing code across student and teacher endpoints while preserving response and file naming behavior.
- Keeps file-path fallback behavior explicit in one place (enabled for student portfolio export; disabled for teacher classroom batch exports).

## Routing mode: local vs domain Caddy configs

**Current decision:**
- Unknown/no domain: use `compose/Caddyfile.local`.
- Known domain: use `compose/Caddyfile.domain` with Caddy-managed TLS.
- Optional separate asset host: use `compose/Caddyfile.domain.assets` + `ASSET_DOMAIN`.
- Template selection is explicit via `CADDYFILE_TEMPLATE` in `compose/.env`.

**Why this remains active:**
- Keeps local setup simple while preserving production-safe HTTPS behavior.
- Reduces configuration drift during deployment.

## Cookie secure flags follow transport mode

**Current decision:**
- `DJANGO_SESSION_COOKIE_SECURE` and `DJANGO_CSRF_COOKIE_SECURE` are explicit deployment settings.
- Defaults remain secure when `DJANGO_DEBUG=0`, but local/day-1 HTTP presets set both to `0`.
- Domain/TLS presets set both to `1`.
- Student join POSTs use a server-rendered CSRF token first (`{% csrf_token %}`), with cookie lookup fallback in JS, to reduce false CSRF failures caused by stale/duplicate browser cookie state during host/domain transitions.

**Why this remains active:**
- Prevents join/session breakage when running HTTP in local mode with `DJANGO_DEBUG=0`.
- Keeps HTTPS deployments strict by default without coupling cookie transport policy to debug mode.

## Authoring template lesson slug convention

**Current decision:**
- Teacher authoring template session blocks now show lesson slug guidance as `sNN-your-topic-slug`.
- Templates explicitly instruct teachers to keep lesson slugs lowercase with numbers/dashes and to keep the `sNN-` prefix aligned to session number.

**Why this remains active:**
- Makes the pre-built template files safer to copy into `course.yaml` without slug formatting drift.
- Reduces import/validation mistakes caused by inconsistent lesson slug formatting.

## Documentation as first-class product surface

**Current decision:**
- Documentation is treated as a core deliverable, not a trailing artifact.
- Role-based entrypoint remains [START_HERE.md](START_HERE.md).
- Documentation contract and standards are centralized in [index.md](index.md).
- Guided, hands-on learning tracks are maintained in [LEARNING_PATHS.md](LEARNING_PATHS.md).
- Symptom-first operational triage is maintained in [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- Documentation pedagogy and maintainer writing standards are maintained in [TEACHING_PLAYBOOK.md](TEACHING_PLAYBOOK.md).

**Why this remains active:**
- This repository is both an operational system and a teaching object.
- Maintainers need repeatable onboarding and incident handling, not tribal knowledge.
- Shipping docs in lockstep with code reduces deployment and handoff risk.

## Teacher docs journey layering

**Current decision:**
- Maintain a teacher-first guided read path at [TEACHER_DOCS_JOURNEY.md](TEACHER_DOCS_JOURNEY.md).
- Keep teacher documentation layered by depth:
  - orientation/intent: [START_HERE_INSTRUCTOR.md](START_HERE_INSTRUCTOR.md),
  - class-day execution: [RUN_A_CLASS_TOMORROW.md](RUN_A_CLASS_TOMORROW.md),
  - plain-language workflow: [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md),
  - screen-level reference: [TEACHER_PORTAL.md](TEACHER_PORTAL.md),
  - issue handling: [COMMON_SCENARIOS.md](COMMON_SCENARIOS.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- Link this journey from shared landing surfaces (`START_HERE`, `DOCS_MAP`, docs `index`) so non-developer staff can navigate without guessing.

**Why this remains active:**
- Teacher users need "what do I read next?" guidance more than API-level detail.
- A layered path reduces cognitive load while keeping advanced docs available on demand.
- It improves onboarding consistency for schools where facilitator technical comfort varies.

## Public docs plain-language default

**Current decision:**
- Public/role-facing docs default to plain-language wording first, with technical detail clearly labeled as optional or advanced.
- Avoid engineering shorthand in public pages when a plain equivalent exists:
  - prefer "current release" over "MVP",
  - prefer "optional features" over "flags",
  - prefer "planned" over "RFC-only",
  - prefer "technical lead/setup team" over internal role jargon when audience is non-technical.
- Keep implementation-level specifics in operator/developer docs and explicitly tagged technical blocks inside shared pages.

**Why this remains active:**
- Mixed audiences (teachers, leadership, partners) need clear operational meaning before implementation detail.
- Plain language improves trust and reduces onboarding friction in school/community contexts.
- Labeled advanced sections preserve technical accuracy without overwhelming non-technical readers.

## Spanish/Somali localization parity

**Current decision:**
- Keep Somali (`so`) and Spanish (`es`) catalogs aligned at the message-id level.
- Require every Spanish `msgid` to have a non-empty Somali `msgstr` entry.
- Enforce parity with:
  - `python3 scripts/check_i18n_spanish_somali_parity.py`
- Track a non-blocking "lantern" metric in the same guard:
  - count of Somali entries still identical to English fallback copy.
- Keep an explicit human review packet for trust-critical Somali copy:
  - [LOCALIZATION_SO_REVIEW_PACKET.md](LOCALIZATION_SO_REVIEW_PACKET.md)
- Extend i18n smoke tests so Somali is validated on the same student surfaces already covered in Spanish:
  - `/student/my-data`
  - `/student/portfolio`
- If a reviewed Somali translation is not yet ready for a new string, keep a non-empty interim fallback and follow up with language review.

**Why this remains active:**
- Prevents Somali support from lagging behind Spanish as copy changes ship.
- Makes localization drift visible early in CI/local checks instead of after release.
- Keeps family-facing language support more consistent across key student flows.

## Feature maturity ledger and evaluator quickstart

**Current decision:**
- Maintain [FEATURE_MATURITY.md](FEATURE_MATURITY.md) as the canonical matrix for:
  - `Live (default)` capabilities,
  - `Live (flagged)` capabilities with rollout toggles,
  - RFC-only roadmap items.
- Maintain [START_HERE_EVALUATOR.md](START_HERE_EVALUATOR.md) as the shortest non-technical evaluation path.
- Expose a superuser-only read-only operator config snapshot in `/teach` to surface active profile/flag state and link operators to maturity/evaluator docs.

**Why this remains active:**
- Reduces cognitive load from distributed feature flags and profile/config knobs.
- Makes rollout readiness visible without requiring direct code or compose file inspection.
- Gives non-technical stakeholders a bounded evaluation path that separates shipped behavior from roadmap intent.

## Docs Mermaid readability defaults

**Current decision:**
- Docs build now includes `docs/stylesheets/extra.css` via `extra_css` in `mkdocs.yml`.
- Mermaid runtime is vendored in-repo (`docs/javascripts/vendor/mermaid.min.js`) and loaded from `mkdocs.yml` as a local static asset instead of a third-party CDN.
- Mermaid blocks default to fit the full width of the content column for in-flow readability.
- Mermaid diagrams are click-to-zoom: selecting a diagram opens a lightbox overlay sized to viewport height for focused reading, with `Esc` and outside-click close behavior.
- Lightbox interaction is implemented in `docs/javascripts/diagram-lightbox.js` and loaded from `mkdocs.yml` as a first-party asset.
- Mermaid containers keep horizontal-scroll fallback enabled for oversized render edge-cases.
- Mermaid defaults are tuned in `docs/javascripts/mermaid-init.js` with `themeVariables.fontSize=22px` and `useMaxWidth=true` for common diagram types.
- Mermaid init normalizes wrapped markdown output (`<pre class="mermaid"><code>...</code></pre>`) into renderable Mermaid blocks before running `mermaid.run(...)`.
- Mermaid init now catches render promise failures and logs structured parse/render diagnostics to the console (page path + error payload) to avoid opaque unhandled-promise errors.
- Docs layout now widens Material's default grid limit (`.md-grid`) on desktop (`min-width: 60em`) to `max-width: min(96vw, 120rem)` so wiki pages use window width more effectively.

**Why this remains active:**
- Keeps diagrams readable in normal page flow while preserving a large-focus view for dense content.
- Reduces friction for non-technical readers by making zoom behavior discoverable (click diagram) instead of requiring horizontal scroll.
- Reduces supply-chain fragility for docs rendering by avoiding runtime fetches from external script CDNs.

## Secret handling: env-only secret sources

**Current decision:**
- Secrets are injected via environment (`compose/.env` or deployment environment), never committed to git.
- `DJANGO_SECRET_KEY` is required in both services.
- Class Hub device-hint cookies are signed with a dedicated `DEVICE_HINT_SIGNING_KEY` (separate from `DJANGO_SECRET_KEY` in production).
- Cross-service bearer tokens and backend API keys are inventoried in [SECRET_ROTATION.md](SECRET_ROTATION.md) with explicit rotation and break-glass revoke steps.
- Mode-specific env examples (`.env.example.local`, `.env.example.domain`) stay non-sensitive and document required knobs.

**Why this remains active:**
- Prevents insecure fallback secret boot behavior.
- Reduces blast radius if one signing key leaks (device-hint cookie signatures stay independently rotatable).
- Supports basic secret hygiene for self-hosted operations.
- Keeps rotation/update workflow operationally simple.
- Makes bearer-token rotation an operator task with a documented verification path instead of an implicit memory exercise.

## Operator profile white-labeling

**Current decision:**
- Operator identity text is environment-configured, not template-edited.
- Class Hub reads the operator profile from:
  - `CLASSHUB_PRODUCT_NAME`
  - `CLASSHUB_OPERATOR_NAME`
  - `CLASSHUB_OPERATOR_DESCRIPTOR`
  - `CLASSHUB_STORAGE_LOCATION_TEXT` (optional explicit override)
  - `CLASSHUB_PRIVACY_PROMISE_TEXT`
  - `CLASSHUB_ADMIN_LABEL`
- Templates consume this profile through a global context processor so join/privacy/admin surfaces stay consistent.

**Why this remains active:**
- Makes forks/deploys feel native without patching HTML files.
- Reduces accidental branding/privacy copy drift across join, helper, upload, and admin pages.
- Keeps white-label changes auditable in deployment config instead of code diffs.

## Compose env dollar escaping

**Current decision:**
- Values in `compose/.env` that include `$` must be Compose-safe:
  - either wrap the value in single quotes
  - or escape each `$` as `$$`
- `scripts/validate_env_secrets.sh` enforces this for `CADDY_ADMIN_BASIC_AUTH_HASH` to prevent interpolation drift and noisy deploy warnings.
- Caddy now fail-closes (`503`) when `CADDY_ADMIN_BASIC_AUTH_ENABLED=1` is set with shipped/default admin basic-auth credentials.
- `compose/.env.example.domain` intentionally keeps `CADDY_ADMIN_BASIC_AUTH_ENABLED=1` and blank credentials as a secure-but-not-usable default until operators set real values.

**Why this remains active:**
- Docker Compose treats bare `$...` as interpolation, which can silently mutate secrets and spam warnings during deploy.
- Bcrypt hashes (`$2...`) are common in Caddy basic-auth setup and need explicit handling.

## Request safety and helper access posture

**Current decision:**
- Helper chat requires either authenticated staff context or valid student classroom session context.
- Student session validation checks classhub identity rows when table access is available, and fails open when classhub tables are unavailable.
- Shared request-safety helpers are canonical for proxy-aware client IP parsing and cache-backed limiter behavior.
- Shared limiter helpers fail open when cache backends error, and emit request-id-tagged warnings when available.
- Helper admin follows superuser-only access, matching classhub admin posture.

**Why this remains active:**
- Prevents policy drift between services.
- Reduces abuse risk while keeping classroom usage workable behind proxies.

## Observability and retention boundaries

**Current decision:**
- Teacher/staff mutations emit append-only `AuditEvent` records.
- Student join/rejoin/upload/helper-access metadata emits append-only `StudentEvent` records.
- Retention is operator-managed using prune commands.
- Successful retention command runs (`prune_submissions`, `prune_student_events`) now emit explicit audit stamps (`retention.prune_*`) so operators can verify last-run timestamps without reading host logs.
- Operator retention verification is available in a read-only teacher-side dashboard at `/teach/data-lifespan` (owner/admin/superuser capability).
- Student event prune supports optional CSV snapshot export before deletion (`prune_student_events --export-csv <path>`).
- File-backed upload models use delete/replacement cleanup signals to prevent orphan file accumulation.
- Orphan file scavenger is available for legacy cleanup (`scavenge_orphan_uploads`, report-first).

**Why this remains active:**
- Preserves incident traceability and accountability.
- Keeps privacy boundaries explicit by storing metadata rather than raw helper prompt/file content in event logs.
- Supports audit handoff and offline review before destructive retention actions.
- Keeps upload storage bounded and predictable after roster resets, asset/video deletes, and file replacements.
- Turns retention policy verification into a visible operational check instead of a cron/log assumption.

## Deployment guardrails

**Current decision:**
- Deploy path uses migration gate + smoke checks + deterministic compose invocation.
- Caddy mount source must match the expected compose config file.
- Deploy script explicitly reloads Caddy config from `/etc/caddy/Caddyfile` before smoke checks.
- Domain-template Caddy CEL expressions must use unquoted `{env.*}` placeholders inside `expression` matchers.
- `scripts/system_doctor.sh` is the canonical one-command stack diagnostic.
- `scripts/operator_preflight.py` is the canonical deploy-time config coherence gate for routing mode, public origins, internal helper URLs, and feature-gated helper/remote-compute env blocks.
- Golden-path smoke can auto-provision fixtures via `scripts/golden_path_smoke.sh`.
- Class Hub static assets are collected during image build; runtime migrations stay disabled in production (`RUN_MIGRATIONS_ON_START=0`) while deploy scripts run explicit migrations.
- Edge health remains `/healthz`; `/upstream-healthz` is now operator-controlled via `CADDY_EXPOSE_UPSTREAM_HEALTHZ` (`1` expose, `0` edge `404`).
- Smoke checks default to `http://localhost` when `CADDYFILE_TEMPLATE=Caddyfile.local`, regardless of placeholder `SMOKE_BASE_URL` values in env examples.
- CI doctor smoke uses `HELPER_LLM_BACKEND=mock` to keep `/helper/chat` deterministic without runtime model pull dependencies.
- Golden smoke issues a server-side staff session key for `/teach` checks so admin-login form changes (OTP/superuser prompts) do not create false negatives.
- `deploy_with_smoke.sh` now auto-retries with golden smoke when strict smoke fails specifically due stale `SMOKE_CLASS_CODE` (`/join` -> `invalid_code`).
- `smoke_check.sh` now emits an explicit stale-code diagnostic for `/join invalid_code` failures, with remediation guidance.
- `smoke_check.sh` now retries `/helper/chat` for transient backend startup failures (`502` + `ollama_error`) before failing deploy smoke.
- `smoke_check.sh` now also retries `/helper/chat` for transient queue saturation failures (`503` + `busy`) so CPU-bound helper stacks do not false-fail on first saturation response.
- `smoke_check.sh` uses a longer default wait for queue saturation retries (`SMOKE_HELPER_CHAT_BUSY_RETRY_DELAY_SECONDS=30`) while keeping non-queue retry delays short (`SMOKE_HELPER_CHAT_RETRY_DELAY_SECONDS=3`).
- `smoke_check.sh` now captures and prints `/student` response headers/body excerpts when the student page returns non-200, so CI output includes concrete failure context.
- `golden_path_smoke.sh` and `system_doctor.sh` now print compose service state + recent logs when smoke fails, not only when `compose up` fails.
- Smoke diagnostics now query compose logs using service names (`caddy`, `classhub_web`, `helper_web`, etc.) rather than container names so log collection does not fail under `docker compose logs`.
- Regression coverage is required for helper auth/admin hardening and backend retry/circuit behavior.
- `ops/systemd/classhub-retention.service` now refuses root execution by default unless `CLASSHUB_ALLOW_ROOT_MAINTENANCE=1` is explicitly set as a break-glass override.
- `ops/systemd/classhub-retention.service` now pins explicit non-root runtime identity (`User=lms`, `Group=docker`) and baseline systemd hardening flags (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `ProtectHome`, etc.).
- Compose app services (`classhub_web`, `helper_web`) now run with `read_only: true` root filesystems plus explicit writable mounts/tmpfs.
- Caddy read-only root filesystem is available as an opt-in hardening toggle (`CADDY_READ_ONLY=true`), with default off until operators validate deploy/smoke behavior on their host.

**Why this remains active:**
- Prevents avoidable outages from config drift.
- Fails fast on deploy-time config mismatches that previously surfaced only after containers were already up.
- Prevents Caddy crash-loop on startup caused by invalid CEL expression rendering.
- Prevents stale edge routing behavior when Caddy container remains running across deploys.
- Catches regressions before users encounter them.
- Reduces operator setup friction for smoke checks that previously depended on static credentials.
- Reduces startup-time healthcheck failures from long runtime `collectstatic` work.
- Prevents CI from accidentally probing external placeholder domains while validating local compose stacks.
- Prevents CI flakes when local model servers are reachable but model weights are not yet loaded.
- Keeps strict smoke focused on route authorization outcomes instead of brittle intermediate login form internals.
- Reduces deploy failures caused by class-code rotation between smoke runs without weakening strict smoke checks for other regressions.
- Reduces false negative deploy smoke failures when local Ollama is healthy but still warming model execution for the first generation request.
- Reduces time-to-root-cause for student-flow regressions by surfacing route-level failure payloads and backend traceback logs in the same CI run.
- Reduces accidental privileged execution for unattended retention maintenance jobs.
- Reduces host-level blast radius if the maintenance unit or script path is compromised.

## Guided stack bootstrap wrapper

**Current decision:**
- Keep `scripts/quickstart_stack.sh` as the low-friction installer wrapper for local/domain onboarding.
- Wrapper responsibilities:
  - initialize `compose/.env` from mode-aware examples,
  - generate required secrets when placeholder values are present,
  - set helper YAML config path (`HELPER_CONFIG_FILE=/app/config/helper.config.yaml`),
  - start compose + run migrations,
  - optionally create/update admin account,
  - optionally load demo content and run `system_doctor.sh --smoke-mode golden`.
- Keep existing lower-level scripts (`deploy_with_smoke.sh`, `system_doctor.sh`, `load_demo_coursepack.sh`) as composable primitives beneath this wrapper.

**Why this remains active:**
- Reduces operator cognitive load from high-volume env/config setup.
- Lowers onboarding failure rate for less technical users while preserving explicit, inspectable script behavior.
- Keeps reliability checks in the default path instead of relying on tribal knowledge.

## Accessibility smoke gate

**Current decision:**
- Add a Playwright + axe smoke gate (`scripts/a11y_smoke.sh`) that runs against the running compose stack.
- Keep scope intentionally small and deterministic:
  - student join page
  - teacher home
  - teacher lessons
  - teacher class dashboard + certificate eligibility page (when smoke class fixture exists)
- CI runs this gate in `stack-smoke` after golden smoke fixture provisioning.
- Fail threshold defaults to `critical` impact violations to avoid noisy rollout regressions while still blocking severe accessibility breaks.

**Why this remains active:**
- Adds fast regression detection for high-impact accessibility failures in core classroom flows.
- Reuses the same stack fixtures/session setup as smoke checks, reducing separate test harness drift.
- Keeps the gate low-friction and repeatable for local/operator runs (`bash scripts/a11y_smoke.sh`).

## Accessibility runtime contract

**Current decision:**
- `scripts/a11y_smoke.sh` is an operator-facing host tool and requires:
  - `node`
  - `npm`
  - `docker`
- Preferred baseline for operator hosts is Node 20 LTS.
- First-run browser provisioning is explicit (`--install-browsers`) and should be treated as normal setup, not an optional extra.
- Do not silently downgrade by skipping a11y smoke when node/npm are missing; fix host prerequisites or run in CI before release.

**Why this remains active:**
- Prevents false assumptions that a11y smoke is Docker-only.
- Keeps accessibility checks reliable and repeatable across server and CI environments.

## CI speed and signal quality

**Current decision:**
- Python-focused workflows now enable pip caching through `actions/setup-python` cache settings with explicit dependency paths.
- Lint workflow now enforces a frontend static asset reference guard (`scripts/check_frontend_static_refs.py`) so classhub template `{% static 'css/*' %}` and `{% static 'js/*' %}` links fail fast if files are missing.
- Lint workflow now enforces a template inline-JS guard (`scripts/check_no_inline_template_js.py`) that fails on:
  - `<script>` tags without `src`
  - inline event handler attributes (`onclick=`, `onsubmit=`, etc.)
- Lint workflow now enforces a template inline-CSS guard (`scripts/check_no_inline_template_css.py`) that fails on:
  - `<style>` blocks
  - inline style attributes (`style=...`)
- Lint workflow now enforces a view security-header helper guard (`scripts/check_view_header_helpers.py`) that fails on direct `Cache-Control` / `Pragma` / CSP / `nosniff` / `Referrer-Policy` assignments inside view modules.
- Lint workflow now enforces dense-view line budgets (`scripts/check_view_size_budgets.py` + `scripts/view_size_budgets.json`) so large view modules cannot grow without an intentional, reviewed budget change.
- Lint workflow now enforces dense-view function budgets (`scripts/check_view_function_budgets.py` + `scripts/view_function_budgets.json`) so large endpoint callables and helper functions cannot grow without explicit review.
- Lint workflow now enforces service-layer import direction (`scripts/check_no_service_imports_from_views.py`) so service modules cannot import from `views.*`.
- Lint workflow now enforces explicit service exports (`scripts/check_no_dynamic_service_all_exports.py`) to block dynamic `__all__` patterns that leak internal helpers as accidental API.
- CI now runs Django `check --deploy --fail-level WARNING` for both services in prod-like env via `.github/workflows/deploy-check.yml`.
  - Expected baseline-specific warnings `security.W019` (`X_FRAME_OPTIONS != DENY`) and `security.W021` (`SECURE_HSTS_PRELOAD != True`) are explicitly silenced in both Django settings modules because framing is controlled by CSP `frame-ancestors 'self'` and HSTS preload ownership is at the edge.
- `docs/ENDPOINT_CHECKLIST.md` is the required baseline for new endpoints (cache, CSP, download hardening, throttling, logging minimization, and error-handling expectations).
- CI now writes concise human-readable summaries to `$GITHUB_STEP_SUMMARY`:
  - Ruff advisory stats in `lint`.
  - Coverage totals for `classhub-tests` and `helper-tests` in `test-suite`.
  - Ruff summary now tolerates missing advisory output and prints a fallback message instead of cascading failure noise after a blocking Ruff error.
- Workflow syntax is now protected by a dedicated YAML parse gate (`.github/workflows/workflow-lint.yml`) so malformed workflow files fail fast in CI.
- Workflow semantics are now additionally linted with `actionlint` in `.github/workflows/workflow-lint.yml`.
- CI surface coverage now includes a contract guard (`scripts/check_ci_workflow_coverage.py`) that fails when critical workflows/jobs/check commands disappear.
- CI now enforces subsystem test inventory coverage (`scripts/check_test_inventory_coverage.py`) with:
  - required high-signal test files across ClassHub + Helper,
  - minimum test function counts by subsystem directory,
  - required smoke/doctor script presence.
- Both workflow/test inventory guards now support `--json` output for dashboard ingestion without parsing human logs.

**Why this remains active:**
- Reduces repeated dependency download/install time across CI jobs.
- Improves review ergonomics by surfacing key quality signals without opening artifacts.
- Catches frontend wiring regressions with a lightweight check while keeping the stack Python-first.
- Prevents CSP regressions by blocking inline JS reintroduction in templates.
- Prevents CSP regressions by blocking inline CSS reintroduction in templates.
- Keeps security-header behavior centralized and reviewable via shared helpers.
- Adds a ratchet on view-file growth so service-layer extraction progress cannot silently regress.
- Adds a second ratchet at function granularity so dense endpoint callables keep trending smaller over time.
- Prevents service/view layering inversion from reappearing during refactors.
- Prevents accidental service API surface expansion from broad dynamic exports.
- Catches production security-setting drift earlier than unit/integration tests.
- Prevents silent CI gate loss from workflow syntax regressions.
- Reduces false-negative confidence from silently dropped CI jobs/steps during rapid workflow edits.
- Prevents accidental erosion of test breadth while features ship quickly.

## Non-root Django runtime containers

**Current decision:**
- `classhub_web` and `helper_web` images run as a non-root `app` user by default.
- Compose passes `APP_UID`/`APP_GID` as Docker build args so operators can align container identity with host-mounted data ownership.
- `scripts/validate_env_secrets.sh` enforces positive integer `APP_UID`/`APP_GID` values to prevent accidental root runtime identity.
- Day-1 bootstrap now creates `data/classhub_uploads` and `data/ollama` directories up front for predictable non-root startup behavior.

**Why this remains active:**
- Reduces blast radius from runtime process compromise compared with root-running containers.
- Keeps upload and generated-template writes reliable on bind-mounted storage when UID/GID is explicitly aligned.

## Compose least-privilege flags

**Current decision:**
- `caddy`, `classhub_web`, and `helper_web` set `security_opt: ["no-new-privileges:true"]`.
- `classhub_web` and `helper_web` drop all Linux capabilities via `cap_drop: ["ALL"]`.
- `caddy` drops all capabilities and adds back only `NET_BIND_SERVICE` for `80/443` binding.
- `caddy`, `classhub_web`, and `helper_web` mount `/tmp` as tmpfs (`rw,noexec,nosuid,size=64m`).

**Why this remains active:**
- Reduces privilege-escalation and container-breakout blast radius on public edge/app workloads.
- Keeps required behavior intact (Caddy low-port bind, Django uploads bind-mount writes) while tightening defaults.

## Pinned infrastructure images + latest-tag CI guard

**Current decision:**
- `compose/docker-compose.yml` pins Ollama and MinIO images by versioned tag defaults (`OLLAMA_IMAGE`, `MINIO_IMAGE`) instead of `:latest`.
- `compose/.env.example`, `.env.example.local`, and `.env.example.domain` declare these pinned image tags as explicit operator-facing defaults.
- CI lint now runs `scripts/check_no_latest_tags.py` to fail on committed `:latest` tags in compose/env config files.

**Why this remains active:**
- Improves reproducibility across deploys and classroom sessions by avoiding implicit upstream image churn.
- Converts accidental `:latest` reintroduction into a fast CI failure instead of a runtime surprise on deploy day.

## CSP rollout modes

**Current decision:**
- Add `DJANGO_CSP_MODE` with three supported values:
  - `relaxed` (settings fallback when `DJANGO_CSP_MODE` is unset): relaxed enforced CSP + strict report-only CSP.
  - `report-only`: strict report-only CSP only.
  - `strict`: strict enforced CSP only.
- Keep `DJANGO_CSP_POLICY` and `DJANGO_CSP_REPORT_ONLY_POLICY` as explicit per-header overrides when operators need fully custom directives.
- Apply the same mode resolver in both Class Hub and Homework Helper middleware so headers stay consistent across services.
- Validate `DJANGO_CSP_MODE` in `scripts/validate_env_secrets.sh` to fail fast on invalid deploy config.

**Why this remains active:**
- Provides a predictable migration path from inline-compatible policy to strict CSP without code edits.
- Keeps browser hardening behavior aligned between both services and easier to reason about in ops runbooks.

## CSP strict flip hold (2026-02-24 to 2026-03-02)

**Current decision:**
- Keep compose example defaults at `DJANGO_CSP_MODE=report-only` during the week of Tuesday, February 24, 2026 through Monday, March 2, 2026.
- Do not flip to `strict` before Monday review; confirm report-only violations are clean after template script extraction.
- Transitional canary allowed before full flip:
  - `DJANGO_CSP_MODE=strict`
  - explicit `DJANGO_CSP_POLICY` with `script-src 'self'` and temporary `style-src 'unsafe-inline'`
  - use for staging / controlled windows, then remove `'unsafe-inline'` from `style-src` for full strict enforcement
- Inline script blocks were removed from:
  - `services/classhub/templates/teach_class.html` (moved to `services/classhub/hub/static/js/teach_class.js`)
  - `services/classhub/templates/student_class.html` (moved to `services/classhub/hub/static/js/student_class.js`)
  - `services/classhub/templates/student_join.html` (moved to `services/classhub/hub/static/js/student_join.js`)
  - `services/classhub/templates/teach_join_card.html` (moved to `services/classhub/hub/static/js/teach_join_card.js`)
  - `services/classhub/templates/teach_home.html` (moved to `services/classhub/hub/static/js/teach_home.js`)
  - `services/classhub/templates/lesson_page.html` (moved to `services/classhub/hub/static/js/lesson_page.js`)
  - `services/classhub/templates/admin/login.html` (moved to `services/classhub/hub/static/js/admin_login.js`)
- Remaining inline form confirm handler in `services/classhub/templates/student_my_data.html` was replaced with `data-confirm` + `services/classhub/hub/static/js/confirm_forms.js`.
- Review report-only violations on Monday, March 2, 2026, then decide whether strict CSP can be enabled without class-day regressions.

**Why this remains active:**
- Keeps classroom-critical pages stable while we validate strict-mode behavior against real report-only telemetry.
- Preserves a clear operator checkpoint (Monday review) before enforcing strict CSP globally.

## Glass theme static assets

**Current decision:**
- Move shared `glass_theme` presentation assets out of inline template blocks into:
  - `services/classhub/hub/static/css/glass_theme.css`
  - `services/classhub/hub/static/js/glass_theme.js`
- Keep `services/classhub/templates/includes/glass_theme.html` as a thin include that only emits static `<link>` and `<script src>` tags.
- Preserve existing class names/behavior so consuming templates remain unchanged.

**Why this remains active:**
- Reduces inline script/style surface and improves compatibility with strict CSP rollout.
- Improves client caching and keeps shared visual behavior centralized for safer iteration.

## Helper widget static assets

**Current decision:**
- Move shared `helper_widget` presentation assets out of inline template blocks into:
  - `services/classhub/hub/static/css/helper_widget.css`
  - `services/classhub/hub/static/js/helper_widget.js`
- Keep `services/classhub/templates/includes/helper_widget.html` as a thin include that emits widget markup plus static `<link>` and `<script src>` tags.
- Keep helper behavior and prompt/citation rendering logic unchanged while reducing inline surface.

**Why this remains active:**
- Reduces inline script/style exposure on the model-facing helper surface.
- Improves cacheability and keeps helper UI behavior centralized for safer updates.

## Helper widget error transparency

**Current decision:**
- For non-2xx `/helper/chat` responses, helper UI now surfaces a structured status line in-widget:
  - `Helper error: <error_code> (request <request_id>)` when the API returns JSON with a request id.
  - status-derived fallback codes (for example `csrf_forbidden` for HTTP 403) when the response is non-JSON.
- Keep citations cleared on error responses and network failures.
- Keep detailed diagnostics server-side; UI only exposes coarse code + request id for support correlation.

**Why this remains active:**
- Reduces MTTR during class sessions by making helper failures diagnosable without immediate shell access.
- Gives staff a stable request id they can match against helper/classhub logs.

## Helper response language contract

**Current decision:**
- Helper output language now follows the active Class Hub UI locale deterministically.
- Class Hub passes `language_code` with helper requests; helper normalizes it to the supported set (`en`, `es`, `so`, `ksw`) and returns the applied `response_language`.
- Helper does not switch languages based only on the student's message text.
- Apply the same language contract to both model-backed answers and fixed helper policy/redirect text so behavior stays consistent.
- Apply the same language contract to widget-managed chrome as well (follow-up labels, status text, quick prompts, button/placeholder copy) so the browser UI does not fall back to English while helper replies are localized.

**Why this remains active:**
- Makes helper language behavior inspectable and testable instead of relying on model inference.
- Keeps live classroom behavior aligned with the UI locale that the student or teacher explicitly selected.

## Karen locale code selection (2026-04-02)

**Current decision:**
- Treat "Karen" support in this repo as S'gaw Karen and use ISO 639-3 code `ksw`.
- Register `ksw` in Django's `LANGUAGES` list and helper response-language normalization so locale cookies, `Accept-Language`, and `/helper/chat` all agree on the same code.
- Ship `ksw` across the same repo-shipped family-visible tranche as `es` and `so`:
  - join page `/`
  - teacher login `/teach/login`
  - trust/privacy page `/trust`
  - student routes `/student`, `/student/my-data`, `/student/portfolio`, `/student/gallery`
  - teacher day-mode shell `/teach?portal_mode=day`
- Treat the current Karen catalog as AI-assisted provisional copy pending native-speaker review rather than as final reviewed phrasing.
- Keep helper-widget chrome and quick prompts aligned with the same `ksw` locale instead of as a separate special-case tranche.

**Why this remains active:**
- "Karen" is a language family, so the implementation needs one concrete locale code to be technically stable.
- `ksw` is the standard code used for S'gaw Karen, which keeps future translation review and tooling interoperable.
- AI-assisted provisional copy is preferable to shipping an English-dominant UI on family/student surfaces where Karen is explicitly offered in the language chooser.
- Explicit review labeling preserves honesty about translation quality while still making Karen visible and test-backed across the routes families actually use.

## Request-scoped localization context for Class Hub (2026-04-02)

**Current decision:**
- Add a single request-scoped localization object in Class Hub middleware after Django `LocaleMiddleware`.
- Expose that object as `request.localization`, a template context value, and a `contextvars`-backed accessor for Python helpers.
- Treat `request.localization` as the canonical locale source inside Class Hub; only pass an explicit language code when crossing the `/helper/chat` service boundary.

**Why this remains active:**
- Removes repeated `getattr(request, "LANGUAGE_CODE", "en")` plumbing from view/helper code.
- Gives templates, Python helpers, and helper-widget rendering one stable locale contract.
- Preserves safe request scoping instead of introducing process-global locale state.
- Helper widget chrome and quick-prompt payloads now come from server-side translated template/data seams instead of maintaining parallel browser-only translation tables.

## Helper conversation memory

**Current decision:**
- Helper chat now accepts/returns a `conversation_id` and uses it to keep short-lived context across follow-up turns.
- Conversation turns are cached (not persisted in SQL) and isolated by actor + scope token + conversation id.
- Stored turns are redacted and bounded by env controls:
  - `HELPER_CONVERSATION_ENABLED`
  - `HELPER_CONVERSATION_MAX_MESSAGES`
  - `HELPER_CONVERSATION_TTL_SECONDS`
  - `HELPER_CONVERSATION_TURN_MAX_CHARS`
  - `HELPER_CONVERSATION_HISTORY_MAX_CHARS`
- Student UI now shows a transcript and includes a `Reset chat` action that starts a fresh conversation id.

**Why this remains active:**
- Makes helper responses meaningfully conversational without introducing long-term transcript retention by default.
- Preserves privacy boundaries while improving tutoring quality for clarifying follow-up questions.

## Helper conversation compaction and class reset control

**Current decision:**
- Helper conversation cache now supports lightweight rolling summaries when turn count exceeds `HELPER_CONVERSATION_MAX_MESSAGES`, controlled by `HELPER_CONVERSATION_SUMMARY_MAX_CHARS`.
- Helper responses include a per-turn `intent` tag (for example `debug`, `concept`, `strategy`) derived from the latest student message.
- Helper responses include bounded `follow_up_suggestions` so student UI can present one-tap next prompts per assistant turn.
- Teacher class dashboard includes a `Reset helper conversations` action (`POST /teach/class/<id>/reset-helper-conversations`) that calls helper internal endpoint `POST /helper/internal/reset-class-conversations`.
- Class-level helper reset now exports a JSON archive snapshot (`HELPER_CLASS_RESET_ARCHIVE_DIR`) before deletion when `HELPER_INTERNAL_RESET_EXPORT_BEFORE_DELETE=1` and `HELPER_CLASS_RESET_ARCHIVE_ENABLED=1`.
- Helper reset archive retention is managed by `scripts/retention_maintenance.sh` (`RETENTION_HELPER_EXPORT_DAYS`, default 30), with path guardrails (`/uploads/*`) and periodic permission tightening (`0700` dir, `0600` files).
- Helper reset archives are operator-only artifacts: not served as public Caddy routes and not included in student-facing portfolio exports.
- Helper chat access events now include summarized telemetry fields (`intent`, `follow_up_suggestions_count`, `conversation_compacted`) and `/teach/class/<id>` renders a “Helper Signals” panel for the last `CLASSHUB_HELPER_SIGNAL_WINDOW_HOURS`.
- Internal helper reset endpoint requires `Authorization: Bearer <HELPER_INTERNAL_API_TOKEN>` and clears only indexed student conversation keys for the target class.

**Why this remains active:**
- Keeps prompt size bounded on CPU-constrained local models while retaining useful conversational context.
- Gives teachers a practical classroom control to clear stale helper context without deleting roster/submission data.
- Gives teachers class-level visibility into how students are using helper support without storing raw prompts.
- Supports internal classroom research by preserving a point-in-time snapshot before helper cache deletion.
- Preserves privacy posture: cache-only memory, class-scoped deletion, and explicit internal token boundary.

## Coursepack validation gate

**Current decision:**
- Add `scripts/validate_coursepack.py` to validate `course.yaml` and lesson front matter before deploy/test execution.
- `scripts/content_preflight.sh` now runs coursepack validation before video-order sync checks.
- CI (`.github/workflows/test-suite.yml`, classhub job) runs `python scripts/validate_coursepack.py --all` so malformed coursepacks fail early with actionable errors.

**Why this remains active:**
- Prevents avoidable runtime lesson failures caused by malformed manifests, missing lesson files, or broken front matter.
- Keeps content-as-code reliable by enforcing basic schema and file-boundary expectations in both operator preflight and CI.

## Overview-derived coursepack scaffolds

**Current decision:**
- When only an overview/public syllabus exists, ship a repo-backed draft coursepack instead of blocking on full teacher-plan documents.
- Mark the structure implicitly through lesson content and documentation as overview-derived scaffolding:
  - preserve source metadata such as title, grade band, age band, duration, materials, and privacy posture,
  - create a coherent session sequence that matches the stated progression,
  - keep artifact capture and helper grounding aligned with the overview rather than inventing advanced scope.
- The initial `energy_electronics_circuits_9_session` coursepack follows this pattern based on `energy_electronics_circuits_overview_import_ready.md`.
- For the day-one littleBits session in that coursepack, make the primary deliverable a `.wav` audio artifact and add teacher-facing links to current official Sphero/littleBits and KORG support pages.

**Why this remains active:**
- Lets operators put a new course into the website quickly when they only have parent/student-facing curriculum docs.
- Keeps the draft honest about its source fidelity while still producing usable lesson routes, importable modules, and helper context.

## Coursepack authoring SDK and registry path

**Current decision:**
- Add `scripts/coursepack_sdk.py` as a single local authoring entry point for:
  - `validate` (one or all coursepacks),
  - `build` (validate + package zip artifact),
  - `package` (artifact build without lint pass).
- Extend `scripts/validate_coursepack.py` checks to include:
  - `ui_level` / `program_profile` value validation,
  - markdown local-link integrity checks within lesson bodies.
- Keep curriculum authoring file-first and Git-native; treat LMS import as a deployment target, not the source of truth.
- Track decentralized distribution evolution in `docs/COURSEPACK_REGISTRY_RFC.md`.

**Why this remains active:**
- Improves survivability and portability by making course content independently buildable outside LMS runtime state.
- Gives schools a practical content-as-code workflow without requiring immediate desktop app investment.
- Creates a direct path to future registry/index distribution while preserving current self-hosted simplicity.

## Redirect target validation

**Current decision:**
- Dynamic redirects in teacher/admin workflows must pass through a same-origin internal redirect guard.
- Redirect targets are constrained to local paths (`/teach`, `/admin`, `/material`, etc.), with scheme/host and `//` checks.
- Legacy teacher routes use the same redirect guard to avoid drift.
- Student artifact publish redirects (`/student/submission/<id>/publish`) use the same local-only redirect pattern:
  - same-origin `url_has_allowed_host_and_scheme` validation,
  - `//`, scheme, and host rejection,
  - constrained student return prefixes (`/student`, `/material`) with safe fallback.

**Why this remains active:**
- Prevents open-redirect regressions when request-derived query values are used to build redirect URLs.
- Keeps redirect behavior explicit and reviewable for CodeQL and manual security review.

## Lesson file path containment

**Current decision:**
- Course manifest and lesson file reads are resolved through a safe path join rooted at `CONTENT_ROOT/courses`.
- Course slugs are validated before path resolution.
- Lesson `file` values from manifest metadata are treated as untrusted and must remain inside the courses root.
- Syllabus backup exports (`hub/services/syllabus_exports.py`) resolve optional `course_slug` selection through `safe_join` + resolved-root containment before reading any directory.

**Why this remains active:**
- Prevents path traversal from malformed or compromised lesson metadata.
- Preserves predictable content loading boundaries for self-hosted operators.

## Untrusted token validation without regex

**Current decision:**
- For short untrusted identifier checks (lesson filenames, YouTube IDs, upload file extensions), prefer bounded character-set scans over regex matching.
- Keep checks explicit: min/max length, required suffix, and allowed-character whitelist.
- Syllabus ingest parsing paths that consume uploaded text metadata now use deterministic token scanners for:
  - session header detection,
  - inline `key: value` metadata extraction,
  - duration/session-count parsing,
  - grade/age range inference.

**Why this remains active:**
- Reduces false-positive and performance risk from regex-on-input security scanners.
- Keeps validation logic auditable and deterministic for maintainers.

## Service-layer extraction scaffold

**Current decision:**
- Keep view modules as request/response adapters while moving denser classroom logic into service modules.
- Student portfolio export logic now runs via `hub/services/export_service.py`.
- Teacher digest/tracker logic now runs via `hub/services/teacher_tracker.py`, with a thin compatibility wrapper in `views/teacher_parts/shared_tracker.py`.
- Helper topic/default parsing now runs via `hub/services/helper_topics.py` and is shared by both lesson rendering and teacher tracker services.
- Lesson tracker service now requires prefetched module materials (`prefetch_related("materials")`) to prevent accidental N+1 query regressions.
- Teacher tracker payload contracts are now explicit via `hub/services/teacher_tracker_types.py` (`TypedDict` shapes for digest rows, lesson rows, and helper signal snapshots).
- Join/upload flows use explicit service facades:
  - `hub/services/join_flow_service.py`
  - `hub/services/submission_service.py`

**Why this remains active:**
- Reduces “big file gravity” in view modules and makes feature work cheaper to test in isolation.
- Establishes stable service boundaries for follow-on refactors (join flow, submission flow, exports, tracker).

## Internal shared package install

**Current decision:**
- `services/common` is now an installable internal package (`classhub-common`) with `pyproject.toml`.
- CI test/migration jobs install it in editable mode (`pip install -e services/common`).
- Service Docker images install `common` during build (instead of relying only on path-copy conventions).

**Why this remains active:**
- Removes reliance on ad-hoc path behavior and makes shared code dependency explicit.
- Keeps local/CI/container environments aligned for shared utility imports.

## Error-response redaction

**Current decision:**
- User-facing lesson metadata errors return a generic 500 message.
- Detailed exception context is logged server-side for maintainers.
- Legacy lesson rendering path follows the same redaction behavior.

**Why this remains active:**
- Prevents exception internals from leaking through HTTP responses.
- Preserves operator debugging signal without exposing stack/metadata details to end users.

## Retention defaults are nonzero

**Current decision:**
- `compose/.env.example.local` and `compose/.env.example.domain` both set:
  - `CLASSHUB_SUBMISSION_RETENTION_DAYS=90`
  - `CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=180`
- Operators can still set either value to `0` as an explicit opt-out.

**Why this remains active:**
- Avoids accidental “indefinite forever” storage when pilots become long-running deployments.
- Keeps privacy defaults aligned with documented retention posture.

## Teacher invite token hardening

**Current decision:**
- Teacher 2FA setup invite links are one-time use.
- Invite links are consumed when first opened and immediately redirected to a tokenless setup URL.
- Default invite TTL is 24 hours (`TEACHER_2FA_INVITE_MAX_AGE_SECONDS=86400`).

**Why this remains active:**
- Reduces bearer-token exposure via browser history, screenshots, and accidental link reuse.
- Preserves simple onboarding while adding practical replay resistance.

## Lint/editor baseline

**Current decision:**
- Repo-level lint baseline is defined in `pyproject.toml` (Ruff).
- Editor defaults are defined in `.editorconfig`.
- CI lint keeps a blocking syntax/undefined gate and also runs a broader Ruff advisory pass (`E,F,I,B,UP`) to track cleanup progress.

**Why this remains active:**
- Keeps code-style drift low across contributors and machines.
- Expands lint coverage without creating sudden merge friction during ratcheting.

## Teacher authoring templates

**Current decision:**
- Provide a script (`scripts/generate_authoring_templates.py`) that outputs both `.md` and `.docx` teacher templates keyed by course slug.
- Keep template sections aligned with `scripts/ingest_syllabus_md.py` parsing rules so teachers can fill in and import without manual reformatting.
- Expose the generator in the teacher landing page (`/teach`) with four required fields: slug, title, sessions, and duration.
- Provide staff-only direct download links for generated files from the same `/teach` card.
- Store UI-generated files under `CLASSHUB_AUTHORING_TEMPLATE_DIR` (default `/uploads/authoring_templates`) to avoid write dependencies on source mounts.

**Why this remains active:**
- Teachers can author in familiar formats (Markdown or Word) while preserving deterministic ingestion.
- Reduces onboarding friction and avoids repeated format mistakes in session-plan documents.

## Syllabus export access and backups

**Current decision:**
- Add a staff-only syllabus export endpoint at `/teach/syllabus-export` with three download modes:
  - catalog CSV of all repo-authored course + lesson metadata,
  - full syllabus backup ZIP across all courses,
  - single-course backup ZIP by course slug.
- Restrict export access to:
  - superusers, and
  - staff with active org memberships in `owner` or `admin` roles.
- Expose export controls in the teacher portal (`/teach`) only when the current staff user has export permission.
- Keep export responses as attachment downloads with `no-store` caching and audit events for traceability.

**Why this remains active:**
- Gives operators a low-friction backup/catalog mechanism without shell access.
- Keeps coursepack export rights aligned with org administration boundaries.

## Teacher UI comfort mode

**Current decision:**
- Teacher pages opt into a dedicated readability mode via `body.teacher-comfort`.
- Comfort mode increases card/table/form spacing, reduces motion emphasis, and removes decorative orb overlays.
- Student-facing pages keep existing visual behavior.

**Why this remains active:**
- Reduces visual fatigue during long grading/planning sessions.
- Improves scanability of dense teacher workflows without a full redesign.

## Teacher portal complexity budget

**Current decision:**
- During stability windows, teacher portal changes must not add new top-level tabs or workflow primitives.
- Preferred change order for `/teach` and `/teach/class/*`:
  1. clarify copy,
  2. reduce simultaneous visible controls,
  3. reorder existing controls for safer defaults,
  4. add or adjust warning language for destructive actions.
- Keep growth pressure visible via existing view/file budget guards; large UI/view expansions require explicit budget justification.
- Syllabus import flow now lives in `views/teacher_parts/content_syllabus_import.py` so `content_home.py` stays within enforced view-size budget and import wiring remains explicit.

**Why this remains active:**
- Keeps the primary staff interface from expanding faster than support/training capacity.
- Reduces regression risk in dense teacher surfaces where many workflows converge.

## Teacher unified class workspace

**Current decision:**
- Keep `/teach/class/<id>` as the primary teacher workspace for day-of-class operations.
- Put the most common teacher actions together at the top of the class page:
  - student access controls,
  - student landing-page edits,
  - session/module creation,
  - fast links to lesson tracker, support board, and outcomes.
- Allow `/teach/create-class` to optionally seed the first session/module and redirect directly into the new class workspace.
- Keep deeper setup panels (`invite links`, `roster`, `full module editor`, `support`, `outcomes`) intact below the workspace instead of creating a second management surface.

**Why this remains active:**
- Reduces click-chasing across `/teach`, `/teach/class/*`, and `/teach/module/*` for the daily teacher loop.
- Improves reliability by making the default path one obvious workspace instead of several partially overlapping entry points.
- Stays within the existing portal-complexity budget by reordering and grouping existing capabilities rather than inventing new workflow primitives.

## Teacher inline lesson images

**Current decision:**
- Let teachers add photos/images directly from the module editor in one step, without making them detour through `/teach/assets` first.
- Store those uploads in the existing `LessonAsset` library and attach them to lessons as asset-backed link materials.
- Render uploaded lesson images inline on both the teacher module page and the student class page.
- Keep image formats constrained to inline-safe raster formats (`png`, `jpg`, `jpeg`, `gif`, `webp`).

**Why this remains active:**
- Reduces authoring friction for visual supports in day-to-day teaching.
- Reuses the existing lesson-asset permission and storage path instead of creating a second media workflow.
- Makes student-facing lesson surfaces feel less text-heavy and less intimidating for younger or more visual learners.

## Helper scope signing

**Current decision:**
- Class Hub now signs helper scope metadata (context/topics/allowed-topics/reference) and sends it as `scope_token`.
- Homework Helper verifies `scope_token` server-side and ignores tamperable client scope fields.
- Student helper requests require a valid scope token.
- Staff can be forced to require scope tokens by setting `HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF=1`.

**Why this remains active:**
- Prevents students from broadening helper scope by editing browser requests.
- Preserves lesson-scoped helper behavior without coupling helper directly to classhub content mounts.

## Helper event ingestion boundary

**Current decision:**
- Homework Helper no longer writes directly to Class Hub tables.
- Helper emits metadata-only chat access events to `POST /internal/events/helper-chat-access` on Class Hub.
- Endpoint is authenticated with `CLASSHUB_INTERNAL_EVENTS_TOKEN` and appends `StudentEvent` rows server-side.

**Why this remains active:**
- Removes raw cross-service SQL writes and keeps ownership of `StudentEvent` writes inside Class Hub.
- Preserves append-only telemetry behavior while reducing coupling between services.

## Edge block for internal endpoints

**Current decision:**
- Caddy blocks public access to `/internal/*` with `404` across all routing templates.
- Internal-path edge blocking is inside ordered `route` blocks so `/internal/*` rejection is evaluated before catch-all proxy handlers.
- Helper internal telemetry continues to target `classhub_web` directly via `CLASSHUB_INTERNAL_EVENTS_URL`, bypassing Caddy.
- Smoke checks assert edge behavior by expecting `404` on `/internal/events/helper-chat-access`.
- Helper internal control/status endpoints also enforce a helper-side caller IP/CIDR gate after bearer auth:
  - default allowlist is loopback + RFC1918/ULA private ranges,
  - optional overrides use `HELPER_INTERNAL_ALLOWED_CIDRS`,
  - proxy header trust stays explicit via `HELPER_INTERNAL_TRUST_PROXY_HEADERS=1`.

**Why this remains active:**
- Shrinks public attack surface and discovery traffic on internal-only endpoints.
- Preserves helper event forwarding reliability without exposing internal routes to browsers.
- Prevents matcher-order drift from leaking internal endpoints to upstream app routing.

## Helper grounding for Piper hardware

**Current decision:**
- Piper course helper references include explicit hardware troubleshooting context (breadboard/jumper/shared-ground/input-path checks), not only Scratch workflow guidance.
- Per-lesson helper references include "Common stuck issues (symptom -> check -> retest)" snippets for deterministic coaching before open-ended hinting.
- Early StoryMode lessons include hardware phrases in `helper_allowed_topics` so strict topic filtering still permits Piper control/wiring questions.
- Helper chat uses a deterministic Piper hardware triage branch for wiring-style questions (clarify mission/step, one targeted check, retest request) before model generation.
- Helper widget includes context-aware quick-action prompts (Piper vs Scratch vs general) that one-tap send structured help requests.
- `scripts/eval_helper.py` supports lightweight rule-based scoring (including Piper hardware cases) so response regressions are easier to spot in CI/local checks.

**Why this remains active:**
- The Piper course includes both Scratch work and physical control wiring; helper grounding must reflect both to be useful in class.
- Narrow topic filtering without hardware terms can incorrectly block or under-serve valid lesson questions.

## Helper lesson citations

**Current decision:**
- Helper now retrieves short lesson excerpts from the signed lesson reference file and includes up to 3 citations in each `/helper/chat` response.
- Prompt policy tells the model to ground responses in those excerpts and cite bracket ids (for example `[L1]`) when relevant.
- Student helper widget renders returned citations under the answer so grounding is visible to the learner.

**Why this remains active:**
- Makes helper output more inspectable and less likely to drift away from lesson intent.
- Gives teachers/students quick traceability from advice back to lesson material.

## Helper local curriculum RAG

**Current decision:**
- Helper supports optional local pgvector retrieval when `HELPER_RAG_ENABLED=1`.
- The vector index is strictly curriculum-only: content is sourced from reference markdown configured by `HELPER_REFERENCE_DIR` and `HELPER_REFERENCE_MAP`.
- Student submissions, student events, and other student-authored data are never embedded or queried in this RAG path.
- Retrieval remains bounded and local via Ollama embeddings (`HELPER_RAG_EMBED_BASE_URL`, `HELPER_RAG_EMBED_MODEL`) and falls back to lexical citations if pgvector/indexing is unavailable.
- Indexing is explicit and operator-driven via `python services/homework_helper/manage.py build_curriculum_rag`.

**Why this remains active:**
- Raises answer quality on long curricula without remote data egress.
- Preserves anti-cheating/privacy posture by preventing cross-student retrieval surfaces.
- Keeps classroom reliability: helper responses continue even when vector retrieval is offline.

## STEM-tech-first helper reference authoring

**Current decision:**
- Course-level and lesson-level helper reference files should front-load STEM technology grounding before broader workflow or policy text.
- Preferred early sections are:
  - `STEM technologies in scope`
  - `Technology tags`
  - `Technology-first troubleshooting`
- Troubleshooting copy should favor `symptom -> check -> retest` phrasing and concrete tool vocabulary (`Scratch`, `breadboard`, `GPIO`, `sprite`, `variable`, etc.).
- Scaffold and reference-generation scripts should emit this structure by default so new content follows the same retrieval-friendly pattern.
- Helper retrieval should apply a bounded STEM-tech rerank when the student question is tool-specific, but it must stay inside the single signed curriculum reference already selected for that request.

**Why this remains active:**
- Improves the current helper immediately because lexical citations and single-reference retrieval depend on explicit overlap with student questions.
- Lets both lexical fallback and local pgvector retrieval prefer technology chunks when results are otherwise close, without turning the helper into a broad search engine.
- Keeps the curriculum-only boundary intact while making tool-specific classroom help easier to retrieve than generic process language.

## Batch helper-reference sync for multi-course deployments

**Current decision:**
- Add `scripts/sync_helper_references.py` as the canonical batch workflow for helper reference setup across multiple course manifests.
- Default behavior is safe for live servers:
  - scan all `services/classhub/content/courses/*/course.yaml` manifests,
  - preserve existing hand-written course-level reference files unless explicitly overwritten,
  - generate lesson reference files only for lessons whose `helper_reference` differs from the course-level `helper_reference`.
- `scripts/generate_lesson_references.py` remains the focused single-course/per-lesson generator beneath this batch wrapper.

**Why this remains active:**
- Reduces operator toil when several courses are already present on a server and helper/RAG setup must be refreshed before deploy.
- Preserves inspectable higher-quality course references without forcing operators to choose between full overwrite and fully manual per-course sync.
- Keeps the repo education-forward by making the batch path deterministic, documented, and based on existing curriculum manifests rather than ad-hoc server-side content copying.

## Helper YAML config layering

**Current decision:**
- Helper now supports optional YAML-backed runtime configuration via `HELPER_CONFIG_FILE`.
- For mapped helper behavior settings, precedence is explicit and stable:
  - explicit env var value,
  - YAML config value,
  - code default/profile fallback.
- Secret-bearing settings remain env-only by design (for example API keys, signing keys, and internal service tokens).
- A baseline template is maintained at `compose/helper.config.example.yaml`.

**Why this remains active:**
- Reduces `.env` sprawl and overlapping setting drift in deployments with many helper knobs.
- Preserves backward compatibility for existing env-only operators.
- Keeps sensitive values out of static config files by policy.

## Production transport hardening

**Current decision:**
- Internal services remain private by default (Postgres/Redis internal network only; Ollama/MinIO host bindings are localhost-only).
- Caddy uses default reverse-proxy forwarded headers for Django client IP/proto awareness.
- Proxy-header trust is mode-aware (`0` in local preset, `1` in domain preset behind Caddy first hop).
- Caddy enforces request-body limits per upstream (`CADDY_CLASSHUB_MAX_BODY`, `CADDY_HELPER_MAX_BODY`).
- Class Hub and Helper CSP defaults are mode-driven via `DJANGO_CSP_MODE` (`relaxed`/`report-only`/`strict`); `DJANGO_CSP_POLICY` and `DJANGO_CSP_REPORT_ONLY_POLICY` can still override/tune headers directly.
- Both Django services reject weak/default secret keys when `DJANGO_DEBUG=0`.
- Deploy flow includes automated `.env` validation via `scripts/validate_env_secrets.sh`.
- Security headers and HTTPS controls are enabled in production through explicit env knobs (`DJANGO_SECURE_*`).
- UI templates use local/system font stacks only (no Google Fonts network calls).
- CI now guards against non-localhost published ports for internal services (`scripts/check_compose_port_exposure.py`).
- CI now includes secret scanning and Python dependency vulnerability scanning (`.github/workflows/security.yml`).
- CI stack-smoke now sets a non-placeholder `CLASSHUB_INTERNAL_EVENTS_TOKEN` before running `scripts/system_doctor.sh`.

**Why this remains active:**
- Reduces accidental public exposure of internal services.
- Improves trust in proxy-aware rate limiting and secure-cookie behavior.
- Drops oversized requests at the edge before they reach Django workers.
- Prevents unsafe production boots with placeholder secrets.
- Removes third-party font calls from student/teacher/admin page loads.
- Makes CSP rollout incremental without breaking inline-heavy templates.
- Prevents accidental internal service exposure regressions during future compose edits.
- Keeps proxy trust assumptions explicit and reviewable in deploy configuration.

## Content parse caching

**Current decision:**
- Course manifests and lesson markdown parsing are cached in-process using `(path, mtime)` keys.
- Cache entries invalidate automatically when file modification times change.
- Returned manifest/front-matter payloads are deep-copied on read to prevent accidental mutation leaks.

**Why this remains active:**
- Reduces repeated disk + YAML/markdown parsing overhead on hot lesson/class pages.
- Keeps behavior deterministic for live content edits without requiring manual cache flushes.

## Teacher lesson-level helper tuning

**Current decision:**
- Reuse `LessonRelease` as the per-class/per-lesson storage point for teacher helper-scope overrides.
- Teachers can set optional overrides for helper context, focus topics, allowed-topic gate, and reference key directly from each lesson row in `/teach/class/<id>`.
- Class Hub applies these overrides when issuing signed helper scope tokens for students in that class.

**Why this remains active:**
- Keeps helper tuning close to lesson release controls where teachers already manage pacing.
- Avoids introducing a second override model/table for the same class+lesson keyspace.

## Collapsed teacher course controls by default

**Current decision:**
- On the teacher class dashboard, `Roster`, `Lesson Tracker`, and `Module Editor` are collapsed by default using explicit section toggles.
- Content is shown only when the teacher opens a section.

**Why this remains active:**
- Reduces visual load in day-to-day teaching workflows while preserving full control paths.
- Makes the class dashboard easier to scan during live instruction.

## Progressive docs layering for non-developers

**Current decision:**
- Introduce a dedicated non-developer entry page: [NON_DEVELOPER_GUIDE.md](NON_DEVELOPER_GUIDE.md).
- Keep [START_HERE.md](START_HERE.md) short and role-based with minimal links per audience.
- Keep [index.md](index.md) as a concise docs index (not a wall of policy text).
- Keep deep ops docs ([RUNBOOK.md](RUNBOOK.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md)) in quick-action-first format with command blocks and symptom indexing.

**Why this remains active:**
- Most readers need task guidance, not full architecture context.
- Progressive disclosure lowers cognitive load for teachers and staff while preserving deep technical docs for operators/developers.

## Teacher daily digest and closeout workflow

**Current decision:**
- `/teach` includes a per-class "since yesterday" digest (new students, uploads, helper usage, first-upload gaps, latest submission timestamp).
- `/teach` includes collapsed closeout actions per class: lock class, export today's submissions zip, print join card.
- Closeout export is local-day scoped (deployment timezone aware), with audit events for lock/export actions.

**Why this remains active:**
- Gives teachers a fast day-over-day signal without opening each class.
- Standardizes end-of-class operations into one predictable flow.

## Student portfolio export

**Current decision:**
- Students can download a personal portfolio ZIP from `/student/portfolio-export`.
- The ZIP contains:
  - `index.html` (offline summary with timestamps, lesson/module labels, notes),
  - `files/...` entries for that student's own submissions only.
- Export filenames are sanitized and scoped to the current authenticated student session.

**Why this remains active:**
- Gives students a take-home artifact without requiring full accounts.
- Supports portability and parent/mentor sharing while preserving class privacy boundaries.

## Checklist, reflection, and rubric material types

**Current decision:**
- Extend `Material.type` with:
  - `checklist`: line-based self-report checklist
  - `reflection`: private journal prompt + student response
  - `rubric`: criteria ratings + optional written feedback
- Extend with `gallery`: upload material where sharing to classmates is explicit opt-in per submission.
- Student responses are stored in `StudentMaterialResponse` keyed by student+material.
- Checklist/reflection/rubric response details are excluded from CSV outcome/detail exports by default.
- Milestone-only outcome events are emitted (`milestone_earned`) without storing reflection body/checklist text in event payloads.
- Gallery downloads for classmates are allowed only when `is_gallery_shared=True` and class membership matches.

**Why this remains active:**
- Adds low-friction non-grade evidence of engagement for paid cohorts and funder reporting.
- Preserves privacy-forward defaults by keeping detailed student writing out of event streams and exports.

## Outcome events and certificate rollups

**Current decision:**
- Track learner progress in append-only `StudentOutcomeEvent` rows with event types:
  - `session_completed`
  - `artifact_submitted`
  - `milestone_earned`
- Successful upload submissions emit outcome events:
  - one `artifact_submitted` per successful submission
  - one `session_completed` per student+module (first artifact in that module)
- Manual/sessionless workflows can emit `session_completed` from teacher UI:
  - `POST /teach/class/<id>/mark-session-completed` records one `session_completed` per student+module if absent.
- Milestone outcome triggers are material-specific:
  - checklist fully checked (`checklist_completed`)
  - first non-empty reflection save (`reflection_submitted`)
  - first rubric save with score/feedback (`rubric_submitted`)
- Teachers can export `/teach/class/<id>/export-outcomes-csv` for class/student rollups.
- Teachers can review all students in `/teach/class/<id>/certificate-eligibility`.
- Certificate issuance uses signed class records (`CertificateIssuance`):
  - one record per class+student (re-issuable in place)
  - captures counts/threshold snapshot at issue time
  - downloadable as signed `.pdf` or `.txt` via `/teach/class/<id>/certificate/<student_id>/download.pdf` and `/teach/class/<id>/certificate/<student_id>/download`
- Certificate eligibility is threshold-based:
  - `CLASSHUB_CERTIFICATE_MIN_SESSIONS` (default 8)
  - `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS` (default 6)

**Why this remains active:**
- Produces funder/parent-facing outcome summaries without adding grades or surveillance patterns.
- Keeps privacy boundary intact by exporting only aggregate counts + display names (no raw details payloads).

## Outcomes and certificate semantics contract

**Current decision:**
- Certificate eligibility is an event-threshold contract, not a competency-grade contract.
- Event semantics are:
  - `artifact_submitted`: one event per successful submission
  - `session_completed`: one event per student+module from first artifact, or teacher manual mark for offline completion
  - `milestone_earned`: material-triggered engagement signal (checklist/reflection/rubric)
- Certificate issuance records are signed snapshots of threshold counts at issue time.
- Reporting/export language must not claim hidden analytics or transcript-based evidence.
- Threshold settings (`CLASSHUB_CERTIFICATE_MIN_SESSIONS`, `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`) should be treated as cycle-level policy and changed intentionally between reporting windows, not ad hoc mid-cycle.

**Why this remains active:**
- Keeps instructors, operations, and fundraising aligned on what certificate/output data means.
- Reduces reporting drift where technically valid exports are interpreted inconsistently.

## Automated retention maintenance

**Current decision:**
- Use `scripts/retention_maintenance.sh` as the single scheduled task entrypoint for:
  - `prune_submissions`
  - `prune_student_events` (with optional CSV export-before-delete)
  - prune helper reset JSON exports (`RETENTION_HELPER_EXPORT_DAYS`, default 30)
  - `scavenge_orphan_uploads` (report/delete/off modes)
- Optional webhook notifications report failures (and optional success) for unattended runs.
- Provide reference systemd units in `ops/systemd/` for daily execution.
- Retention command audit stamps are surfaced in `/teach/data-lifespan` as a quick health indicator.

**Why this remains active:**
- Moves retention from manual cleanup to reliable routine operations.
- Surfaces cleanup failures early and keeps uploads/event tables bounded over time.

## Unified backup + restore rehearsal workflow

**Current decision:**
- Use `scripts/backup_restore_rehearsal.sh` as the single operator entrypoint for backup+restore drills.
- The rehearsal script:
  - runs Postgres/uploads/MinIO backup scripts,
  - starts the compose Postgres service and waits for a healthy state before running `pg_dump`,
  - restores Postgres into a temporary database,
  - extracts uploads/MinIO archives into a temporary workspace,
  - runs ClassHub/Helper `migrate` + `check` against the restored DB.
- `scripts/backup_postgres.sh` uses `docker compose exec` against the configured Postgres service instead of a hard-coded container name so CI, dev, and production compose modes share the same service addressing path.
- Legacy per-surface scripts remain available for ad-hoc usage:
  - `scripts/backup_postgres.sh`
  - `scripts/backup_uploads.sh`
  - `scripts/backup_minio.sh`

**Why this remains active:**
- Turns disaster recovery from documentation-only into a repeatable operator ritual.
- Verifies restore viability before an incident, not during one.
- Reduces drift between backup artifacts and practical restore commands.

## Defensive hardening pass (downloads, return codes, rate limits)

**Current decision:**
- Submission downloads now force safer browser behavior:
  - sanitized attachment filename
  - `Content-Type: application/octet-stream`
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy: default-src 'none'; sandbox`
  - `Referrer-Policy: no-referrer`
- Return codes are masked by default in student and teacher pages, with explicit `Show/Hide` and `Copy` controls.
- Return-code pages and submission downloads set `Cache-Control: private, no-store` to reduce shared-device/back-button exposure.
- `join_class` responses now emit `Cache-Control: no-store` (+ `Pragma: no-cache`) because they carry student return codes in JSON.
- `student_portfolio_export` now emits `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff`.
- Student event payloads are reduced to low-sensitivity metadata (for example, join mode and file extension), avoiding display-name/class-code duplication.
- Internal helper chat access events now enforce a strict details allowlist before persistence, silently dropping unknown keys.
- Helper -> ClassHub internal event forwarding now uses an ultra-short timeout by default (0.35s), stays best-effort, and logs only request-id/error metadata.
- Cache-backed limiter helpers now tolerate corrupt cache state without raising request-path errors (fail-open with warning logs including request id).
- Release archives now run a reusable artifact lint check (`scripts/lint_release_artifact.py`) and exclude local/runtime secrets and state (`compose/.env` + local backup variants, `data/`, `.deploy/`).
- `safe_filename` now lives in a dedicated filename service module (`hub/services/filenames.py`) and is imported where needed.
- Student/teacher return-code reveal is no longer sourced from DOM attributes; `/student` and `/teach/class/<id>` now fetch via authenticated endpoints (`GET /student/return-code`, `GET /teach/class/<id>/student/<id>/return-code`) with `private, no-store` caching.

**Why this remains active:**
- Reduces content-sniffing and filename abuse risk on download endpoints.
- Limits shoulder-surfing exposure for return codes during classroom use.
- Preserves classroom availability during transient cache issues.
- Keeps release bundles safer and reproducible across local and CI workflows.

## Public-domain hardening pass (CSP enforcement, proxy armor, degradation modes)

**Current decision:**
- Security header and cache ownership is documented in one place: [SECURITY_BASELINE.md](SECURITY_BASELINE.md).
- Class Hub and Helper now support CSP rollout modes via `DJANGO_CSP_MODE`, with optional per-header overrides via `DJANGO_CSP_POLICY` and `DJANGO_CSP_REPORT_ONLY_POLICY`.
- Security headers are attached consistently by middleware (`Permissions-Policy`, `Referrer-Policy`, `X-Frame-Options`, plus CSP headers).
- Caddy templates now support optional teacher/admin edge armor:
  - IP allowlist for `/admin*` and `/teach*` via `CADDY_STAFF_IP_ALLOWLIST_V4`/`CADDY_STAFF_IP_ALLOWLIST_V6`
  - optional extra basic-auth gate for `/admin*` via `CADDY_ADMIN_BASIC_AUTH_*`
  - fail-closed guard when admin basic auth is enabled with shipped/default credentials
  - explicit acknowledgement required to keep open staff-route allowlists in domain mode: `CADDY_ALLOW_PUBLIC_STAFF_ROUTES=1`
  - optional upstream app health exposure toggle: `CADDY_EXPOSE_UPSTREAM_HEALTHZ`
- Added a single operator-controlled degradation switch: `CLASSHUB_SITE_MODE` with modes:
  - `normal`
  - `read-only`
  - `join-only`
  - `maintenance`
- Helper chat now respects degraded site modes (`join-only`, `maintenance`) and returns explicit machine-readable `site_mode_restricted` responses.

**Why this remains active:**
- Moves CSP from passive observation toward active browser-enforced protection.
- Lowers clickjacking/browser-capability exposure with stable default headers.
- Adds defense-in-depth for public `/admin` discovery pressure.
- Gives operators a predictable, low-chaos incident posture without code edits.

## Privacy control-surface pass (consent microcopy + self-service deletion)

**Current decision:**
- Add plain-language privacy microcopy directly on join, upload, and helper UI surfaces:
  - what is stored,
  - where it is stored,
  - retention framing,
  - where to delete now.
- Add student self-service control surface at `/student/my-data` with:
  - view submissions,
  - portfolio export,
  - delete submissions now,
  - end session on this device.
- Add teacher per-student data deletion control from class roster, with explicit confirmation and session invalidation.
- Add explicit helper backend visibility in UI (`Local model (Ollama)` vs `Remote model (OpenAI)` badge).
- Make remote helper mode (`openai`) require explicit operator acknowledgment (`HELPER_REMOTE_MODE_ACKNOWLEDGED=1`) before chat is allowed.
- Add project-level [PRIVACY-ADDENDUM.md](PRIVACY-ADDENDUM.md) as field-level source of truth for lifecycle and deletion paths.

**Why this remains active:**
- Makes the privacy bargain visible in-product, not only in repository docs.
- Keeps deletion a control surface instead of an operator ticket.
- Prevents accidental/silent enablement of remote helper mode.
- Gives operators and reviewers a concrete, auditable privacy checklist.

## Helper timeout budget guardrail (prevent `/helper/chat` worker timeouts)

**Current decision:**
- Make helper Gunicorn runtime timeout configurable:
  - `HELPER_GUNICORN_TIMEOUT_SECONDS` (default `180`)
  - `HELPER_GUNICORN_WORKERS` (default `2`)
- Add deploy-time env validation math in `scripts/validate_env_secrets.sh` for Ollama mode:
  - compute worst-case helper request budget as:
    - `HELPER_QUEUE_MAX_WAIT_SECONDS`
    - `+ HELPER_BACKEND_MAX_ATTEMPTS * OLLAMA_TIMEOUT_SECONDS`
    - `+ exponential HELPER_BACKOFF_SECONDS`
    - `+ safety margin`
  - fail fast when `HELPER_GUNICORN_TIMEOUT_SECONDS` is below this budget.

**Why this remains active:**
- Prevents intermittent `/helper/chat` 500s caused by Gunicorn worker timeout while waiting on backend model responses.
- Converts a runtime failure into an early deploy-time config check.

## Caddy basic-auth compatibility with teacher OTP login

**Current decision:**
- Keep the optional Caddy basic-auth gate for `/admin*`, but explicitly bypass `/admin/login*`.
- Apply this matcher behavior consistently in `compose/Caddyfile.local`, `compose/Caddyfile.domain`, `compose/Caddyfile.domain.assets`, and `compose/Caddyfile`.
- Document that `/admin/login*` is Django-owned so staff can complete username/password + OTP before entering `/teach`.

**Why this remains active:**
- Prevents browser-native auth popups from blocking teacher login and OTP setup.
- Preserves defense-in-depth on the rest of the admin surface when edge basic auth is enabled.

## Smoke guardrail for admin login edge-auth regressions

**Current decision:**
- `scripts/smoke_check.sh` now explicitly checks `GET /admin/login/` before teacher/session checks.
- Smoke fails when the route responds with `401` and `WWW-Authenticate: Basic`, with a targeted error directing operators to exempt `/admin/login*` from edge basic-auth.

**Why this remains active:**
- Prevents golden/strict smoke from passing when Caddy is still showing browser auth popups and blocking Django OTP login.

## Teacher-side student identity merge for duplicate rejoins

**Current decision:**
- Add a teacher roster action at `POST /teach/class/<id>/merge-students`.
- Teachers choose a source student and destination student in the same class, confirm merge, then:
  - move `Submission` rows from source -> destination,
  - move `StudentEvent` rows from source -> destination,
  - delete the source student identity.
- Keep destination identity (including return code) as the canonical record after merge.
- Record merge actions in audit logs as `student.merge` with moved row counts.

**Why this remains active:**
- Students who rejoin with class code (without return code) can create duplicate roster entries in legitimate classroom usage.
- Gives teachers a low-friction correction path without manual database edits or admin-only intervention.

## Name-match fallback on student join (reduce duplicate roster growth)

**Current decision:**
- For `POST /join` without `return_code`, rejoin resolution now uses:
  1) signed same-device hint, then
  2) class + display-name match (`display_name__iexact`) selecting the oldest matching identity.
- If a name-match identity is reused, `rejoined=true` is returned and event details record `join_mode=name_match`.

**Why this remains active:**
- Prevents repeated same-name joins (for example smoke/rehearsal cycles or classroom cookie churn) from creating unbounded duplicate student rows.
- Keeps behavior deterministic when duplicate-name rows already exist.

## Optional short-lived teacher panel cache

**Current decision:**
- Add an opt-in cache window for expensive teacher tracker panels:
  - class digest rows (`/teach`)
  - lesson tracker rows (`/teach/lessons`, `/teach/class/<id>`)
  - helper signal snapshot (`/teach/class/<id>`)
- New setting: `CLASSHUB_TEACHER_PANEL_CACHE_TTL_SECONDS` (default `0`, disabled).
- Cache keys are panel-scoped and include classroom/session context so classes do not share panel snapshots.
- Cache storage uses primitive payloads (`classroom_id`, `module_id`, counters, timestamps, URLs) and rehydrates model references per request, avoiding ORM-object pickling in shared caches.
- Cache behavior fails open: if cache get/set errors occur, panel generation continues uncached.

**Why this remains active:**
- During class, teachers often refresh the same dashboard repeatedly in short bursts.
- A 15–30 second cache window can cut repeated DB/aggregation load without changing long-term data behavior.
- Keeping default `0` preserves strict real-time behavior unless an operator explicitly opts in.

## View wildcard import guardrail

**Current decision:**
- CI lint runs `scripts/check_no_new_wildcard_view_imports.py`.
- The guard blocks any new `from ... import *` under `services/classhub/hub/views/**`.
- A temporary path-based baseline allows only known legacy wildcard imports while those modules are being incrementally split/refactored.

**Why this remains active:**
- Prevents wildcard imports from spreading back into new files after the recent explicit-import cleanup.
- Keeps cleanup incremental without breaking CI on legacy compatibility surfaces that are still in-flight.

## Submission query composite indexes

**Current decision:**
- Add composite indexes on `Submission` for:
  - `("material", "uploaded_at")`
  - `("student", "uploaded_at")`
  - `("material", "student")`
- Add composite index on `StudentIdentity` for:
  - `("classroom", "created_at")`
- Add composite index on `StudentEvent` for:
  - `("classroom", "event_type", "created_at")`
- Keep existing behavior and query shapes unchanged; this is a storage-level performance optimization only.

**Why this remains active:**
- Teacher tracker and export paths frequently query latest uploads and distinct submitters by material/student.
- Composite keys reduce row-scan and sort pressure as classroom data volume grows.

## Retention-only StudentEvent deletes, paid-cohort invite links, and class summary CSV

**Current decision:**
- Enforce StudentEvent delete invariants at both model and queryset layers:
  - `StudentEvent.delete()` is blocked unless a retention-only context is active.
  - `StudentEventQuerySet.delete()` is also blocked by default, closing the bulk-delete gap.
  - Retention command path (`manage.py prune_student_events`) now enables a scoped privileged delete context explicitly.
- Teacher roster "delete student data" no longer hard-deletes StudentEvent rows; events are retained and detached from deleted student identities via FK `SET_NULL`.
- Add teacher-generated `ClassInviteLink` records for no-login student onboarding:
  - invite URL `/invite/<token>` bridges into join flow,
  - optional expiry (`expires_at`),
  - optional seat cap (`max_uses`, consumed only on new identity creation),
  - disable action in teacher UI.
- Add class-level CSV export (`/teach/class/<id>/export-summary-csv`) with row types:
  - `class_summary` (joins/rejoins, active students, submissions, helper access totals),
  - `student_summary` (display_name, joins, submissions, helper access counts, first/last seen),
  - `lesson_summary` (course/lesson/module submission coverage).
- Add dedicated helper scope signing secret support via `HELPER_SCOPE_SIGNING_KEY`:
  - shared by classhub + helper service via compose `.env`,
  - defaults to `DJANGO_SECRET_KEY` for backward compatibility,
  - documented as a separate key in env examples and deploy validation.

**Why this remains active:**
- Preserves append-only telemetry guarantees outside explicit retention workflows.
- Supports paid/cohort onboarding flows without introducing student logins.
- Gives staff a low-friction operational export with minimal PII and no helper prompt content.
- Reduces blast radius by decoupling helper scope token signing from Django’s primary secret.

## Learner UI density by program/course level

**Current decision:**
- Keep a single product surface, but vary learner-facing UI density via three modes:
  - `compact` for elementary cohorts,
  - `standard` for secondary cohorts,
  - `expanded` for advanced cohorts.
- Source of truth order:
  1) lesson metadata (`ui_level` / `learner_level`),
  2) course manifest metadata (`ui_level` / `learner_level` / `program_profile`),
  3) global env default (`CLASSHUB_PROGRAM_PROFILE`).
- No database schema changes. Resolution is computed at render time from existing settings/content metadata.
- This mode only adjusts copy density and layout complexity in learner pages (`/`, `/student`, `/course/*`).
- `expanded` is treated as studio mode (not just "more text"):
  - keep accountability handles visible (rubric links, portfolio export, gallery-share controls),
  - include per-lesson design-log/changelog/release-note prompts,
  - show challenge branches clearly when lesson `extend` options are present.

**Why this remains active:**
- Supports mixed-age delivery without forking the platform or duplicating templates.
- Keeps operations boring: one deploy, one data model, one permission system.
- Preserves non-negotiables (privacy posture, no prompt archiving, no surveillance analytics) while improving age-appropriate usability.

## Student class landing page + weekly lesson highlight

**Current decision:**
- Keep `/student` as the single student home entry point, but add a landing section that:
  - shows teacher-managed class intro content (title, message, optional hero image),
  - highlights one lesson either:
    - automatically from existing release schedule (default), or
    - from a teacher-selected default lesson module pinned in class settings,
  - keeps full course lesson links available from the same page.
- Landing content is stored on `Class` (`student_landing_title`, `student_landing_message`, `student_landing_hero_url`, `student_landing_default_module`) and managed in the existing teacher class dashboard.
- Hero URL validation allows only:
  - same-origin paths starting with `/` (for local assets), or
  - absolute `http/https` URLs.
- Teacher default-lesson selection is validated to class-scoped modules that contain a valid `/course/<course>/<lesson>` link material.

**Why this remains active:**
- Gives young learners a clear “start here” focus without removing access to the rest of the course.
- Keeps release-driven behavior as the default while allowing teacher in-the-moment guidance for younger cohorts that need a single obvious next click.
- Keeps operations centralized: teachers edit landing content in the same class dashboard they already use for invites, roster, and releases.

## Script stack hardening for local + CI parity

**Current decision:**
- Keep script behavior stable, but remove Bash 4-only lowercase expansion from `scripts/validate_env_secrets.sh` so it runs on macOS default Bash 3.2 and Linux.
- Add explicit `--help` handling to `scripts/make_release_zip.sh` and validate argument count/path parsing before file operations.
- Standardize day-1 bootstrap default project root to `/srv/lms/app` to match runbook/systemd conventions.

**Why this remains active:**
- Local operators and developers run deploy/ops scripts from macOS as well as Linux; env validation must be portable.
- Script UX should fail clearly on bad arguments instead of treating flags as filesystem paths.
- Keeping one canonical server path reduces drift between bootstrap docs, runbooks, and systemd units.

## Secondary track pilot coursepack (Grade 9, 6 sessions)

**Current decision:**
- Add a new repo-authored coursepack at `services/classhub/content/courses/scratch_intro_games_code_grade9_6_session/`.
- Set manifest metadata to `program_profile: secondary` and `ui_level: secondary` for density testing beyond elementary pacing.
- Keep assessment completion-forward, with short reflections and vocabulary checks.
- Add dedicated helper reference `grade9_scratch_games` for course-aligned tutoring context.

**Why this remains active:**
- Enables testing with a second pacing profile while preserving the same platform primitives (class code login, module import, helper boundary).
- Supports mixed classroom cohorts without creating a separate product mode.

## Teacher syllabus source import (.md/.docx/.zip)

**Current decision:**
- Add a staff endpoint at `/teach/import-syllabus-source` to ingest curriculum source files into coursepacks.
- Support three source types:
  - single `.md` session plan,
  - single `.docx` session plan,
  - `.zip` bundles containing multiple `.md`/`.docx` files (including `sessions/` style archives).
- Move parsing/writing logic into `hub/services/syllabus_ingest.py` so the teacher UI and script stack can share one ingest contract over time.
- Keep ingestion conservative:
  - explicit slug validation (`[a-z0-9_-]+`),
  - parser modes (`auto` / `template` / `verbose`),
  - bounded zip parsing (file count/size guardrails),
  - normalized zip member paths (no traversal/absolute/null-byte segments),
  - `safe_join`-backed child path construction for course/temp/lesson writes,
  - temporary write paths independent of user-provided slug text,
  - overwrite only when explicitly requested.
- Persist imported output in standard coursepack layout under `CONTENT_ROOT/courses/<slug>/` with generated `course.yaml` + `lessons/*.md`.

**Why this remains active:**
- Teachers and operators can onboard externally authored curricula without manual file surgery in the repo tree.
- ZIP-first support matches real inbound package formats (multi-file session folders, course descriptions, templates).
- Centralized ingest rules reduce drift between authoring scripts and portal behavior while preserving inspectable disk artifacts.

## Low-surveillance feedback mechanics (micro-checks + facilitator support board)

**Current decision:**
- Add three in-session micro-check signals on `/student`:
  - `I can do this`
  - `I'm stuck`
  - `I taught someone`
- Persist these as append-only `StudentEvent` records with classroom/student linkage and timestamps.
- Add optional peer-feedback sentence starters in reflection/rubric forms:
  - default starter set resolved by active language (`en` / `es`),
  - optional per-course overrides via `course.yaml` key `peer_feedback_sentence_starters`.
- Add a facilitator-first support board on `/teach/class/<id>` that prioritizes:
  - unresolved stuck signals,
  - recent upload error events,
  - idle-time context (non-judgmental interpretation).
- Keep updates lightweight:
  - no continuous polling loop,
  - manual refresh path on the dashboard.

**Why this remains active:**
- Preserves privacy-forward operations while still giving facilitators actionable support cues.
- Favors “help requested/help offered” signals over ranking, points, or performance gamification.
- Keeps implementation operationally boring by reusing existing event streams and teacher dashboard surfaces.

## Gallery publish state + deletion-request queue clarity

**Current decision:**
- Enforce a strict two-step gallery workflow:
  - student intent: `is_published=True`,
  - teacher moderation: `is_gallery_shared=True`.
- Student upload opt-in now records publish intent only; it no longer auto-sets teacher approval.
- Student unpublish always clears `is_gallery_shared`, so republish returns to pending-approval state.
- Student self-delete copy is explicit:
  - immediate delete removes submissions + learning responses + student-linked class events/outcomes.
- When `CLASSHUB_STUDENT_SELF_DELETE_MODE=request`, teacher dashboard now includes a deletion-request queue with `Mark addressed`, logged as a resolution event.

**Why this remains active:**
- Keeps trust boundaries clear where student visibility and teacher moderation intersect.
- Prevents stale approval flags from bypassing moderation on republish.
- Makes deletion behavior honest and operationally actionable for both students and staff.

## Translation pass for student upload/trust cues + JS status copy

**Current decision:**
- Wrap new student-facing upload labels and privacy copy in translation tags:
  - `Station (optional)`,
  - `Process note (optional)`,
  - upload-page privacy/retention strings.
- Pass student interaction status strings into `student_class.js` via `data-i18n-*` attributes (no inline JS, no framework dependency), including:
  - show/hide return code,
  - copy success/failure,
  - sentence starter insertion notices.
- Improve built-in Spanish peer-feedback starters to natural forms:
  - `Noté que...`
  - `Me pregunto...`
  - `¿Qué pasaría si...?`

**Why this remains active:**
- Keeps student trust/safety instructions understandable in the same language as the rest of the UI.
- Avoids hardcoded English in dynamic JS status paths without adding heavy i18n tooling.

## Join flow and teacher submissions i18n consistency

**Current decision:**
- Move `student_join.js` user-visible text to template-provided `data-i18n-*` values so all error/status copy remains translatable without inline JS.
- Localize student gallery publish notices in `student_artifacts.py` (`Removed from gallery`, `Published...`, gallery-disabled notice).
- Wrap teacher submissions page copy (`teach_material_submissions.html`) in translation tags and set `lang="{{ LANGUAGE_CODE }}"` for consistency.

**Why this remains active:**
- Closes remaining English-only islands in critical student join and teacher review flows.
- Keeps static JS lightweight while preserving multilingual behavior under CSP constraints.

## Upload quota and portfolio status performance guardrails

**Current decision:**
- Replace per-upload full class directory scans with a short-lived cache-backed quota byte counter:
  - first read scans `MEDIA_ROOT/submissions/class_<id>`,
  - hot path reads cached bytes and bumps on successful upload,
  - destructive class/student submission flows invalidate cache.
- Make portfolio file existence verification opt-in via `CLASSHUB_PORTFOLIO_VERIFY_FILE_EXISTENCE` (default `False`):
  - default status path avoids per-row `storage.exists()` calls,
  - deployments needing strict remote tombstone verification can enable explicit checks.

**Why this remains active:**
- Keeps upload latency stable as class artifact counts grow.
- Reduces remote storage round-trips on portfolio render while preserving an explicit strict mode.

## CI inventory guard: anchor flows over raw test counts

**Current decision:**
- Refactor `scripts/check_test_inventory_coverage.py` to enforce:
  - required test files,
  - anchor test names per subsystem,
  - suite/endpoint tokens for critical flows,
  - required smoke script presence.
- Remove raw per-file and per-directory minimum test-count thresholds from the guard.

**Why this remains active:**
- Keeps CI strict about coverage of critical behaviors while reducing false failures during healthy test refactors.
- Makes guard failures easier to interpret: missing flow coverage rather than arbitrary count drift.

## Phase 1 RBAC capability evaluator (backward-compatible)

**Current decision:**
- Add a capability-based access evaluator in `hub/services/org_access.py` with explicit action keys:
  - `class.view`, `class.manage`, `class.create`,
  - `roster.manage`,
  - `submission.view`, `submission.delete`,
  - `policy.manage`,
  - `syllabus.export`.
- Keep current `OrganizationMembership.role` as the source of truth in Phase 1; map roles to capability sets:
  - `owner`/`admin`: full capability set,
  - `teacher`: management capabilities without syllabus export,
  - `viewer`: read-only class/submission visibility.
- Preserve legacy fallback behavior:
  - staff without memberships keep class view/manage/create only when `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`,
  - syllabus export remains membership-gated.
- Route legacy helper APIs through the evaluator (`staff_can_manage_classroom`, `staff_can_create_classes`, `staff_can_export_syllabi`) so existing call sites stay stable.
- Support module scope in the evaluator contract (`module_id`) with strict class-module validation (future module-range grants build on this seam).
- Add a first scoped-grant persistence model `ClassStaffModuleScopeGrant`:
  - stores per-class, per-user, per-capability module order ranges,
  - currently scoped to `submission.view` and `submission.delete`.
- Keep scoped-grant enforcement feature-flagged and disabled by default:
  - `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=0` -> evaluator behaves like role-only checks,
  - `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1` -> module-scoped submission checks enforce active range grants when present.

**Why this remains active:**
- Enables incremental migration from coarse roles to capability checks without breaking current operations.
- Makes permission reasoning explicit and testable ahead of custom role/scoped-grant tables.
- Reduces risk of accidental privilege expansion by centralizing allow/deny decisions in one service path.

## RBAC endpoint hardening: policy/manage splits and drift guards

**Current decision:**
- Tighten teacher endpoint guards to capability-specific checks instead of broad classroom access:
  - policy mutation paths use `staff_can_manage_policy`,
  - roster-destructive paths use `staff_can_manage_roster`,
  - class outcomes/submission exports require `staff_can_view_submissions`,
  - certificate downloads require roster-management capability.
- Align API teacher mutation routes (`toggle_lock`, `rotate_code`, `set_enrollment_mode`) with the same policy capability contract.
- Expand CI RBAC endpoint contracts to assert both required guards and forbidden legacy guard usage for sensitive paths.

**Why this remains active:**
- Enforces least privilege on high-impact endpoints while preserving existing role mappings.
- Prevents silent permission drift by failing CI when endpoint guards regress.

## Scoped-grant deny precedence, simulation, and policy-audit trail

**Current decision:**
- Extend `ClassStaffModuleScopeGrant` with an explicit `effect` (`allow` / `deny`) to support overlapping range policy semantics.
- Enforce scoped module capability precedence as:
  - explicit deny > explicit allow > role fallback.
- Add RBAC simulation surfaces for operators:
  - API: `POST /api/v1/teacher/rbac/simulate` (staff+OTP with org-level export capability),
  - CLI: `simulate_rbac_access` management command.
- Emit audit events for scoped grant policy changes in admin:
  - `rbac.scope_grant.create`,
  - `rbac.scope_grant.update`,
  - `rbac.scope_grant.delete`.

**Why this remains active:**
- Makes conflict resolution explicit and deterministic for district-style boundary policies.
- Improves supportability by enabling machine-readable "why denied" simulation without mutating state.
- Preserves accountability for policy edits by adding immutable grant-change audit records.

## Org role templates + bulk RBAC simulation matrix

**Current decision:**
- Add org-level role capability templates (`OrganizationRoleCapability`) so operators can define per-org capability sets for each membership role.
- Keep a static default role->capability map as fallback; when an org template exists for a role, use that org template as the effective role capability set.
- Add a read-only bulk simulation matrix in teacher RBAC tools to evaluate one capability/class scope across staff:
  - `GET /teach?rbac_tools=1&rbac_bulk_class_id=<id>&rbac_bulk_capability=<capability>[&rbac_bulk_module_id=<id>]`
  - include allow/deny + reason + resolved role metadata per staff row.
- Limit matrix rows to 250 and constrain rows to staff inside the selected class org boundary (plus superusers).
- Extend endpoint-level RBAC tests so org template overrides are validated across both `/teach/*` and `/api/v1/teacher/*` policy endpoints.

**Why this remains active:**
- Enables district-style policy customization without replacing existing membership roles.
- Improves operator debugging by surfacing capability outcomes for multiple staff accounts in one view.
- Reduces policy drift risk by proving runtime parity between teacher and API policy endpoints under customized role templates.

## Scoped-grant expansion + RBAC audit ops feed

**Current decision:**
- Expand `ClassStaffModuleScopeGrant` capability choices to include:
  - `roster.manage`
  - `policy.manage`
- Keep submission capabilities module-range based; for class-wide policy/roster controls use range `0-0` sentinel.
- Keep deny precedence stable across all scoped capabilities:
  - explicit deny > explicit allow > role fallback.
- Extend teacher RBAC tools with an audit operations panel:
  - filter by action family, optional class, and row limit,
  - include RBAC + org policy actions (`rbac.*`, `organization.role_capability.*`, `organization.membership.*`),
  - scope feed to accessible class/org boundaries.

**Why this remains active:**
- Closes the gap between role templates and per-class operational overrides for high-impact policy/roster actions.
- Gives operators a fast, in-product audit surface for RBAC changes and simulation actions without requiring admin-site querying.
- Preserves least-privilege and traceability while avoiding a separate parallel audit system.

## RBAC policy-as-code import/export

**Current decision:**
- Add RBAC policy bundle export endpoint for operators:
  - `GET /teach/rbac/policy/export`
- Add RBAC policy bundle import endpoint for operators:
  - `POST /teach/rbac/policy/import`
- Use schema `classhub.rbac_policy.v1` with two sections:
  - organization role-capability templates
  - class scoped grants
- Use stable identifiers in bundle rows:
  - organization by name
  - class by join code
  - staff target by username
- Import behavior is upsert-only (no destructive deletes) with strict validation and one atomic apply transaction.

**Why this remains active:**
- Enables reviewable policy handoff between environments and operators without manual UI re-entry.
- Keeps policy updates auditable (`rbac.policy.export`, `rbac.policy.import`) and minimizes accidental drift.

## Phase 2 RBAC custom-role persistence foundation

**Current decision:**
- Add first-class custom role entities:
  - `OrganizationCustomRole` (org-scoped role definitions),
  - `OrganizationCustomRoleCapability` (capabilities attached to custom roles),
  - `OrganizationCustomRoleAssignment` (user-role assignment per organization).
- Keep existing membership-role templates as the baseline policy source of truth.
- Apply custom-role capabilities additively in the evaluator:
  - effective capabilities = membership-role capabilities + assigned custom-role capabilities for that org.
- Keep scoped-grant precedence unchanged:
  - explicit deny > explicit allow > effective capability fallback.
- Register custom-role entities in Django admin and emit audit events on create/update/delete:
  - `organization.custom_role.*`
  - `organization.custom_role_capability.*`
  - `organization.custom_role_assignment.*`

**Why this remains active:**
- Begins RFC Phase 2 with low migration risk and no regression to current role-template behavior.
- Supports district-style delegated duties (for example, grant export/policy rights to specific staff) without adding new base membership roles.
- Preserves inspectability through explicit audit events before building broader custom-role UX and approval workflows.

## RBAC Phase 2 continuation: custom role tools + policy approval workflow

**Current decision:**
- Extend teacher RBAC tools with custom-role management actions:
  - `POST /teach/rbac/custom-role/upsert`
  - `POST /teach/rbac/custom-role/capability/upsert`
  - `POST /teach/rbac/custom-role/assignment/upsert`
- Extend policy-as-code bundle schema `classhub.rbac_policy.v1` with optional sections:
  - `custom_roles[]`
  - `custom_role_assignments[]`
- Add delegated approval workflow for RBAC mutations behind feature flag:
  - `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1`
  - queued model: `RbacPolicyChangeRequest`
  - review endpoint: `POST /teach/rbac/change-request/review`
  - requesters cannot approve their own changes.
- Keep immediate apply behavior unchanged when approval flag is disabled.

**Why this remains active:**
- Moves custom-role management from persistence-only to operator-usable workflows.
- Keeps policy handoff complete across environments by including custom-role policy rows in import/export bundles.
- Provides concrete review/approval separation for high-impact policy changes without forcing a hard cutover in current operations.

## View-size guard budget entry for RBAC tools module

**Current decision:**
- Add explicit view-size budget entry for `services/classhub/hub/views/teacher_parts/content_rbac_tools.py`:
  - max lines: `980`

**Why this remains active:**
- The RBAC Phase-2 rollout consolidated custom-role policy operations, change-request workflow, and scoped-grant tooling in one module to keep transaction and audit paths consistent during rollout.
- This budget is a temporary guardrail acknowledgment; follow-up refactor should split request parsing/apply/review helpers into smaller dedicated modules once behavior is stable in production.

## View-function budget entries for RBAC policy handlers

**Current decision:**
- Add explicit function-size budget entries:
  - `services/classhub/hub/views/teacher_parts/content_rbac_policy_io.py::teach_import_rbac_policy` -> `95`
  - `services/classhub/hub/views/teacher_parts/content_rbac_tools.py::teach_review_rbac_change_request` -> `85`

**Why this remains active:**
- These handlers intentionally keep validation + audit-safe branching in one function to preserve predictable request-level behavior during rollout.
- Budgets acknowledge current complexity while keeping CI strict against further accidental growth.

## Privacy/AI evidence dashboard v2 contract

**Current decision:**
- Extend `/teach/data-lifespan` with:
  - retention trend rows (7-day prune run activity),
  - tokenized CSV/JSON snapshot export endpoint (`/teach/data-lifespan/export?format=<json|csv>`),
  - helper RAG posture panel.
- Add audit event on each snapshot export:
  - `data_lifespan.snapshot_export`.
- Add helper-side internal status endpoint:
  - `GET /helper/internal/rag-status` (bearer token, same `HELPER_INTERNAL_API_TOKEN` contract as other helper internal control endpoints).
- Keep helper internal control/status auditing log-based inside Homework Helper:
  - emit structured `tutor.internal_audit` events for token failures, successful status reads, and remote-control/reset actions,
  - do not write cross-service helper-internal access into ClassHub `AuditEvent` rows.
- Keep helper RAG status response explicitly curriculum-only by contract:
  - includes per-reference chunk counts + last index timestamps,
  - includes explicit `student_data_excluded_from_index: true`.

**Why this remains active:**
- Gives operators and external evaluators exportable privacy/AI evidence without reading source code.
- Preserves least-privilege by keeping helper status introspection on token-protected internal routes only.
- Keeps retention and RAG posture in one operator surface so verification can be completed quickly during demos and audits.

## One-command full-stack smoke wrapper

**Current decision:**
- Add a repo-root `Makefile` operator shortcut:
  - `make smoke-full` -> runs `system_doctor.sh --smoke-mode golden` then `a11y_smoke.sh`.
- Keep existing scripts (`system_doctor.sh`, `a11y_smoke.sh`) as source-of-truth primitives.
- Allow small environment overrides through make variables (`SMOKE_COMPOSE_MODE`, `SMOKE_BASE_URL`, `SMOKE_INSTALL_BROWSERS`, etc.).

**Why this remains active:**
- Reduces operator cognitive load by giving non-specialists a single, repeatable command for full-stack confidence checks.
- Preserves script composability while making routine operations easier to delegate across staff turnover.

## Helper RAG SQL identifier compatibility + safety

**Current decision:**
- Keep SQL-composed identifiers in `services/homework_helper/tutor/engine/rag.py` for DDL/DML.
- Treat `table_name` as a relation name with 1-2 identifier parts (`table` or `schema.table`), split into parts and pass to `sql.Identifier(*parts)`.
- Reject invalid relation names (`invalid_rag_table_name`) before issuing SQL.
- Build index identifiers in the same schema as the target table so schema-qualified table names remain behavior-compatible.

**Why this remains active:**
- Prevents SQL-identifier injection risks while preserving callers that pass schema-qualified table names.
- Avoids accidental relation mismatches caused by quoting `schema.table` as a single identifier.
## Student submissions API material-id extraction contract

**Current decision:**
- In `api_student_submissions`, derive `material_ids` from `Material` rows scoped to the classroom (`Material.objects.filter(module__classroom=...)`) instead of reverse `modules.values_list("materials__id", flat=True)`.
- Short-circuit the endpoint response when no classroom materials exist, returning empty payload maps without querying submission/response/gallery tables.

**Why this remains active:**
- Prevents `None` IDs from reverse-join value lists from bypassing helper empty-list fast paths.
- Avoids unnecessary queries for newly created or partially populated classes while preserving response shape.
## Module/material prefetch contract for roster and UI density

**Current decision:**
- Treat module/material iteration in teacher dashboard and student UI-density resolution as prefetch-required paths.
- Keep `build_dashboard_context` to a single module/material prefetch pass and reuse the same in-memory module list after order normalization.
- Make `resolve_ui_density_mode_for_modules` fail fast when modules are not prefetched with `materials`:
  - raises `ValueError` with explicit `prefetch_related('materials')` guidance.
- Add service tests for:
  - parsing edge cases in `parse_extensions`,
  - malformed/missing-key handling in `_safe_reference_rows`,
  - prefetch enforcement in UI-density resolution,
  - single-fetch regression guard for dashboard context.

**Why this remains active:**
- Prevents accidental N+1 query regressions in hot class-home and teacher-dashboard paths.
- Keeps service contracts explicit and test-enforced so future callers do not silently fall back to per-module DB reads.
- Improves reviewer/operator confidence by codifying the query-safety decision in both tests and docs.

## Signal wiring and RAG SQL identifier hardening

**Current decision:**
- Keep Django signal registration in `HubConfig.ready()` as an explicit side-effect import using `import_module("hub.signals")`, instead of deleting the import.
- Remove unused `from __future__ import annotations` lines in `hub/forms.py` and `hub/signals.py`.
- Treat helper RAG table names as untrusted identifiers and enforce a strict allowlist before interpolating any SQL identifier:
  - allow only lowercase snake-case identifiers (`^[a-z_][a-z0-9_]*$`),
  - quote validated identifiers through Django DB ops (`connection.ops.quote_name(...)`),
  - raise `ValueError("invalid_rag_table_name")` for invalid inputs.
- Add helper-engine tests to assert invalid table names are rejected across schema/create, delete, upsert, and retrieval paths.

**Why this remains active:**
- Preserves required signal hookup behavior while eliminating style/lint noise.
- Closes identifier-interpolation risk in raw SQL paths even if future table-name configuration becomes dynamic.
- Keeps security posture inspectable through explicit tests instead of relying on assumptions about constant-only inputs.

## Canonical docs front door + strict production org-boundary defaults

**Current decision:**
- Consolidate repository onboarding around one canonical front-door contract:
  - `README.md` is the repo entrypoint (quick start + high-level architecture).
  - `docs/START_HERE.md` is the role router.
  - `docs/PUBLIC_OVERVIEW.md` is external evaluator/funder framing.
  - `docs/CURRENT_STATE.md` is shipped-state evidence for `main`.
- Remove overlapping README onboarding/architecture blocks so there is a single source of truth for first-read paths.
- Standardize top-level product naming in front-door docs as **Class Hub**.
- Change `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` runtime default to `True` in Class Hub settings.
- Keep explicit fallback posture only where intended:
  - `compose/.env.example.local` and local/day-1 presets keep `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`.
  - `compose/.env.example.domain` sets `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`.
- Align teacher/security/deploy/maturity docs with this posture and add explicit screenshot-status guidance in `CURRENT_STATE.md`.

**Why this remains active:**
- Reduces docs drift risk by giving each front-door document one ownership role.
- Makes the public-deploy path secure by default while preserving practical migration/local escape hatches.
- Improves external evaluator trust by making screenshot evidence state explicit instead of implicit.

## Teacher portal mode switcher for surface-density control

**Current decision:**
- Keep `/teach` as the same route, but add an explicit mode switcher contract via query param `portal_mode`.
- Supported modes:
  - `setup` (default),
  - `day`,
  - `all` (superuser + advanced mode),
  - `admin` (superuser + advanced mode),
  - `policy` (superuser + advanced mode).
- Apply mode visibility as rendering filters over existing sections/cards:
  - `day`: class-focus + digest + closeout + recent submissions.
  - `setup`: class setup, profile, import/template tools.
  - `admin`: organization/staff/operator surfaces.
  - `policy`: RBAC/policy/operator surfaces.
- Do not add new routes or new top-level workflow primitives as part of this change.

**Why this remains active:**
- Reduces first-contact cognitive load in `/teach` without removing existing capability.
- Preserves backward compatibility (`/teach` remains the same route with mode filtering rather than route sprawl).
- Aligns with stability-plan constraints to simplify entry-path complexity before adding net-new surface area.

## Strict org-boundary compatibility for legacy unscoped classes

**Current decision:**
- Keep strict org-boundary behavior for org-scoped classes when `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`.
- Preserve access fallback for legacy classes with no organization (`organization_id is null`) so existing class operations still work during migration.
- Permit `class.create` for staff without memberships only when there are zero active organizations, to support bootstrap/day-0 setup before org memberships exist.

**Why this remains active:**
- Prevents operational lockouts for legacy unscoped classes while still enforcing strict boundaries on org-scoped data.
- Preserves a controlled bootstrap path for first-run deployments without reopening broad legacy fallback once organizations are configured.

## Teacher home view-size guard split

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/content_home.py` focused on endpoints only.
- Move home-page state/context builders into:
  - `services/classhub/hub/views/teacher_parts/content_home_context.py`
  - `services/classhub/hub/views/teacher_parts/content_home_org_admin.py`
- Preserve behavior and template contract while satisfying `scripts/check_view_size_budgets.py` limits.

**Why this remains active:**
- Keeps view modules below dense-size thresholds so future changes stay reviewable.
- Reduces coupling by separating request handlers from context construction logic.

## Stability evidence pack automation (Day 0-30 Track B)

**Current decision:**
- Add `scripts/stability_release_evidence.sh` as the one-command collector for Day 0-30 release proof artifacts.
- Standardize evidence output under `artifacts/stability/<release-date>/` with:
  - `guardrails.log`
  - `test_inventory_coverage.log`
  - `system_doctor.log`
  - `a11y_smoke.log`
  - `restore_rehearsal.log`
  - `kiosk_resilience.log`
  - `release_artifact_lint.log`
  - `operator_scorecard.md`
- Add `make stability-evidence` to provide a stable operator entrypoint.

**Why this remains active:**
- Converts “run these checks” guidance into repeatable operational evidence.
- Reduces release sign-off ambiguity by producing one consistent artifact folder and scorecard each cycle.

## Canonical top-10 teacher task map for stability walkthroughs

**Current decision:**
- Create `docs/TEACHER_TOP_TASKS.md` as the canonical top-task list for `/teach`.
- Define each task with:
  - primary route/action contract,
  - explicit completion signal,
  - weekly walkthrough sequence (daily path first, then admin path).
- Link this task map from stability planning docs.

**Why this remains active:**
- Keeps teacher-surface stabilization tied to observed workflows, not theoretical portal structure.
- Provides a shared reference for copy/order improvements without introducing new workflow primitives.

## Turnover packet v1 as the canonical handoff artifact

**Current decision:**
- Add `docs/TURNOVER_PACKET.md` as the canonical turnover packet for Track C in the 30/60/90 stability plan.
- Standardize packet contents around:
  - 60-minute safe takeover path,
  - first-week confidence path,
  - command checklist by cadence (release/monthly/quarterly/incident),
  - owner + backup matrix,
  - cadence table and evidence log template.
- Link turnover packet from stability planning and survivability docs to keep handoff guidance centralized.

**Why this remains active:**
- Converts survivability guidance into an executable handoff checklist instead of narrative-only policy.
- Reduces maintainer dependency risk by making role ownership and required evidence explicit.

## Canonical outcomes/certificate semantics note

**Current decision:**
- Publish `docs/OUTCOME_SEMANTICS.md` as the canonical semantics reference for:
  - `artifact_submitted`,
  - `session_completed`,
  - `milestone_earned`,
  - certificate `eligible` and `issued` meanings.
- Link this semantics note from teacher and operator docs so reporting language stays consistent.

**Why this remains active:**
- Reduces interpretation drift between instructional, ops, and external reporting contexts.
- Keeps certificate/outcome communication aligned with the actual threshold/event contract in code.

## Ops cadence checklist for monthly/quarterly rituals

**Current decision:**
- Publish `docs/OPS_CADENCE_CHECKLIST.md` as the canonical recurring-operations checklist.
- Standardize monthly, quarterly, and per-release cadence steps with:
  - command sequence,
  - expected pass condition,
  - artifact/evidence location,
  - escalation rules.
- Link checklist from runbook and turnover packet docs.

**Why this remains active:**
- Prevents drift from "we usually run this" to explicit audited cadence.
- Improves survivability by making routine ops executable by backup maintainers.

## Org-boundary policy audit record for strict-mode governance

**Current decision:**
- Publish `docs/ORG_BOUNDARY_POLICY_AUDIT.md` as the canonical monthly policy-audit record for org-boundary posture.
- Require the audit to capture:
  - configured env value (`compose/.env`),
  - runtime Django setting value,
  - `/teach` warning-banner state,
  - reviewer + approver + next review date.
- Treat fallback mode (`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`) as exception posture requiring explicit approval metadata.

**Why this remains active:**
- Converts boundary-policy intent into an auditable recurring control.
- Reduces risk that fallback mode remains active silently in production.

## Stability owner/cadence tracker for risk governance

**Current decision:**
- Publish `docs/STABILITY_OWNER_CADENCE.md` as the canonical tracker for Risk IDs R1-R5 owner roles, backup roles, cadence, and next review dates.
- Require this tracker to be updated during each review cycle and linked from stability governance docs.

**Why this remains active:**
- Closes the gap between “risk register exists” and “risk governance runs on schedule.”
- Makes ownership continuity explicit during turnover and freeze periods.

## End-to-end reporting rehearsal playbook for risk R3

**Current decision:**
- Publish `docs/REPORTING_REHEARSAL.md` as the canonical playbook and evidence template for the reporting path rehearsal:
  - join,
  - artifact submission,
  - session completion review,
  - outcomes export,
  - certificate issue/re-issue.
- Require one dated evidence row per cadence cycle and link this playbook from stability ops docs.

**Why this remains active:**
- Converts reporting confidence from narrative assertion to repeatable operational evidence.
- Reduces outcome/certificate semantics drift by forcing periodic cross-role validation.

## Retention health snapshot command for risk R4 cadence

**Current decision:**
- Add `scripts/retention_health_snapshot.sh` as the canonical monthly retention-health command.
- The snapshot must include:
  - `classhub-retention.timer` state (when systemd is available),
  - recent `classhub-retention.service` logs (when available),
  - `retention_maintenance.sh --dry-run` output.
- Store output under `artifacts/stability/<date>/retention_health.log`.

**Why this remains active:**
- Reduces operational ambiguity by replacing multi-command spot checks with one evidence-ready command.
- Makes retention verification easier to run consistently during turnover and freeze periods.

## Restore rehearsal evidence wrapper for risk R4 quarterly drills

**Current decision:**
- Add `scripts/restore_rehearsal_evidence.sh` as the canonical quarterly restore rehearsal command.
- This wrapper must:
  - run `backup_restore_rehearsal.sh`,
  - capture rehearsal log,
  - write metrics (`RTO`/`RPO`) JSON,
  - record whether the drill was same-host or replacement-host proof plus the rehearsal host label,
  - copy backup artifacts and write checksums,
  - emit a human-readable summary markdown.
- Record each rehearsal in `docs/RESTORE_REHEARSAL_LOG.md` with date, result, evidence path, and next review date.

**Why this remains active:**
- Converts restore confidence from periodic ad-hoc checks into durable, auditable evidence.
- Gives turnover and release governance one stable source of truth for quarterly recovery readiness.

## Turnover drill log for risk R5 survivability evidence

**Current decision:**
- Publish `docs/TURNOVER_DRILL_LOG.md` as the canonical evidence log for maintainer turnover drills.
- Require each drill to record:
  - 60-minute path result,
  - first-day path result,
  - whether backup maintainer completed checks without coaching,
  - blockers and doc patch follow-ups,
  - next drill date.
- Link this log from turnover packet and cadence docs.

**Why this remains active:**
- Converts turnover readiness from a one-time narrative into repeatable evidence.
- Makes survivability regressions visible before a real staff transition occurs.

## Stability Phase 1 + telemetry Slice 7 cycle gate policy (2026-03-10)

**Current decision:**
- Current-cycle closeout for Day 0-30 stability Phase 1 and telemetry Slice 7 requires one command-backed evidence packet under `artifacts/stability/<YYYY-MM-DD>/` plus telemetry artifacts under `artifacts/stability/<YYYY-MM-DD>/telemetry/`.
- Gate C parity threshold for this cycle is strict zero drift; any unresolved parity delta is a hard blocker for sign-off.
- Keep telemetry steady state at `CLASSHUB_TELEMETRY_WRITE_MODE=dual` for this cycle.
- Defer Gate D (`telemetry_only`) decision to the next review cycle after another full evidence pass.
- Runtime lock for this cycle is explicit:
  - `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`
  - `CLASSHUB_TELEMETRY_WRITE_MODE=dual`
  - `CLASSHUB_TELEMETRY_READ_MODE=telemetry`
- As of March 10, 2026, Gate C technical evidence capture passed for this cycle:
  - `artifacts/stability/2026-03-10/cycle_closeout_summary.md`
  - `artifacts/stability/2026-03-10/telemetry/parity_check.log`
  - `artifacts/stability/2026-03-10/telemetry/smoke_strict.log`
  - `artifacts/stability/2026-03-10/telemetry/rollback_drill.log`
- Gate D remains deferred; production write mode stays `dual` until the next full-cycle review.

**Why this remains active:**
- Enforces proof-first sign-off criteria for stability and telemetry rollouts.
- Reduces cutover risk by requiring strict parity and rollback drill evidence before any write-mode escalation.

## Telemetry SLO evidence renderer + telemetry-aware restore rehearsal (2026-05-07)

**Current decision:**
- Replace the hand-edited telemetry `slo_summary.md` placeholder path with an explicit renderer:
  - `scripts/render_telemetry_slo_summary.py`
  - wired through `scripts/telemetry_stabilization_evidence.sh`
  - enforced during full closeout by `scripts/stability_phase1_closeout.sh`
- Require explicit baseline/observed metric inputs for:
  - student home p95 latency,
  - student upload success rate,
  - helper chat 5xx rate.
- Extend disaster-recovery tooling so telemetry split environments can rehearse both databases intentionally:
  - `scripts/backup_telemetry_postgres.sh`
  - `scripts/backup_restore_rehearsal.sh --include-telemetry-db`
  - `scripts/restore_rehearsal_evidence.sh --include-telemetry-db`
- When telemetry rehearsal is not enabled, force restore validation to run with telemetry env overrides disabled so rehearsal commands do not accidentally point at the live telemetry database.

**Why this remains active:**
- Converts telemetry SLO closeout from a markdown TODO into a repeatable operator command path.
- Removes ambiguity about whether telemetry DB disaster recovery is covered when the split is active.
- Prevents restore rehearsal from quietly validating core data while still reading from a live telemetry endpoint.

## Runtime policy lock surfaced in `/teach` and evidence guardrails (2026-03-11)

**Current decision:**
- Add a superuser-only runtime lock panel to `/teach` advanced mode (`/teach?advanced=1&portal_mode=admin`) that reports PASS/FAIL for:
  - `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF` strict mode,
  - telemetry rollout modes (`CLASSHUB_TELEMETRY_WRITE_MODE`, `CLASSHUB_TELEMETRY_READ_MODE`),
  - explicit certificate threshold env posture (`CLASSHUB_CERTIFICATE_MIN_SESSIONS`, `CLASSHUB_CERTIFICATE_MIN_ARTIFACTS`).
- Add `scripts/check_runtime_policy_lock.py` and run it inside `scripts/stability_release_evidence.sh` guardrails.
- Treat runtime lock mismatch as a release-evidence blocker until env values are aligned.

**Why this remains active:**
- Converts policy-sensitive deployment assumptions into in-product and command-backed checks.
- Reduces reliance on maintainer memory when validating org-boundary and telemetry posture before release sign-off.

## Teacher top-task choreography surfaced in `/teach` (2026-03-11)

**Current decision:**
- Add a `Start Here Today` contract block to `/teach` for `portal_mode=setup|day|all`:
  - daily teaching workflows (tasks 1-8),
  - operator/policy workflows (tasks 9-10) only for superuser context.
- Keep task definitions canonical in `docs/TEACHER_TOP_TASKS.md` and enforce wiring with `scripts/check_teacher_top_tasks_contract.py`.
- Run this guard from `scripts/stability_release_evidence.sh` guardrails.

**Why this remains active:**
- Reduces teacher UI ambiguity by giving one explicit default sequence for recurring class operations.
- Prevents future drift between documented top tasks and actual `/teach` discoverability.

## Canonical docs truth map and stale-status refresh discipline (2026-03-11)

**Current decision:**
- Treat `docs/CURRENT_STATE.md` as the canonical shipped-state page and keep its date aligned with significant state changes.
- Keep `docs/DOCS_MAP.md` authoritative for "which doc wins" when readers encounter overlapping guidance.
- Keep `docs/MAINTENANCE_RISK_REGISTER.md` risk evidence grounded in guardrail-enforced signals (for example view-size/function budget checks), not only narrative claims.
- When telemetry/stability gate status changes, update `CURRENT_STATE.md` and reference concrete artifact paths under `artifacts/stability/<date>/`.

**Why this remains active:**
- Reduces documentation tax by making fewer files responsible for truth ownership.
- Lowers stale-doc risk by tying high-impact status claims to concrete evidence artifacts and guardrail checks.

## Screenshot gallery status split: captured baseline vs pending backlog (2026-03-11)

**Current decision:**
- Keep `docs/SCREENSHOT_GALLERY.md` scoped to currently captured screenshots only.
- Track uncaptured screenshot slots in `press/screenshots/PLACEHOLDERS.md` (including optional companion captures) and avoid implying full-shotlist completion in public docs until files exist.
- Keep `docs/PUBLIC_OVERVIEW.md` wording aligned with this split by labeling embeds as captured baseline and linking pending slots to the placeholder tracker.

**Why this remains active:**
- Prevents public-facing documentation from overstating visual evidence coverage.
- Gives reviewers one reliable place to distinguish shipped screenshots from backlog captures.

## Runtime policy lock profiles: baseline vs release (2026-03-11)

**Current decision:**
- Split `scripts/check_runtime_policy_lock.py` into explicit profiles:
  - `baseline`: validates explicit boundary/telemetry/certificate env posture without enforcing release-only rollout gates.
  - `release`: enforces strict closeout lock values for org-boundary and telemetry rollout (`1 / dual / telemetry`) plus explicit certificate thresholds.
- Wire release evidence paths to call `--profile release` explicitly:
  - `scripts/stability_release_evidence.sh`
  - `scripts/stability_phase1_closeout.sh`
- Keep `runtime_lock_check.log` as a generated artifact during cycle closeout using the same script (`--markdown`), so closeout and guardrails share one source of truth.

**Why this remains active:**
- Removes ambiguity where example env files looked "wrong" against release-only checks.
- Reduces drift risk by eliminating duplicate runtime-lock logic across scripts.

## Teach class template decomposition contract (2026-03-11)

**Current decision:**
- Keep `services/classhub/templates/teach_class.html` as the orchestration shell only (header, class focus block, include wiring).
- Move heavy section cards into `services/classhub/templates/includes/teach_class/*` partials:
  - class setup + roster,
  - facilitator support board,
  - outcomes snapshot,
  - helper signals,
  - lesson tracker,
  - module editor.
- Add `scripts/check_teach_class_template_contract.py` as a guardrail that enforces:
  - root template size budget (`teach_class.html` <= 220 lines),
  - required include wiring,
  - required section anchor IDs in partials.
- Run this guard in `scripts/stability_release_evidence.sh` guardrails.

**Why this remains active:**
- Reduces cognitive load in the main `/teach/class` template without changing behavior.
- Prevents silent template re-growth by making decomposition an explicit contract.

## Teach class dashboard service decomposition contract (2026-03-11)

**Current decision:**
- Keep `services/classhub/hub/services/teacher_roster_class.py` as orchestration + export entry points.
- Move section-level context logic into dedicated modules under `services/classhub/hub/services/teacher_dashboard_sections/`:
  - `roster.py` (submission/tag context),
  - `facilitator_support.py` (support board snapshot),
  - `outcomes.py` (outcome rollups + certificate snapshot helpers),
  - `shared.py` (typed setting/detail helpers).
- Keep compatibility wrapper function names in `teacher_roster_class.py` for existing imports/tests (`_build_outcome_snapshot`, `_build_facilitator_support_snapshot`, `_material_submission_counts`, etc.).
- Add `scripts/check_teacher_roster_service_contract.py` and run it in stability release guardrails.

**Why this remains active:**
- Reduces maintenance risk by aligning backend structure with `/teach/class` section boundaries.
- Prevents regressions from refactor drift while preserving current external call sites.

## Press backlog governance + teach class section budgets (2026-03-11)

**Current decision:**
- Add `scripts/check_press_capture_backlog_contract.py` to enforce press-layer governance contracts:
  - bounded capture backlog size (max 3),
  - explicit owner + target closeout date in `press/screenshots/PLACEHOLDERS.md`,
  - required linkage markers in `docs/PUBLIC_OVERVIEW.md` and `docs/CURRENT_STATE.md`.
- Add `scripts/check_teach_class_section_budgets.py` to enforce line budgets for:
  - `/teach/class` include partials,
  - `/teach/class` section service modules (`teacher_dashboard_sections/*`).
- Run both checks in `scripts/stability_release_evidence.sh` guardrails.

**Why this remains active:**
- Keeps public/press evidence lag visible and bounded instead of ad-hoc.
- Prevents redistributed complexity in section partials/services from becoming the next monolith.

## Teach class setup/roster card split into sub-partials (2026-03-11)

**Current decision:**
- Split `class_setup_and_roster_card.html` into focused sub-partials:
  - `class_setup_landing_section.html`
  - `class_setup_invites_section.html`
  - `class_setup_staff_assignments_section.html`
  - `class_setup_roster_section.html`
- Keep the parent card as orchestration + notice/error shell only.
- Tighten section budgets so complexity pressure applies to each subsection, not just the aggregate card.
- Extend `check_teach_class_template_contract.py` to validate nested include wiring for this card.

**Why this remains active:**
- Continues reducing cognitive load in the heaviest `/teach/class` section without behavior change.
- Avoids recreating a monolith inside one "section partial" by enforcing subsection boundaries.

## Teach lesson tracker split into focused row/release/dropbox partials (2026-03-11)

**Current decision:**
- Split `lesson_tracker_card.html` into focused lesson-tracker partials:
  - `lesson_tracker_row_lesson_cell.html`
  - `lesson_tracker_dropbox_cell.html`
  - `lesson_tracker_release_controls.html`
  - `lesson_tracker_helper_tuning.html`
- Keep `lesson_tracker_card.html` as section/table orchestration only.
- Extend `check_teach_class_template_contract.py` to enforce nested include wiring for lesson tracker row/release/helper/dropbox partials.
- Tighten `check_teach_class_section_budgets.py` with explicit budgets for each new lesson-tracker partial.

**Why this remains active:**
- Reduces cognitive load in lesson-tracker maintenance by isolating independent responsibilities.
- Keeps release/helper tuning complexity from silently re-accumulating in the section wrapper.

## Teach class section service split: outcomes/facilitator internals (2026-03-11)

**Current decision:**
- Keep public section-builder entrypoints stable in:
  - `teacher_dashboard_sections/outcomes.py`
  - `teacher_dashboard_sections/facilitator_support.py`
- Move heavy internal aggregation/row-building logic into focused helper modules:
  - `outcomes_rollup.py`
  - `outcomes_snapshot.py`
  - `facilitator_support_builders.py`
- Expand section budget guard coverage to include these helper modules and tighten wrapper module budgets so orchestration files stay thin.
- Extend roster service decomposition guard to require the new section helper modules.

**Why this remains active:**
- Reduces maintenance risk by separating aggregation/query logic from section orchestration surfaces.
- Prevents “split once, regrow later” drift by enforcing budgets/contracts on the new helper modules too.

## Teach class roster section split into focused roster sub-partials (2026-03-11)

**Current decision:**
- Split `class_setup_roster_section.html` into focused sub-partials:
  - `class_setup_roster_table.html`
  - `class_setup_roster_student_row.html`
  - `class_setup_roster_merge_zone.html`
  - `class_setup_roster_danger_zone.html`
- Keep `class_setup_roster_section.html` as section wrapper/orchestration only.
- Extend `check_teach_class_template_contract.py` to enforce nested include wiring for roster section/table.
- Tighten `check_teach_class_section_budgets.py` so each new roster sub-partial has an explicit line budget.

**Why this remains active:**
- Keeps the highest-density teacher roster controls prunable and easier to reason about.
- Prevents destructive-action and student-row complexity from regrowing inside one section file.

## Ops-readiness command + policy-mode access contract guard (2026-03-11)

**Current decision:**
- Add a single host-level readiness command path:
  - `make ops-readiness`
  - backed by `scripts/ops_readiness_check.sh` (default `baseline` runtime lock profile, optional `release` profile argument).
- Include runtime-lock + decomposition + truth/backlog checks in that path:
  - `check_runtime_policy_lock.py`
  - `check_teach_class_template_contract.py`
  - `check_teach_class_section_budgets.py`
  - `check_teacher_roster_service_contract.py`
  - `check_docs_truth.py`
  - `check_test_inventory_coverage.py`
  - `check_press_capture_backlog_contract.py`
- Add `scripts/check_teacher_policy_mode_contract.py` to lock advanced-tools semantics:
  - advanced tools require superuser,
  - policy/RBAC tools require superuser + advanced mode.
- Run this policy-mode guard in both lint CI and release-evidence guardrails.
- Tighten selected teach-class budgets to preserve headroom before files regrow near ceilings.

**Why this remains active:**
- Moves another high-risk operational expectation from "remembered ritual" to executable contract.
- Prevents docs/wording drift around policy/RBAC access semantics by asserting one source of truth in code + template wiring.

## Lesson front matter course-slug consistency guard (2026-03-11)

**Current decision:**
- Enforce lesson front matter `course`/`course_slug` consistency with course folder + manifest slug.
- Add dependency-free guard `scripts/check_lesson_course_slug_consistency.py` and run it in:
  - lint CI (`.github/workflows/lint.yml`)
  - stability release guardrails (`scripts/stability_release_evidence.sh`)
  - ops readiness check (`scripts/ops_readiness_check.sh`)
- Extend `scripts/validate_coursepack.py` to fail when lesson front matter course slug is missing, invalid, or mismatched.
- Normalize existing Piper lesson front matter to use `piper_scratch_12_session` for strict consistency.

**Why this remains active:**
- Prevents content-identity drift across lessons inside a coursepack.
- Catches high-impact authoring mistakes before deploy and before release evidence closeout.

## Minimum-viable operator floor + release evidence index (2026-03-11)

**Current decision:**
- Publish `docs/MINIMUM_VIABLE_OPERATOR.md` as a one-page operator skill-floor contract.
- Link this skill-floor doc from:
  - `docs/DAY1_DEPLOY_CHECKLIST.md`
  - `docs/RUNBOOK.md`
  - `docs/ORG_BOUNDARY_POLICY_AUDIT.md`
- Generate `artifacts/stability/<date>/EVIDENCE_INDEX.md` in `scripts/stability_release_evidence.sh` so evaluators/operators can inspect one canonical artifact index per run.
- Treat `EVIDENCE_INDEX.md` as a required artifact in `scripts/stability_phase1_closeout.sh`.

**Why this remains active:**
- Reduces handoff ambiguity by defining the minimum operator capability explicitly.
- Improves release-bundle inspectability by turning artifact discovery into a stable, generated index.

## Localization slice: student class core translation pass (2026-03-11)

**Current decision:**
- Expand i18n coverage from join/login-only into core student flows by wrapping high-frequency user-facing strings in `{% trans %}` / `{% blocktrans %}` across:
  - `services/classhub/templates/student_class.html`
  - `services/classhub/templates/student_my_data.html`
  - `services/classhub/templates/student_portfolio.html`
  - `services/classhub/templates/student_portfolio_index.html`
- Add/refresh Spanish translations in `services/classhub/locale/es/LC_MESSAGES/django.po` and compile locale catalogs.
- Add regression coverage in `hub.tests.test_i18n` for Spanish rendering on:
  - `/student` (`Enlaces del curso`)
  - `/student/my-data` (`Privacidad en resumen`)
  - `/student/portfolio` (`Filtros`)
- Update localization/docs posture to reflect current coverage honestly:
  - `docs/LOCALIZATION.md`
  - `docs/CURRENT_STATE.md`

**Why this remains active:**
- Closes part of the values-to-implementation gap for multilingual classroom use.
- Keeps localization progress inspectable and test-backed instead of aspirational.

## Release handoff packaging contract: source zip + companion evidence bundle (2026-03-11)

**Current decision:**
- Keep `scripts/make_release_zip.sh` as a tracked-source-only archive path (`git ls-files` + release artifact lint).
- Treat release-cycle evidence under `artifacts/stability/<release-date>/` as a companion artifact set, not part of the source zip contract.
- Require evaluator/operator handoff language in docs to point reviewers to:
  - source bundle (`dist/classhub_release_*.zip`)
  - companion evidence bundle (`artifacts/stability/<release-date>/`, typically packaged as `dist/classhub_evidence_<release-date>.tgz`)
  - `EVIDENCE_INDEX.md` as first-stop artifact index.
- Document baseline-vs-release runtime lock profile expectations in one canonical page:
  - `docs/RUNTIME_LOCK_PROFILES.md`

**Why this remains active:**
- Removes ambiguity where reviewers expect runtime evidence artifacts inside the source archive.
- Improves external inspectability by making source code provenance and release evidence provenance explicit and separate.

## Classroom-realistic helper evaluation protocol + model decision rubric (2026-03-11)

**Current decision:**
- Add a classroom-realistic prompt pack for Helper quality checks:
  - `services/homework_helper/tutor/fixtures/eval_prompts_classroom_realistic.jsonl`
  - includes teacher expectations and lightweight phrase contracts (`required_any`, `required_all`, `forbidden_any`).
- Extend `scripts/eval_helper.py` with:
  - aggregate summary outputs (`--summary-json`, `--summary-md`),
  - optional pass-rate gate (`--min-pass-rate`, `--fail-on-min-pass-rate`),
  - phrase-contract scoring hooks.
- Add one-command runner:
  - `scripts/run_helper_classroom_eval.sh`
  - writes `results.jsonl`, `summary.json`, `summary.md` to a timestamped output folder.
- Publish decision rubric in docs (`docs/HELPER_EVALS.md`) for when to keep local `llama3.2:1b` versus trial a stronger model backend.

**Why this remains active:**
- Moves Helper model-quality discussions from anecdotal feedback to repeatable evidence.
- Gives ops/teaching leads a concrete signal for model sufficiency without requiring paid services in the evaluation loop.

## Classroom helper strictness hardening closed with 18/18 strict pass (2026-03-12)

**Current decision:**
- Close the current classroom-helper hardening loop after authenticated strict-mode eval reaches full pass:
  - strict `v6`: `18/18` (`pass_rate=1.0`) on `eval_prompts_classroom_realistic.jsonl`
  - light `v4`: `15/18` (`pass_rate=0.8333`) retained as comparison baseline.
- Keep deterministic guardrail responses for four previously failing classroom contracts:
  - class re-entry privacy (`display name` + `class code` + `teacher` guidance),
  - score-condition debugging (`if condition` + `check` framing),
  - publish-without-full-name privacy,
  - wellbeing reset (`not dumb` + `small next step`).
- Treat `/tmp/classhub_helper_eval_strict_v6` and `/tmp/classhub_helper_eval_light_v4` summaries as completion evidence for this cycle.

**Why this remains active:**
- Confirms strict-mode helper behavior can satisfy the classroom rubric without paid-model escalation.
- Converts prior phrase-contract misses into test-backed deterministic paths, reducing churn in future eval cycles.

## Teacher/admin hotspot budgets + runtime-lock profile labeling hardening (2026-03-12)

**Current decision:**
- Add a dedicated governance-surface growth guard:
  - `scripts/check_teacher_admin_hotspot_budgets.py`
  - enforces explicit line ceilings on known teacher/admin/RBAC hotspot files:
    - `hub/tests/test_teacher_admin_portal.py`
    - `hub/services/org_access.py`
    - `hub/services/rbac_policy_bundle.py`
    - `hub/views/teacher_parts/content_rbac_view_endpoints.py`
    - `templates/includes/teach_home/setup_sections_rbac_panel.html`
- Wire this guard into:
  - CI lint workflow (`.github/workflows/lint.yml`)
  - release-evidence guardrails (`scripts/stability_release_evidence.sh`)
  - fast operator readiness checks (`scripts/ops_readiness_check.sh`)
- Make baseline-vs-release runtime lock expectations explicit where operators look first:
  - annotate `compose/.env.example.domain` telemetry defaults as **baseline-only** and release-profile-fail-by-design.
  - extend `docs/RUNTIME_LOCK_PROFILES.md` with an explicit expected-failure example for `--profile release` on `.env.example.domain`.
  - extend `scripts/check_runtime_policy_lock.py` release failure output with a targeted note when the checked file is a `.env.example.*` path.

**Why this remains active:**
- Prevents governance-heavy staff surfaces from silently becoming the next monolith.
- Reduces operator confusion between deploy-baseline env examples and strict release-closeout lock posture.

## Localization tranche contract: family-visible first (`/student` + `/teach` day mode) (2026-03-12)

**Current decision:**
- Define a bounded localization tranche for family-visible flows:
  - student class route: `/student`
  - teacher day-of-class route: `/teach?portal_mode=day`
- Translate top teacher day-of-class copy in `services/classhub/templates/includes/teach_home/day_sections.html` using `{% trans %}` and `{% blocktrans %}` for headings, digest labels, closeout labels, and primary actions.
- Add/refresh matching Spanish + Somali + S'gaw Karen strings in:
  - `services/classhub/locale/es/LC_MESSAGES/django.po`
  - `services/classhub/locale/so/LC_MESSAGES/django.po`
  - `services/classhub/locale/ksw/LC_MESSAGES/django.po`
- Add dedicated route regression coverage in `hub.tests.test_i18n`:
  - `test_teach_home_day_mode_spanish_renders_translated_core_copy`
  - `test_teach_home_day_mode_somali_renders_translated_core_copy`
  - `test_teach_home_day_mode_sgaw_karen_renders_translated_core_copy`
- Add enforceable contract guard:
  - `scripts/check_i18n_family_visible_contract.py`
  - validates doc tranche markers, required tests, required template translation markers, and non-empty Spanish + Somali + S'gaw Karen translations for tranche msgids.
- Wire this guard into:
  - CI lint workflow (`.github/workflows/lint.yml`)
  - release-evidence guardrails (`scripts/stability_release_evidence.sh`)
  - fast operator readiness checks (`scripts/ops_readiness_check.sh`)

**Why this remains active:**
- Keeps localization progress bounded, inspectable, and test-backed instead of broad narrative promises.
- Prioritizes high-frequency classroom/family-visible copy before wider admin-surface translation expansion.

## Somali i18n expansion for family-visible routes + peer-feedback defaults (2026-03-12)

**Current decision:**
- Add Somali (`so`) to supported UI languages in `config/settings.py`.
- Add Somali locale catalog scaffold at `services/classhub/locale/so/LC_MESSAGES/django.po` and compile `django.mo`.
- Extend peer-feedback default sentence starters with Somali copy in `hub/services/peer_feedback.py`.
- Add Somali route checks in `hub.tests.test_i18n` and Somali starter checks in `hub.tests.test_student_ops`.
- Keep Somali rollout bounded to family-visible routes and student-facing starter copy first; broader admin translation remains iterative.

**Why this remains active:**
- Makes multilingual commitments more locally relevant for Minneapolis-family contexts without requiring a full-surface translation freeze.
- Ensures Somali support is enforced by tests and guardrails rather than left as an unverified promise.

## Documentation mass control: canonical truths index (2026-03-12)

**Current decision:**
- Add a central source-of-truth index at `docs/CANONICAL_TRUTHS.md`.
- Use this page as the first resolver when documentation appears to overlap.
- Keep one canonical doc per policy area and list supporting docs as secondary references.
- Link the index from core entry points:
  - `docs/START_HERE.md`
  - `docs/PUBLIC_OVERVIEW.md`
  - `docs/RUNBOOK.md`
  - `docs/DOCS_MAP.md`
  - `docs/CURRENT_STATE.md`
  - `docs/index.md`

**Why this remains active:**
- Reduces decision fatigue for operators and evaluators who face high doc volume.
- Preserves detailed docs while enforcing a single-entry canonical path per policy concern.

## Teacher RBAC panel pruning: split monolithic template into bounded partials (2026-03-12)

**Current decision:**
- Decompose `services/classhub/templates/includes/teach_home/setup_sections_rbac_panel.html` into focused include partials under:
  - `services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_scope_and_simulation.html`
  - `services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_custom_roles.html`
  - `services/classhub/templates/includes/teach_home/rbac_tools/rbac_tools_policy_and_audit.html`
- Keep the root RBAC panel template as a thin orchestration shell that only renders panel header/intro and includes section partials.
- Tighten hotspot guard budgets in `scripts/check_teacher_admin_hotspot_budgets.py` to enforce the split shape:
  - root panel budget reduced to `80` lines
  - each new section partial receives its own explicit budget ceiling

**Why this remains active:**
- Reduces single-file cognitive load in the highest-pressure governance surface without changing RBAC behavior.
- Prevents future “sideways monolith” drift by budgeting the new partials directly.

## Teacher org-admin panel pruning: split superuser panel into bounded partials (2026-03-12)

**Current decision:**
- Decompose `services/classhub/templates/includes/teach_home/setup_sections_org_admin_panel.html` into focused include partials under:
  - `services/classhub/templates/includes/teach_home/org_admin/org_admin_organizations_and_memberships.html`
  - `services/classhub/templates/includes/teach_home/org_admin/org_admin_class_assignments_and_moves.html`
  - `services/classhub/templates/includes/teach_home/org_admin/org_admin_role_capability_templates.html`
- Keep the root org-admin panel template as a thin orchestration shell.
- Extend hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py` so the split stays enforced:
  - root panel budget `60`
  - section partial budgets `220` / `190` / `120`

**Why this remains active:**
- Lowers cognitive load in the superuser governance surface while preserving current behavior.
- Keeps decomposition durable by enforcing explicit per-partial line ceilings.

## Teacher RBAC endpoint pruning: move shared view helpers out of endpoint module (2026-03-12)

**Current decision:**
- Extract shared RBAC view helper logic from `services/classhub/hub/views/teacher_parts/content_rbac_view_endpoints.py` into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_helpers.py`
- Keep endpoint handlers focused on request/response orchestration while shared redirect/state/change-review helpers live in the new helper module.
- Tighten hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py`:
  - endpoint module budget reduced to `500`
  - new helper module budget set to `240`

**Why this remains active:**
- Reduces single-file cognitive load in the RBAC endpoint hotspot without changing behavior.
- Prevents complexity from regrowing invisibly by budgeting both the entrypoint module and extracted helper module.

## Teacher RBAC endpoint split seam II

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/content_rbac_view_endpoints.py` as a thin compatibility facade exporting the existing RBAC endpoint/context symbols.
- Move RBAC access predicates into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_access.py`
- Move RBAC context assembly for `teach_home` into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_context.py`
- Move RBAC mutation handlers into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_mutations.py`
- Move RBAC simulation/review handlers into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_review.py`
- Preserve route wiring and imports by keeping export names unchanged in the facade module.
- Update guard contracts:
  - move function budget mapping for `teach_review_rbac_change_request` to `content_rbac_view_review.py` in `scripts/view_function_budgets.json`
  - tighten/add hotspot budgets for facade + new split modules in `scripts/check_teacher_admin_hotspot_budgets.py`

**Why this remains active:**
- Reduces cognitive load in RBAC teacher-home endpoint code without behavior changes.
- Keeps context assembly, mutation actions, and review flow bounded so governance complexity does not re-form as one hotspot file.

## Teacher RBAC helper split seam

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/content_rbac_view_helpers.py` as a compatibility facade for shared RBAC helper exports.
- Move RBAC state/redirect helper logic into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_state.py`
- Move RBAC change-request/policy helper logic into:
  - `services/classhub/hub/views/teacher_parts/content_rbac_view_change_requests.py`
- Preserve existing helper import names via facade re-exports so endpoint/context modules do not change behavior.
- Extend hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py` for the new split modules and tighten the facade budget.

**Why this remains active:**
- Reduces cognitive load in RBAC shared helper code without behavior changes.
- Keeps state/redirect wiring and change-request policy logic bounded so the helper layer does not become the next governance hotspot.

## Org access policy pruning: split capability evaluator from class-access facade (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/org_access.py` as the stable public facade for class-access helpers and public exports.
- Move capability-policy evaluation internals into:
  - `services/classhub/hub/services/org_access_capabilities.py`
- Preserve existing external API contracts (`CAP_*`, `evaluate_staff_capability`, `staff_can*`, `staff_default_organization`) via re-exports from `org_access.py`.
- Tighten hotspot guard budgets in `scripts/check_teacher_admin_hotspot_budgets.py`:
  - `org_access.py` reduced to `260`
  - new `org_access_capabilities.py` budget set to `620`

**Why this remains active:**
- Reduces cognitive load in one of the highest-pressure governance services without behavior changes.
- Keeps the capability engine isolated so future policy growth does not re-expand the facade module.

## RBAC policy bundle pruning: split normalize/export/apply layers (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/rbac_policy_bundle.py` as the stable public facade exposing:
  - `POLICY_SCHEMA_VERSION`
  - `build_rbac_policy_export_payload`
  - `validate_rbac_policy_payload`
  - `apply_rbac_policy_payload`
- Move normalization and export payload shaping into:
  - `services/classhub/hub/services/rbac_policy_bundle_normalize.py`
- Move transactional persistence apply logic into:
  - `services/classhub/hub/services/rbac_policy_bundle_apply.py`
- Tighten hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py`:
  - `rbac_policy_bundle.py` reduced to `180`
  - `rbac_policy_bundle_normalize.py` budget `560`
  - `rbac_policy_bundle_apply.py` budget `180`

**Why this remains active:**
- Preserves external import stability while reducing cognitive load in the top-level policy bundle service.
- Isolates high-churn normalization and persistence logic so future growth is bounded and reviewable.

## Teacher tracker pruning: split digest, helper signals, and lesson tracker modules (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/teacher_tracker.py` as a compatibility facade exporting existing helper names.
- Move focused logic into dedicated modules:
  - `services/classhub/hub/services/teacher_tracker_digest.py`
  - `services/classhub/hub/services/teacher_tracker_helper_signals.py`
  - `services/classhub/hub/services/teacher_tracker_lessons.py`
  - shared panel cache helpers in `services/classhub/hub/services/teacher_tracker_cache.py`
- Preserve existing external contracts used by views/services/tests:
  - `_build_class_digest_rows`
  - `_local_day_window`
  - `_build_helper_signal_snapshot`
  - `_build_lesson_tracker_rows`
  - `_material_submission_counts`
  - `_material_latest_upload_map`
- Tighten hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py`:
  - `teacher_tracker.py` budget `90`
  - `teacher_tracker_digest.py` budget `220`
  - `teacher_tracker_helper_signals.py` budget `180`
  - `teacher_tracker_lessons.py` budget `340`

**Why this remains active:**
- Reduces cognitive load in a high-traffic teacher dashboard service without changing behavior.
- Makes future tracker changes easier to review and less likely to re-form a single-file hotspot.

<a id="teacher-roster-class-export-split-seam"></a>
## Teacher roster class export split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/teacher_roster_class_exports.py` as a compatibility facade exposing:
  - `export_submissions_today_archive`
  - `export_class_summary_csv`
  - `export_class_outcomes_csv`
- Move export internals into focused modules:
  - `services/classhub/hub/services/teacher_roster_class_exports_archive.py`
  - `services/classhub/hub/services/teacher_roster_class_exports_summary.py`
  - `services/classhub/hub/services/teacher_roster_class_exports_outcomes.py`
- Preserve existing imports through `services/classhub/hub/services/teacher_roster_class.py` so views/tests do not change call sites.
- Extend hotspot guardrails in `scripts/check_teacher_admin_hotspot_budgets.py` with explicit line budgets for the facade and each new export module.

**Why this remains active:**
- Reduces cognitive load in roster export logic without changing export behavior.
- Prevents the export layer from reforming as a single-file hotspot.

<a id="teacher-class-endpoint-split-seam"></a>
## Teacher class endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_class.py` as a compatibility facade for class-level roster endpoints.
- Move class dashboard/create/join-card handlers into:
  - `services/classhub/hub/views/teacher_parts/roster_class_dashboard.py`
- Move class control/export handlers into:
  - `services/classhub/hub/views/teacher_parts/roster_class_controls.py`
- Preserve existing test monkeypatch contract for helper reset by keeping:
  - `_reset_helper_class_conversations` import and `teach_reset_helper_conversations` wrapper in `roster_class.py`.
- Extend `scripts/check_teacher_admin_hotspot_budgets.py` with explicit budgets for the facade and both new modules.

**Why this remains active:**
- Reduces cognitive load in one of the highest-churn teacher class endpoint surfaces without route behavior changes.
- Preserves compatibility for existing tests/imports while preventing the split modules from silently regrowing.

<a id="teacher-materials-endpoint-split-seam"></a>
## Teacher materials endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_materials.py` as a compatibility facade for teacher module/material/submission endpoints.
- Move module/material CRUD and ordering handlers into:
  - `services/classhub/hub/views/teacher_parts/roster_materials_module_ops.py`
- Move submission/rubric review and ZIP export endpoint into:
  - `services/classhub/hub/views/teacher_parts/roster_materials_submissions.py`
- Preserve external imports and route wiring by keeping endpoint export names unchanged in the facade.
- Update guard contracts:
  - move function budget mapping for `teach_material_submissions` to `roster_materials_submissions.py` in `scripts/view_function_budgets.json`
  - add hotspot budgets for facade + split modules in `scripts/check_teacher_admin_hotspot_budgets.py`

**Why this remains active:**
- Reduces cognitive load in teacher content-authoring endpoints without changing behavior.
- Keeps module/material flow growth bounded so it does not reform into another single-file hotspot.

<a id="teacher-students-endpoint-split-seam"></a>
## Teacher students endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_students.py` as a compatibility facade for student roster endpoints.
- Move student identity handlers into:
  - `services/classhub/hub/views/teacher_parts/roster_students_identity.py`
  - (`teach_student_return_code`, `teach_rename_student`)
- Move student lifecycle handlers into:
  - `services/classhub/hub/views/teacher_parts/roster_students_lifecycle.py`
  - (`teach_merge_students`, `teach_delete_student_data`)
- Preserve route wiring/import contracts by exporting unchanged endpoint names via the facade module.
- Update guard contracts:
  - move function budget entries for merge/delete to `roster_students_lifecycle.py` in `scripts/view_function_budgets.json`
  - add hotspot budgets for student facade + split modules in `scripts/check_teacher_admin_hotspot_budgets.py`

**Why this remains active:**
- Reduces cognitive load in student roster maintenance endpoints without changing behavior.
- Keeps student merge/delete complexity bounded so it does not silently re-aggregate.

<a id="teacher-invites-endpoint-split-seam"></a>
## Teacher invites endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_invites.py` as a compatibility facade for invite/export endpoints.
- Move invite-link creation/disable flows into:
  - `services/classhub/hub/views/teacher_parts/roster_invites_links.py`
- Move summary/outcomes CSV exports and enrollment-mode changes into:
  - `services/classhub/hub/views/teacher_parts/roster_invites_exports.py`
- Preserve route wiring and imports by exporting unchanged endpoint names via the facade module.
- Extend hotspot guard budgets in `scripts/check_teacher_admin_hotspot_budgets.py` for the facade and both split modules.

**Why this remains active:**
- Reduces cognitive load in invite/export endpoint logic without behavior changes.
- Prevents invite/enrollment/export complexity from silently re-forming as a single hotspot file.

<a id="teacher-support-endpoint-split-seam"></a>
## Teacher support endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_support.py` as a compatibility facade.
- Move support-signal resolution endpoints into:
  - `services/classhub/hub/views/teacher_parts/roster_support_signals.py`
  - (`teach_resolve_stuck_flag`, `teach_resolve_delete_request`)
- Move support-tag mutation endpoints into:
  - `services/classhub/hub/views/teacher_parts/roster_support_tags.py`
  - (`teach_add_support_tag`, `teach_remove_support_tag`)
- Preserve route/export names unchanged through the facade.
- Extend `scripts/check_teacher_admin_hotspot_budgets.py` with explicit budgets for the facade and both split modules.

**Why this remains active:**
- Reduces cognitive load in facilitator-support actions without changing behavior.
- Keeps support-flow complexity bounded across signals and tags so the file does not regrow as a hotspot.

<a id="teacher-org-endpoints-split-seam"></a>
## Teacher org endpoints split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_orgs.py` as a compatibility facade for superuser org endpoints.
- Move org lifecycle endpoints into:
  - `services/classhub/hub/views/teacher_parts/roster_orgs_organizations.py`
  - (`teach_create_organization`, `teach_set_organization_active`)
- Move org membership/capability endpoints into:
  - `services/classhub/hub/views/teacher_parts/roster_orgs_membership_policy.py`
  - (`teach_upsert_organization_membership`, `teach_upsert_org_role_capability`)
- Move shared parsing/upsert/superuser gate helpers into:
  - `services/classhub/hub/views/teacher_parts/roster_orgs_shared.py`
- Preserve route wiring and endpoint names via facade exports.
- Extend `scripts/check_teacher_admin_hotspot_budgets.py` with explicit budgets for facade + split modules.

**Why this remains active:**
- Reduces cognitive load in org/governance endpoints without changing behavior.
- Keeps superuser org-management growth bounded across lifecycle vs membership/policy concerns.

<a id="teacher-account-endpoints-split-seam"></a>
## Teacher account endpoints split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/auth_teacher_accounts.py` as a compatibility facade.
- Move shared account helper logic into:
  - `services/classhub/hub/views/teacher_parts/auth_teacher_accounts_shared.py`
- Move onboarding/invite endpoints into:
  - `services/classhub/hub/views/teacher_parts/auth_teacher_accounts_onboarding.py`
  - (`teach_create_teacher`, `teach_resend_teacher_invite`)
- Move account-state/password endpoints into:
  - `services/classhub/hub/views/teacher_parts/auth_teacher_accounts_controls.py`
  - (`teach_set_teacher_account_active`, `teach_set_teacher_account_superuser`, `teach_reset_teacher_account_password`)
- Preserve route wiring and endpoint names via facade exports.
- Update guard contracts:
  - move function budget mapping for `teach_create_teacher` to `auth_teacher_accounts_onboarding.py` in `scripts/view_function_budgets.json`
  - add hotspot budgets for facade + split modules in `scripts/check_teacher_admin_hotspot_budgets.py`

**Why this remains active:**
- Reduces cognitive load in superuser teacher-account management endpoints without behavior changes.
- Keeps onboarding/invite flows separated from account-control flows so they do not re-aggregate.

<a id="teacher-home-context-split-seam"></a>
## Teacher home context split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/content_home_context.py` as a compatibility facade for `teach_home` context helpers.
- Move state-reading helpers into:
  - `services/classhub/hub/views/teacher_parts/content_home_context_state.py`
- Move portal-mode helpers into:
  - `services/classhub/hub/views/teacher_parts/content_home_context_portal.py`
- Move payload/data-shaping helpers into:
  - `services/classhub/hub/views/teacher_parts/content_home_context_payloads.py`
- Keep org-admin helper imports in the facade so existing `content_home.py` imports remain unchanged.
- Extend `scripts/check_teacher_admin_hotspot_budgets.py` with explicit budgets for the facade and each split module.

**Why this remains active:**
- Reduces cognitive load in `teach_home` context assembly without changing behavior.
- Keeps portal mode, state read, and payload shaping concerns explicitly bounded so they do not regrow into a single hotspot module.

<a id="teacher-sso-endpoint-split-seam"></a>
## Teacher SSO endpoint split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/auth_sso.py` as the compatibility seam module for teacher SSO routes and test patch points.
- Keep `services/classhub/hub/views/teacher_parts/auth_sso_core.py` as a compatibility facade for shared SSO core helpers.
- Move SSO core provider/config/redirect primitives into:
  - `services/classhub/hub/views/teacher_parts/auth_sso_core_providers.py`
- Move SSO state token lifecycle helpers into:
  - `services/classhub/hub/views/teacher_parts/auth_sso_core_state.py`
- Move callback/login completion helpers into:
  - `services/classhub/hub/views/teacher_parts/auth_sso_core_callback.py`
- Move Google-specific authorize/callback orchestration into:
  - `services/classhub/hub/views/teacher_parts/auth_sso_google_flow.py`
- Preserve patchable seam symbols in `auth_sso.py` used by auth tests:
  - `_load_provider_discovery`
  - `_consume_sso_state`
  - `_google_exchange_code_for_identity`
- Extend hotspot budget contracts in `scripts/check_teacher_admin_hotspot_budgets.py` for the core split modules, Google flow module, and tighten facade budgets.

**Why this remains active:**
- Reduces cognitive load in teacher SSO endpoint code without changing route behavior.
- Keeps provider/state primitives separate from Google flow orchestration while preserving test seam stability.

<a id="teacher-landing-update-helper-seam"></a>
## Teacher landing update helper seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/views/teacher_parts/roster_landing.py::teach_update_class_landing` under the dense function threshold by extracting request parsing, redirect composition, save, and audit helpers within the module.
- Do not add a new exception in `scripts/view_function_budgets.json` for this endpoint while the logic still fits a small local helper seam.

**Why this remains active:**
- Preserves the teacher landing-page update behavior and route wiring without growing the view budget ledger.
- Keeps this endpoint inspectable and treats budget pressure as a refactor signal first.

## Teacher portal test pruning: split org-access/RBAC suite from main portal tests (2026-03-12)

**Current decision:**
- Move `TeacherOrganizationAccessTests` out of:
  - `services/classhub/hub/tests/test_teacher_admin_portal.py`
- Into a dedicated module:
  - `services/classhub/hub/tests/test_teacher_admin_portal_org_access.py`
- Keep test discovery/import behavior unchanged by using the same shared test import scaffold (`from ._shared import *`).
- Tighten hotspot budgets in `scripts/check_teacher_admin_hotspot_budgets.py`:
  - `test_teacher_admin_portal.py` reduced to `3000`
  - `test_teacher_admin_portal_org_access.py` budget `1700`

**Why this remains active:**
- Reduces single-file test maintenance load in the highest-churn teacher/admin surface.
- Creates a clear domain seam for future test slicing (org-access/RBAC policy flows vs main portal behavior).

## Teacher portal test pruning: split class-ops and teacher-account suites (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/tests/test_teacher_admin_portal.py` for non-portal anchor suites only:
  - retention setting parsing
  - data lifespan dashboard
  - teacher roster class service
- Move former `TeacherPortalTests` coverage into two focused modules:
  - `services/classhub/hub/tests/test_teacher_admin_portal_class_ops.py`
  - `services/classhub/hub/tests/test_teacher_admin_portal_teacher_accounts.py`
- Add shared setup/helper base:
  - `services/classhub/hub/tests/_teacher_admin_portal_base.py`
- Update guard contracts so coverage remains explicit:
  - `scripts/check_test_inventory_coverage.py`
  - `scripts/check_teacher_admin_hotspot_budgets.py`

**Why this remains active:**
- Reduces test-file cognitive load while preserving full domain coverage.
- Makes portal regressions easier to triage by separating class workflow failures from account/admin failures.

## Org access capability service split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/org_access_capabilities.py` as a compatibility facade for org-capability policy imports.
- Move shared constants/settings/query primitives into:
  - `services/classhub/hub/services/org_access_capabilities_shared.py`
- Move role/custom-capability override helpers into:
  - `services/classhub/hub/services/org_access_capabilities_roles.py`
- Move scoped module/class range helpers into:
  - `services/classhub/hub/services/org_access_capabilities_scope.py`
- Move decision evaluation + convenience wrappers into:
  - `services/classhub/hub/services/org_access_capabilities_policy.py`
- Extend hotspot budget contracts in `scripts/check_teacher_admin_hotspot_budgets.py` for all split modules and tighten facade budget.

**Why this remains active:**
- Reduces cognitive load in the governance-heavy org access policy surface without changing endpoint semantics.
- Keeps role/capability source loading, scope range checks, and decision orchestration separately bounded so future changes prune locally instead of regrowing one monolith.

## RBAC policy bundle normalization split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/services/rbac_policy_bundle_normalize.py` as a compatibility facade for RBAC bundle schema/export/import helpers.
- Move schema/constants/dataclass helpers into:
  - `services/classhub/hub/services/rbac_policy_bundle_schema.py`
- Move export payload shaping into:
  - `services/classhub/hub/services/rbac_policy_bundle_export.py`
- Move actor-scoped import normalization into:
  - `services/classhub/hub/services/rbac_policy_bundle_import.py`
- Keep `build_policy_export_payload`, `normalize_payload_for_actor`, `POLICY_SCHEMA_VERSION`, and `NormalizedPolicyRows` available from the facade so existing imports and apply-service type hints stay stable.
- Extend hotspot budget contracts in `scripts/check_teacher_admin_hotspot_budgets.py` for all split modules and tighten facade budget.

**Why this remains active:**
- Reduces cognitive load in RBAC policy import/export normalization without changing endpoint or management-command behavior.
- Keeps schema concerns, export shaping, and import validation bounded so future policy changes can be pruned in-place rather than regrowing a single heavy module.

## Student ops test split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/tests/test_student_ops.py` as a compatibility facade import surface.
- Move student-op test suites into focused modules:
  - `services/classhub/hub/tests/test_student_ops_join_retention.py`
  - `services/classhub/hub/tests/test_student_ops_submission_flows.py`
  - `services/classhub/hub/tests/test_student_ops_portfolio_controls.py`
- Update flow coverage contracts in `scripts/check_test_inventory_coverage.py` to track required tests/tokens in the new modules.

**Why this remains active:**
- Reduces cognitive load in the largest student test hotspot without changing class/test names or test discovery behavior.
- Keeps join/retention, submission flow, and portfolio/data-control behaviors separately bounded so future additions prune by domain instead of regrowing a single test monolith.

## Teacher org-access test split seam (2026-03-12)

**Current decision:**
- Keep `services/classhub/hub/tests/test_teacher_admin_portal_org_access.py` as a compatibility stub.
- Split the prior monolith into:
  - `services/classhub/hub/tests/test_teacher_admin_portal_org_access_boundary.py`
  - `services/classhub/hub/tests/test_teacher_admin_portal_org_access_rbac_tooling.py`
- Keep both suites with independent setup scaffolds so boundary behavior and RBAC tooling behavior can be evolved/tested independently.
- Update guard contracts in:
  - `scripts/check_teacher_admin_hotspot_budgets.py`
  - `scripts/check_test_inventory_coverage.py`

**Why this remains active:**
- Separates org-boundary/classroom-access expectations from RBAC policy tooling workflows.
- Keeps the heaviest teacher governance test surface prunable by domain so future changes do not re-aggregate into one file.

## Teacher rolling class-build flow (2026-03-18)

**Current decision:**
- Keep the existing module/material models and `POST /teach/module/<id>/add-material` endpoint as the write path for in-progress class edits.
- Let `teach_add_material` honor a safe teacher-only `return_to` path so class-page quick-add actions can reuse the existing endpoint and redirect back into the class workspace.
- Surface lightweight per-session quick-add forms directly inside the class-page module editor for the most common mid-class changes:
  - note/text block
  - lesson/resource link
  - image upload
  - default project dropbox

**Why this remains active:**
- Supports responsive, in-progress teaching without forcing teachers to leave the class page for every small adjustment.
- Avoids a backend rewrite by reusing the current material creation flow, audit events, validation, and permissions.

## Ollama remote-edge User-Agent header (2026-03-26)

**Current decision:**
- Send an explicit service `User-Agent` and `Accept: application/json` header on helper Ollama HTTP requests.
- Apply the same header set to helper chat calls and helper RAG embedding calls.

**Why this remains active:**
- Some hosted Ollama-compatible edges reject the default `Python-urllib/*` client signature with Cloudflare-style `403` access-denied responses even when the same endpoint accepts `curl`.
- Keeping the change in the helper HTTP client avoids deployment-specific proxy workarounds while preserving the existing backend interface and env contract.

## Compose-local Ollama becomes opt-in (2026-03-26)

**Current decision:**
- Remove the production `helper_web -> ollama` Compose dependency.
- Keep the bundled `ollama` service available only behind the `local-ollama` Compose profile.

**Why this remains active:**
- Prevents production deploys from starting an unused local Ollama container when helper inference is pointed at a remote Ollama-compatible endpoint.
- Preserves the existing local self-hosted Ollama workflow with an explicit profile opt-in instead of removing the service entirely.

## Helper strict-topic filter uses broader signed lesson scope (2026-03-26)

**Current decision:**
- Keep the helper topic filter in strict mode for elementary-style deployments.
- Treat a student message as in-scope when it overlaps either:
  - explicit `allowed_topics`, or
  - the broader signed lesson scope (`context`, lesson `topics`, or reference text).
- Ignore low-signal instructional words when computing overlap.

**Why this remains active:**
- Prevents valid concept questions from being blocked just because lesson `helper_allowed_topics` are written as narrow task prompts instead of vocabulary/concept labels.
- Keeps the off-topic redirect behavior while reducing false positives like lesson-relevant module/component questions.

## Helper becomes more conversational by default (2026-03-26)

**Current decision:**
- Persist helper conversation state in the browser for the current lesson/session so reloads can resume the same thread.
- Tune the tutor system prompt to treat follow-ups as part of an ongoing tutoring exchange.
- Raise helper conversation defaults to keep more short-turn context before compaction.

**Why this remains active:**
- The backend already supported `conversation_id` + cached memory, but the browser experience still felt like isolated single-turn asks after reload/navigation.
- Small memory-budget increases plus browser-side restoration improve continuity without changing the helper’s privacy boundaries or turning it into an unrestricted long-term chat log.

## Helper strict-topic filter honors terse follow-ups in thread context (2026-03-26)

**Current decision:**
- Keep the strict topic filter enabled.
- When a student sends a short context-dependent follow-up (for example `There isn't`, `I don't know`, `Yes`) and the helper already has thread history for the lesson, evaluate topic scope against the recent thread context instead of the reply in isolation.

**Why this remains active:**
- Prevents valid tutoring exchanges from breaking after the first turn just because the latest student reply is too short to overlap with lesson topic metadata on its own.
- Limits the relaxation to context-dependent follow-ups so the helper still redirects genuine topic switches.

## Helper exposes Ollama context-window cap for remote GPU deploys (2026-03-26)

**Current decision:**
- Add `OLLAMA_NUM_CTX` as an optional helper setting and pass it through to Ollama `options.num_ctx`.
- Keep the default at `0` so existing local deployments continue using the model default unless operators opt in.

**Why this remains active:**
- Some remote GPU Ollama deployments advertise very large default context windows that are unnecessary for short tutoring prompts and can cause `/api/chat` to stall even when local `ollama run` works.
- Exposing the knob in env/YAML lets operators stabilize inference and smoke checks without patching model files or hard-coding a global context size into the app.

## Remote Ollama should prefer host-managed Tailscale Serve (2026-03-26)

**Current decision:**
- Keep Tailscale out of the default Compose stack.
- For private remote GPU inference, run Tailscale on the hosts and publish Ollama from the GPU node with `tailscale serve`.
- Point `OLLAMA_BASE_URL` and `HELPER_RAG_EMBED_BASE_URL` at the GPU node's MagicDNS HTTPS URL.

**Why this remains active:**
- Preserves the current least-privilege Compose posture instead of introducing a privileged VPN sidecar with `/dev/net/tun` or `NET_ADMIN`.
- Avoids public edge timeouts and proxy incompatibilities when `helper_web` talks to a remote Ollama-compatible backend.
- Gives operators one stable private URL that is usable in browser-based checks, smoke scripts, and helper env configuration.

## Container image scanning + immutable-ready pin policy (2026-04-04)

**Current decision:**
- Keep Compose runtime images pinned by exact version tag today, with digest pinning deferred to a later operator-ready pass.
- Extend `scripts/check_no_latest_tags.py` from a `:latest` ban into a stricter Compose image pin policy:
  - runtime image refs must be explicit,
  - `:latest` is banned,
  - floating runtime tags are banned,
  - exact version tags or digests are required.
- Add Trivy image scanning for the built Class Hub and Homework Helper images in `.github/workflows/security.yml`.
- Record the deferred digest path and operator expectations in [IMAGE_PINNING_POLICY.md](IMAGE_PINNING_POLICY.md).

**Why this remains active:**
- Raises supply-chain visibility immediately without forcing a risky all-digest migration in one pass.
- Keeps the runtime image policy machine-checkable in lint/CI so pin drift does not quietly return.
- Makes the deferred work explicit instead of leaving mutability as an undocumented accident.

## Local CPU Ollama becomes the default deploy/test helper path (2026-04-06)

**Current decision:**
- Default local and day-1 domain deploy flows to the bundled CPU-local Ollama service when `LLM_BASE_URL` points at the Compose-local endpoint.
- Auto-enable the `local-ollama` Compose profile in the guided deploy/smoke scripts and auto-pull the configured model before helper checks.
- Treat remote/private helper validation as advisory by default in doctor/deploy smoke paths, so private tailnet and remote-provider readiness reports pass/fail without blocking the rest of the LMS stack.

**Why this remains active:**
- Keeps the default deployment path self-contained and testable on ordinary CPU hosts.
- Avoids the previous failure mode where local deploys selected Ollama in env but forgot the Compose profile or model pull.
- Preserves the private remote-GPU path without making tailnet or remote-provider readiness a prerequisite for shipping or validating the core site.

## CSP acceptance-check guardrail (2026-04-04)

**Current decision:**
- Keep the repo-shipped env presets at `DJANGO_CSP_MODE=report-only` until the staged acceptance checks stay clean.
- Add `scripts/check_csp_runtime_contract.py` and wire it into lint and ops-readiness.
- Treat strict CSP canary mode as acceptable only when:
  - `script-src` is explicitly present,
  - inline script execution is not allowed,
  - any temporary inline allowance is limited to `style-src`.
- Keep report-only overrides strict so telemetry reflects the intended end state rather than a relaxed parallel policy.
- Keep release artifact expectations explicit: release ZIPs intentionally omit `compose/.env`, so the CSP runtime contract is verified against env presets or deployment env, not from `dist` alone.

**Why this remains active:**
- Creates an explicit guardrail between “we are still transitioning” and “we accidentally shipped a weak strict override.”
- Keeps the rollout path boring for operators: report-only by default, canary only with a provable script lock.
- Prevents CSP posture from regressing through ad hoc env overrides.

## Registry-backed docs truth spine (2026-04-04)

**Current decision:**
- Add a small runtime/docs registry at `docs/_registry/runtime_contracts.json` for selected shipped statuses and policy-sensitive defaults.
- Extend `scripts/check_docs_truth.py` to validate:
  - registry-backed status notes in canonical docs,
  - feature-maturity rows for selected high-signal capabilities,
  - stale contradictory phrases in docs and env examples.
- Keep the human-facing explanation in [DOCS_TRUTH_MECHANISM.md](DOCS_TRUTH_MECHANISM.md).
- Reuse `scripts/security_posture_snapshot.py` in `scripts/ops_readiness_check.sh` for a concise operator-facing readout.

**Why this remains active:**
- Reduces docs drift without introducing a full docs build pipeline.
- Gives maintainers one bounded place to update when shipped status or repo defaults change.
- Makes existing contradictions, especially around teacher SSO and CSP rollout posture, fail fast in CI instead of lingering across docs.

## Localization finish + governance usability tranche (2026-04-11)

**Current decision:**
- Treat the next stability slice as two bounded initiatives, not a generic UX expansion:
  - localization finish for runtime-visible core flows,
  - governance usability/training hardening for staff-operated controls.
- For localization finish:
  - prioritize runtime-visible copy on join/day-of-class/helper/certificate flows over new i18n architecture work,
  - require explicit coverage decisions for supported locales (`en`, `es`, `so`, `ksw`) on shell chrome, notices, errors, button labels, export affordances, and empty states,
  - keep rendered-route regression coverage in `hub.tests.test_i18n` and `scripts/check_i18n_family_visible_contract.py` as the bounded guardrail surface,
  - record any remaining intentional gaps as a deferred-string ledger rather than leaving partial coverage implicit.
- For governance usability/training hardening:
  - freeze net-new governance primitives unless they directly reduce ambiguity in an existing staff workflow,
  - define one canonical operator persona map for org admin, lead teacher, classroom teacher, and support reviewer,
  - require short runbook guidance for the highest-risk staff actions before expanding those controls further:
    - roster reset,
    - policy changes,
    - helper remote-compute controls,
    - exports,
    - RBAC/policy changes,
  - treat backup-operator walkthrough evidence as part of governance readiness, not optional documentation polish.
- Keep the execution details in [30_DAY_STABILITY_PLAN.md](30_DAY_STABILITY_PLAN.md), with supporting operator/task docs anchored in:
  - [LOCALIZATION.md](LOCALIZATION.md)
  - [TEACHER_TOP_TASKS.md](TEACHER_TOP_TASKS.md)
  - [TURNOVER_PACKET.md](TURNOVER_PACKET.md)

**Why this remains active:**
- The repo already has multilingual scaffolding; the more likely release-visible failure is mixed-language runtime polish in core community-facing flows.
- The governance surface is now broader than the average staff member can safely use without explicit role boundaries and short runbooks.
- This keeps the next tranche focused on reliability and operational clarity instead of letting stability work drift back into feature expansion.

## Screenshot truth reset + Python 3.14 psycopg pin correction (2026-04-11)

**Current decision:**
- Treat `18-teacher-landing-editor.png` as refresh backlog, not shipped evidence, because the tracked public capture audited blank on 2026-04-11.
- Remove `18` from embedded public docs until a real recapture exists, and keep the bounded screenshot backlog focused on `18`, `20`, and `21`.
- Bump both Django services from `psycopg[binary]==3.2.1` to `psycopg[binary]==3.3.3` so pinned local installs remain reproducible on Python 3.14 without requiring system `libpq`.

**Why this remains active:**
- A blank screenshot is worse than a missing screenshot because it makes the release packet claim evidence that is not actually visible.
- The repo’s active local interpreter is Python 3.14, and the older `3.2.1` binary pin does not provide a usable binary/runtime path there.
- This keeps the fix narrow: truthful docs plus the smallest dependency correction needed for local verification.

## Screenshot audit-first refresh discipline (2026-04-11)

**Current decision:**
- Add `scripts/press_screenshot_audit.py` as the fast local truth check for the public screenshot set.
- Treat suspiciously small duplicate PNGs as evidence drift until proven otherwise, and move them back into refresh backlog instead of continuing to embed them publicly.
- Allow the bounded screenshot backlog contract to grow from 3 to 5 items when the machine audit finds additional blank assets, rather than hiding the drift to satisfy an artificial limit.

**Why this remains active:**
- Screenshot drift is easier to miss than code drift because broken PNGs can still exist at the expected path.
- A cheap audit script creates a repeatable operator check even when full browser recapture is not available in the current shell.
- Truthful backlog governance matters more than preserving an outdated smaller number.

## Unattended remote-compute evidence watch (2026-05-07)

**Current decision:**
- Add `python3 scripts/remote_compute_operator_watch.py` as the bounded unattended watcher for helper remote-compute evidence.
- Keep the watcher on the existing private control path by executing snapshot export inside `classhub_web`, rather than exposing helper internal URLs on the host network.
- Reuse the same derived aggregate/class signal summaries already shown in `/teach/data-lifespan`, and treat `attention` as a failing alert state while keeping `watch` configurable (`REMOTE_COMPUTE_FAIL_ON_WATCH=1`).
- Provide reference systemd units in `ops/systemd/classhub-remote-compute-watch.{service,timer}` plus optional webhook env hooks:
  - `REMOTE_COMPUTE_ALERT_WEBHOOK_URL`
  - `REMOTE_COMPUTE_ALERT_ON_SUCCESS`
  - `REMOTE_COMPUTE_FAIL_ON_WATCH`
- Keep artifact output under `artifacts/stability/<YYYY-MM-DD>/remote_compute_watch_<HHMMSSZ>/` with:
  - `remote_compute_operator_snapshot.json`
  - `remote_compute_operator_report.json`
  - `remote_compute_operator_summary.md`
  - `remote_compute_operator_watch.log`

**Why this remains active:**
- Closes the “broader trend/alerting signals” gap in a bounded way without pretending the repo ships a full observability platform.
- Preserves the internal-only helper topology and avoids turning alerting into a reason to publish sensitive control endpoints.
- Produces durable unattended evidence artifacts even when no human is logged into `/teach/data-lifespan`.

## Remote-compute signal thresholds + operator drill + calm teacher copy (2026-05-08)

**Current decision:**
- Treat the derived remote-compute signal levels as a small explicit contract, not as ad hoc UI wording:
  - `quiet`
  - `calm`
  - `watch`
  - `attention`
  - `unavailable`
- Keep the current thresholds bounded and test them directly in `hub.tests_services` rather than relying on prose alone.
- Change the warning-level teacher/admin summary text from `Needs attention` to `Needs operator attention`, and explicitly state that local/default helper remains available while the remote path is reviewed.
- Split the `/teach/class` helper-signals card into smaller nested partials so the class dashboard keeps its section-budget discipline while still carrying the richer remote-compute evidence.
- Add a first-pass [OPERATOR_ONBOARDING_DRILL.md](OPERATOR_ONBOARDING_DRILL.md) so a new operator can prove:
  - system doctor,
  - smoke,
  - remote-compute snapshot export,
  - retention evidence,
  - token-rotation lookup,
  - degraded-helper triage,
  without needing the original maintainer in the room.
- Add `python3 scripts/init_operator_onboarding_drill.py` so the drill creates a dated evidence pack by command instead of relying on the operator to assemble directories and markdown by hand, and allow a guarded `--append-turnover-log` mode for updating [TURNOVER_DRILL_LOG.md](TURNOVER_DRILL_LOG.md) without retyping the dated row.
- Add [CSP_STRICT_MIGRATION_PLAN.md](CSP_STRICT_MIGRATION_PLAN.md) to separate:
  - repo-shipped env posture,
  - Django fallback posture,
  - recommended current production posture,
  - strict end state.

**Why this remains active:**
- Makes remote-compute signal claims and operator actions testable, not just descriptive.
- Keeps the teacher-facing `/teach/class` surface calmer by answering state, impact, and next action before exposing lower-level counters.
- Reduces staff-turnover risk by turning common operator knowledge into a repeatable drill and a named CSP migration map.

## Admin coursepack ZIP live import (2026-05-26)

**Current decision:**
- Add a superuser-only Django admin tool on the Class changelist for importing a repo-style coursepack `.zip`.
- Keep the existing teacher `/teach/import-syllabus-source` flow as a scratch compiler that returns a downloadable ZIP and does not mutate live content.
- Make the admin import the explicit live-content path: safely extract one `course.yaml` course into `CONTENT_ROOT/courses/<slug>/`, then create modules/materials in the selected or newly-created class.
- Reuse the same coursepack-to-class importer for both the admin GUI and `import_coursepack` management command.
- Emit `admin.coursepack_zip.import` audit events with course slug, target class, extracted file count, and module/material/asset counts.
- Keep the ClassHub container root filesystem read-only while mounting `CLASSHUB_CONTENT_ROOT=/content` from `data/classhub_content`.
- Seed bundled repo coursepacks from the image into the mounted content root at container startup when they are missing, so an empty writable content volume does not hide shipped courses.

**Why this remains active:**
- Separates low-risk teacher authoring from operator-controlled live curriculum mutation.
- Gives operators a browser path for importing reviewed coursepack artifacts without shell access.
- Keeps command-line and admin imports aligned so support images, dropboxes, and lesson links behave the same way.
- Preserves the read-only-root hardening posture by making curriculum mutation explicit and isolated to one mounted data directory.
