# Decisions (active)

This file tracks current live decisions and constraints.
Historical implementation logs and superseded decisions are archived by month in `docs/decisions/archive/`.

## Active Decisions Snapshot

- [Auth model: student access](#auth-model-student-access)
- [Service boundary: Homework Helper separate service](#service-boundary-homework-helper-separate-service)
- [Helper engine modularization seam](#helper-engine-modularization-seam)
- [Student join service seam](#student-join-service-seam)
- [Student home and upload service seam](#student-home-and-upload-service-seam)
- [Teacher shared helpers split seam](#teacher-shared-helpers-split-seam)
- [Teacher roster code/reorder helper seam](#teacher-roster-codereorder-helper-seam)
- [Shared zip export helper seam](#shared-zip-export-helper-seam)
- [Routing mode: local vs domain Caddy configs](#routing-mode-local-vs-domain-caddy-configs)
- [Documentation as first-class product surface](#documentation-as-first-class-product-surface)
- [Docs Mermaid readability defaults](#docs-mermaid-readability-defaults)
- [Secret handling: env-only secret sources](#secret-handling-env-only-secret-sources)
- [Operator profile white-labeling](#operator-profile-white-labeling)
- [Compose env dollar escaping](#compose-env-dollar-escaping)
- [Request safety and helper access posture](#request-safety-and-helper-access-posture)
- [Observability and retention boundaries](#observability-and-retention-boundaries)
- [Deployment guardrails](#deployment-guardrails)
- [CI speed and signal quality](#ci-speed-and-signal-quality)
- [Non-root Django runtime containers](#non-root-django-runtime-containers)
- [Compose least-privilege flags](#compose-least-privilege-flags)
- [Pinned infrastructure images + latest-tag CI guard](#pinned-infrastructure-images--latest-tag-ci-guard)
- [CSP rollout modes](#csp-rollout-modes)
- [CSP strict flip hold (2026-02-24 to 2026-03-02)](#csp-strict-flip-hold-2026-02-24-to-2026-03-02)
- [Glass theme static assets](#glass-theme-static-assets)
- [Helper widget static assets](#helper-widget-static-assets)
- [Helper widget error transparency](#helper-widget-error-transparency)
- [Helper conversation memory](#helper-conversation-memory)
- [Helper conversation compaction + class reset control](#helper-conversation-compaction--class-reset-control)
- [Coursepack validation gate](#coursepack-validation-gate)
- [Redirect target validation](#redirect-target-validation)
- [Lesson file path containment](#lesson-file-path-containment)
- [Error-response redaction](#error-response-redaction)
- [Teacher authoring templates](#teacher-authoring-templates)
- [Teacher UI comfort mode](#teacher-ui-comfort-mode)
- [Helper scope signing](#helper-scope-signing)
- [Helper event ingestion boundary](#helper-event-ingestion-boundary)
- [Edge block for internal endpoints](#edge-block-for-internal-endpoints)
- [Helper grounding for Piper hardware](#helper-grounding-for-piper-hardware)
- [Helper lesson citations](#helper-lesson-citations)
- [Production transport hardening](#production-transport-hardening)
- [Content parse caching](#content-parse-caching)
- [Admin access 2FA](#admin-access-2fa)
- [Teacher onboarding invites + 2FA](#teacher-onboarding-invites-and-2fa)
- [Teacher route 2FA enforcement](#teacher-route-2fa-enforcement)
- [Staff auth POST throttling](#staff-auth-post-throttling)
- [Lesson asset delivery hardening](#lesson-asset-delivery-hardening)
- [Optional separate asset origin](#optional-separate-asset-origin)
- [Upload content validation](#upload-content-validation)
- [Deployment timezone by environment](#deployment-timezone-by-environment)
- [Migration execution at deploy time](#migration-execution-at-deploy-time)
- [Teacher daily digest + closeout workflow](#teacher-daily-digest-and-closeout-workflow)
- [Student portfolio export](#student-portfolio-export)
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
- Keep `tutor.views` helper function names stable as compatibility wrappers during extraction.
- Helper endpoint tests default to the real `/helper/chat` path with `HELPER_LLM_BACKEND=mock`; fault-injection tests patch engine-level seams (`tutor.engine.backends.*`) instead of view wrappers.

**Why this remains active:**
- Reduces change risk by preserving endpoint behavior and test patch targets while creating a clean seam for future streaming/new providers.
- Makes backend retry/circuit/reference code independently testable without expanding view-layer complexity.
- Keeps tests focused on runtime behavior while reducing brittle coupling to temporary view compatibility shims.

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

## Docs Mermaid readability defaults

**Current decision:**
- Docs build now includes `docs/stylesheets/extra.css` via `extra_css` in `mkdocs.yml`.
- Mermaid blocks are rendered with horizontal overflow instead of forced shrink-to-fit so diagram text stays legible at normal browser zoom.
- Mermaid defaults are tuned in `docs/javascripts/mermaid-init.js` with `themeVariables.fontSize=22px` and `useMaxWidth=false` for common diagram types.
- Mermaid SVG output now has a large minimum width in `docs/stylesheets/extra.css` (`min-width: 1200px`, reduced to `960px` on narrower viewports) so diagrams scale up first and use horizontal scroll when needed.
- Mermaid init now catches render promise failures and logs structured parse/render diagnostics to the console (page path + error payload) to avoid opaque unhandled-promise errors.
- Docs layout now widens Material's default grid limit (`.md-grid`) on desktop (`min-width: 60em`) to `max-width: min(96vw, 120rem)` so wiki pages use window width more effectively.

**Why this remains active:**
- Prevents operational and architecture diagrams from becoming unreadable on standard laptop displays.
- Keeps mobile behavior usable by allowing horizontal scroll on large diagrams instead of shrinking text.

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
- Student event prune supports optional CSV snapshot export before deletion (`prune_student_events --export-csv <path>`).
- File-backed upload models use delete/replacement cleanup signals to prevent orphan file accumulation.
- Orphan file scavenger is available for legacy cleanup (`scavenge_orphan_uploads`, report-first).

**Why this remains active:**
- Preserves incident traceability and accountability.
- Keeps privacy boundaries explicit by storing metadata rather than raw helper prompt/file content in event logs.
- Supports audit handoff and offline review before destructive retention actions.
- Keeps upload storage bounded and predictable after roster resets, asset/video deletes, and file replacements.

## Deployment guardrails

**Current decision:**
- Deploy path uses migration gate + smoke checks + deterministic compose invocation.
- Caddy mount source must match the expected compose config file.
- Deploy script explicitly reloads Caddy config from `/etc/caddy/Caddyfile` before smoke checks.
- Domain-template Caddy CEL expressions must use unquoted `{env.*}` placeholders inside `expression` matchers.
- `scripts/system_doctor.sh` is the canonical one-command stack diagnostic.
- Golden-path smoke can auto-provision fixtures via `scripts/golden_path_smoke.sh`.
- Class Hub static assets are collected during image build; runtime migrations stay disabled in production (`RUN_MIGRATIONS_ON_START=0`) while deploy scripts run explicit migrations.
- Edge health remains `/healthz` and upstream app health is exposed at `/upstream-healthz` for monitoring clarity.
- Smoke checks default to `http://localhost` when `CADDYFILE_TEMPLATE=Caddyfile.local`, regardless of placeholder `SMOKE_BASE_URL` values in env examples.
- CI doctor smoke uses `HELPER_LLM_BACKEND=mock` to keep `/helper/chat` deterministic without runtime model pull dependencies.
- Golden smoke issues a server-side staff session key for `/teach` checks so admin-login form changes (OTP/superuser prompts) do not create false negatives.
- `deploy_with_smoke.sh` now auto-retries with golden smoke when strict smoke fails specifically due stale `SMOKE_CLASS_CODE` (`/join` -> `invalid_code`).
- `smoke_check.sh` now emits an explicit stale-code diagnostic for `/join invalid_code` failures, with remediation guidance.
- `smoke_check.sh` now retries `/helper/chat` for transient backend startup failures (`502` + `ollama_error`) before failing deploy smoke.
- Regression coverage is required for helper auth/admin hardening and backend retry/circuit behavior.

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
- CI now writes concise human-readable summaries to `$GITHUB_STEP_SUMMARY`:
  - Ruff advisory stats in `lint`.
  - Coverage totals for `classhub-tests` and `helper-tests` in `test-suite`.
- Workflow syntax is now protected by a dedicated YAML parse gate (`.github/workflows/workflow-lint.yml`) so malformed workflow files fail fast in CI.

**Why this remains active:**
- Reduces repeated dependency download/install time across CI jobs.
- Improves review ergonomics by surfacing key quality signals without opening artifacts.
- Catches frontend wiring regressions with a lightweight check while keeping the stack Python-first.
- Prevents CSP regressions by blocking inline JS reintroduction in templates.
- Prevents CSP regressions by blocking inline CSS reintroduction in templates.
- Prevents silent CI gate loss from workflow syntax regressions.

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

## Redirect target validation

**Current decision:**
- Dynamic redirects in teacher/admin workflows must pass through a same-origin internal redirect guard.
- Redirect targets are constrained to local paths (`/teach`, `/admin`, `/material`, etc.), with scheme/host and `//` checks.
- Legacy teacher routes use the same redirect guard to avoid drift.

**Why this remains active:**
- Prevents open-redirect regressions when request-derived query values are used to build redirect URLs.
- Keeps redirect behavior explicit and reviewable for CodeQL and manual security review.

## Lesson file path containment

**Current decision:**
- Course manifest and lesson file reads are resolved through a safe path join rooted at `CONTENT_ROOT/courses`.
- Course slugs are validated before path resolution.
- Lesson `file` values from manifest metadata are treated as untrusted and must remain inside the courses root.

**Why this remains active:**
- Prevents path traversal from malformed or compromised lesson metadata.
- Preserves predictable content loading boundaries for self-hosted operators.

## Service-layer extraction scaffold

**Current decision:**
- Keep view modules as request/response adapters while moving denser classroom logic into service modules.
- Student portfolio export logic now runs via `hub/services/export_service.py`.
- Teacher digest/tracker logic now runs via `hub/services/teacher_tracker.py`, with a thin compatibility wrapper in `views/teacher_parts/shared_tracker.py`.
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

## Teacher UI comfort mode

**Current decision:**
- Teacher pages opt into a dedicated readability mode via `body.teacher-comfort`.
- Comfort mode increases card/table/form spacing, reduces motion emphasis, and removes decorative orb overlays.
- Student-facing pages keep existing visual behavior.

**Why this remains active:**
- Reduces visual fatigue during long grading/planning sessions.
- Improves scanability of dense teacher workflows without a full redesign.

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

## Automated retention maintenance

**Current decision:**
- Use `scripts/retention_maintenance.sh` as the single scheduled task entrypoint for:
  - `prune_submissions`
  - `prune_student_events` (with optional CSV export-before-delete)
  - prune helper reset JSON exports (`RETENTION_HELPER_EXPORT_DAYS`, default 180)
  - `scavenge_orphan_uploads` (report/delete/off modes)
- Optional webhook notifications report failures (and optional success) for unattended runs.
- Provide reference systemd units in `ops/systemd/` for daily execution.

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
  - explicit acknowledgement required to keep open staff-route allowlists in domain mode: `CADDY_ALLOW_PUBLIC_STAFF_ROUTES=1`
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
