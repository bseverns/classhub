# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning where practical.

## [Unreleased]

### Added
- Pseudonym-first student join flow: display name prefilled with a generated pseudonym (e.g., "Curious Otter 17"), help text encouraging nicknames over real names, and configurable name-safety validation (`CLASSHUB_NAME_SAFETY_MODE`: off/warn/strict) that flags email/phone-like display names.
- i18n scaffolding: Django internationalization enabled end-to-end with Spanish translations for join/login pages, language chooser widget (no inline JS), and `docs/LOCALIZATION.md` contributor guide.
- `/privacy` page and student-facing privacy controls (export/delete/end session).
- Cross-class media isolation for lesson assets/videos with test coverage.
- Classroom storage quota (`CLASSHUB_CLASSROOM_QUOTA_MB`) to prevent disk exhaustion.
- Headless Student API endpoints (`/api/v1/student/*`) with rate limiting + no-store headers.
- Curriculum operations documentation, import helper script, and example crontab for backups/retention.
- "Content visibility model" section in `SECURITY.md` documenting public-curriculum / private-artifact stance.
- `ops/logrotate/classhub` config to rotate cron job logs.
- Privacy flow E2E test suite (`test_privacy_flow.py`, 9 tests).
- Headless Teacher API endpoints (`/api/v1/teacher/*`) with staff auth, rate limiting, and paginated submissions.
- Teacher write API: toggle-lock, rotate-code, set-enrollment-mode via JSON POST endpoints.
- Stateless bearer token auth for student API (issued at join, `Authorization: Bearer` header on `/api/` paths).
- CodeQL workflow for Python static analysis in CI.
- API test suites: 55 tests across `test_api_tokens.py`, `test_api_student.py`, and `test_api_teacher.py`.
- `docs/API.md`: Full JSON API reference (authentication, endpoints, rate limits, error codes).
- Bandit high-confidence/high-severity SAST scan in CI.
- Student micro-check signals during class (`I can do this`, `I'm stuck`, `I taught someone`) with event capture.
- Multilingual peer-feedback sentence starters and facilitator support board with stuck-resolution actions.
- Plain-language trust notes page and join-page trust links (`What we store / never store`).
- Per-class retention presets integrated with existing prune workflows (no parallel retention system).
- Student self-serve display-name rename and policy-aware self-delete controls, plus staff deletion-request inbox.
- Staff-only support tags (controlled vocabulary; no freeform notes by default).
- Artifact-first flows: student portfolio, opt-in gallery publishing, and moderated session gallery views.
- Auto-provision class creation on teacher syllabus import.
- Organization/RBAC foundation: capability evaluator, feature-flagged module-range scoped grants, and org boundary docs.
- Endpoint-level RBAC contract tests and RBAC drift-guard script coverage in CI.
- Teacher-home RBAC tools tab for scoped grant upsert/activation and access simulation, plus a route-to-capability CI contract guard for `/teach*` and `/api/v1/teacher*`.
- CI guard scripts for workflow coverage, test inventory flow anchors, and machine-readable JSON output modes.
- Phased telemetry database split runbook for reliability-oriented service separation.
- RFC docs for asynchronous self-paced workflows and granular RBAC expansion planning.
- Coursepack Authoring SDK CLI (`scripts/coursepack_sdk.py`) for local validate/build/package workflows, plus stronger coursepack lint checks for `ui_level`/`program_profile` values and lesson markdown local-link integrity.
- Optional `HELPER_CONFIG_FILE` YAML support for Homework Helper runtime behavior (policy/rate-limit/backend/conversation/RAG/queue knobs), with explicit env-var override precedence and example config template at `compose/helper.config.example.yaml`.

### Fixed
- Student "Delete my work" (`/student/delete-work`) crashed with 500 because `StudentEvent.delete()` was called without the required `allow_retention_delete()` context manager.
- Media isolation URL matching now handles trailing slashes in teacher-entered lesson URLs.
- API heartbeat (`last_seen_at`) throttled to once per 60 seconds to prevent DB churn from polling.
- `/student` and smoke CI regressions causing 500s from template/rendering and static-manifest edge cases.
- Teacher/internal and student artifact redirect hardening against host-header/open-redirect influence.
- Syllabus ingest/export hardening for path safety (`..`, absolute zip member paths, and unsafe joins).
- Regex-driven ingest validators replaced with linear-time checks to reduce ReDoS exposure.
- Teacher import wiring regressions and stale release/auth test seams after view/module refactors.
- Local HTTP join CSRF instability by decoupling secure-cookie behavior from `DEBUG`.
- Smoke diagnostics/logging robustness (admin response excerpts, compose service-name mismatch handling, summary safety).
- Workflow-lint action resolution failure (`rhysd/actionlint`) in CI.

### Changed
- `psycopg[binary]` re-pinned to `==3.2.1` for deployment reproducibility.
- Default CSP report-only policies are now stricter (no `'unsafe-inline'`) in both services.
- Gallery behavior standardized to a two-step state model: student publish intent plus teacher moderation approval.
- Student self-delete semantics now remove student class event history (not just submissions/material responses).
- Staticfiles behavior split by environment: manifest storage for production builds, non-manifest storage for debug/test.
- Class upload quota checks now use cached accounting instead of full directory scans on each upload.
- Portfolio artifact-status checks avoid per-row storage existence calls by default (opt-in strict verification flag available).
- CI Django test execution now targets full package suites instead of narrower subsets.
- Test inventory guard moved from raw test-count thresholds to anchor-flow contract checks.
- Teacher/student view modules were refactored to satisfy view size/function budget guards while preserving behavior.
