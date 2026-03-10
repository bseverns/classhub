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
- [Syllabus import class provisioning](#syllabus-import-class-provisioning)
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
- [Teacher roster code/reorder helper seam](#teacher-roster-codereorder-helper-seam)
- [Shared zip export helper seam](#shared-zip-export-helper-seam)
- [Routing mode: local vs domain Caddy configs](#routing-mode-local-vs-domain-caddy-configs)
- [Cookie secure flags follow transport mode](#cookie-secure-flags-follow-transport-mode)
- [Authoring template lesson slug convention](#authoring-template-lesson-slug-convention)
- [Documentation as first-class product surface](#documentation-as-first-class-product-surface)
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
- [CSP rollout modes](#csp-rollout-modes)
- [CSP strict flip hold (2026-02-24 to 2026-03-02)](#csp-strict-flip-hold-2026-02-24-to-2026-03-02)
- [Glass theme static assets](#glass-theme-static-assets)
- [Helper widget static assets](#helper-widget-static-assets)
- [Helper widget error transparency](#helper-widget-error-transparency)
- [Helper conversation memory](#helper-conversation-memory)
- [Helper conversation compaction + class reset control](#helper-conversation-compaction-and-class-reset-control)
- [Coursepack validation gate](#coursepack-validation-gate)
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
- [Helper scope signing](#helper-scope-signing)
- [Helper event ingestion boundary](#helper-event-ingestion-boundary)
- [Edge block for internal endpoints](#edge-block-for-internal-endpoints)
- [Helper grounding for Piper hardware](#helper-grounding-for-piper-hardware)
- [Helper lesson citations](#helper-lesson-citations)
- [Helper local curriculum RAG](#helper-local-curriculum-rag)
- [Helper YAML config layering](#helper-yaml-config-layering)
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

## Syllabus import class provisioning

**Current decision:**
- Teacher portal syllabus imports (`/teach/import-syllabus-source`) now provision a class automatically.
- The class is created in the uploader’s default organization scope and populated from the imported course pack.
- Non-superuser staff uploaders receive an active `ClassStaffAssignment` on the newly created class.
- If staff cannot create classes under current org policy, syllabus import returns an error instead of creating content without a class.
- Zip syllabus imports now map lesson-support images by filename prefix (`01-...`, `02-...`) to matching sessions:
  - images are written into course content under `lesson_support_images/`,
  - generated lesson front matter includes `support_images`,
  - coursepack import creates lesson-tagged `LessonAsset` rows + module links to those assets.

**Why this remains active:**
- Keeps teacher workflow one-step: upload source, then immediately have a runnable class.
- Reduces setup drift where course content exists on disk but no class is attached for student use.
- Preserves supportive visual context from teacher-authored zip bundles without manual per-lesson asset re-upload.

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
- Mermaid blocks are rendered with horizontal overflow instead of forced shrink-to-fit so diagram text stays legible at normal browser zoom.
- Mermaid defaults are tuned in `docs/javascripts/mermaid-init.js` with `themeVariables.fontSize=22px` and `useMaxWidth=false` for common diagram types.
- Mermaid SVG output now has a large minimum width in `docs/stylesheets/extra.css` (`min-width: 1200px`, reduced to `960px` on narrower viewports) so diagrams scale up first and use horizontal scroll when needed.
- Mermaid init now catches render promise failures and logs structured parse/render diagnostics to the console (page path + error payload) to avoid opaque unhandled-promise errors.
- Docs layout now widens Material's default grid limit (`.md-grid`) on desktop (`min-width: 60em`) to `max-width: min(96vw, 120rem)` so wiki pages use window width more effectively.

**Why this remains active:**
- Prevents operational and architecture diagrams from becoming unreadable on standard laptop displays.
- Keeps mobile behavior usable by allowing horizontal scroll on large diagrams instead of shrinking text.
- Reduces supply-chain fragility for docs rendering by avoiding runtime fetches from external script CDNs.

## Secret handling: env-only secret sources

**Current decision:**
- Secrets are injected via environment (`compose/.env` or deployment environment), never committed to git.
- `DJANGO_SECRET_KEY` is required in both services.
- Class Hub device-hint cookies are signed with a dedicated `DEVICE_HINT_SIGNING_KEY` (separate from `DJANGO_SECRET_KEY` in production).
- Mode-specific env examples (`.env.example.local`, `.env.example.domain`) stay non-sensitive and document required knobs.

**Why this remains active:**
- Prevents insecure fallback secret boot behavior.
- Reduces blast radius if one signing key leaks (device-hint cookie signatures stay independently rotatable).
- Supports basic secret hygiene for self-hosted operations.
- Keeps rotation/update workflow operationally simple.

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
  - restores Postgres into a temporary database,
  - extracts uploads/MinIO archives into a temporary workspace,
  - runs ClassHub/Helper `migrate` + `check` against the restored DB.
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
  - highlights one lesson for the current week using existing lesson release dates,
  - keeps full course lesson links available from the same page.
- Landing content is stored on `Class` (`student_landing_title`, `student_landing_message`, `student_landing_hero_url`) and managed in the existing teacher class dashboard.
- Hero URL validation allows only:
  - same-origin paths starting with `/` (for local assets), or
  - absolute `http/https` URLs.

**Why this remains active:**
- Gives young learners a clear “start here” focus without removing access to the rest of the course.
- Reuses existing scheduling primitives (`LessonRelease.available_on`) rather than adding new calendar models.
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
  - `all` (default),
  - `day`,
  - `setup`,
  - `admin` (superuser-only),
  - `policy` (superuser or RBAC-enabled staff).
- Apply mode visibility as rendering filters over existing sections/cards:
  - `day`: class-focus + digest + closeout + recent submissions.
  - `setup`: class setup, profile, import/template tools.
  - `admin`: organization/staff/operator surfaces.
  - `policy`: RBAC/policy/operator surfaces.
- Do not add new routes or new top-level workflow primitives as part of this change.

**Why this remains active:**
- Reduces first-contact cognitive load in `/teach` without removing existing capability.
- Preserves backward compatibility (`/teach` default remains full cockpit).
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
