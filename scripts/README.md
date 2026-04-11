# Script Index

This directory contains operational tools, CI guardrails, and quality gates for the Class Hub stack. 

These tools are designed to be run from the repository root: `bash scripts/script_name.sh`.

Operator shortcut:
- `make smoke-full` runs golden stack smoke plus accessibility smoke against a deliberately small local helper baseline, even if `compose/.env` is pointed at a remote/private helper backend. It overrides both the canonical `LLM_*` keys and the legacy `HELPER_LLM_BACKEND` / `OLLAMA_*` keys so doctor/smoke logic cannot drift on mixed env files, and it keeps the local smoke lane bounded instead of pretending the LMS box is the serious long-term inference host.
- `make ops-readiness` runs runtime-lock + CSP rollout contract + teach-class contracts + docs/inventory/backlog guards in one command (`OPS_READINESS_PROFILE=baseline|release`, `OPS_READINESS_ENV_FILE=compose/.env`).

## Core Operations & Deployment
| Script | Intent |
|---|---|
| `deploy_with_smoke.sh` | Safely deploys the stack and runs mandatory smoke checks. Reverts if checks fail. |
| `system_doctor.sh` | Comprehensive health check evaluating containers, endpoints, and curriculum state. |
| `quickstart_stack.sh` | Guided one-command stack bootstrap (env prep, compose up, migrations, optional admin + demo + doctor). |
| `bootstrap_day1.sh` | Day-1 server provisioning tool (installs Docker, configures users, structure). |
| `migration_gate.sh` | CI/CD gate ensuring uncommitted or failed Django migrations block deployment. |
| `operator_preflight.py` | Validates deploy-time env coherence: routing mode, public host/origin settings, internal helper URLs, and feature-gated helper remote-compute blocks. |
| `validate_env_secrets.sh`| Validates `.env` secrets and operator contracts for production readiness, including private remote LLM posture, canonical-vs-legacy LLM alias consistency (`LLM_*` vs `HELPER_LLM_BACKEND` / `OLLAMA_*`), plus flagged remote-helper-compute gates (`CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED` / acknowledgement / bridge URLs). |
| `repo_hygiene_check.sh` | Ensures local artifacts (sqlite, venvs) aren't accidentally tracked before push. |

## Backups & Data Management
| Script | Intent |
|---|---|
| `backup_postgres.sh` | Dumps the Postgres database to an archive format. |
| `backup_minio.sh` | Syncs MinIO (if used) object storage. |
| `backup_uploads.sh` | Creates a tarball of user-uploaded files for safe keeping. |
| `backup_restore_rehearsal.sh`| Automated script for rehearsing and verifying disaster recovery. |
| `restore_rehearsal_evidence.sh` | Runs restore rehearsal and writes evidence artifacts (log, metrics, checksums, summary). |
| `retention_maintenance.sh` | Automates execution of data retention policies (deleting old submissions/events). |
| `retention_health_snapshot.sh` | Captures timer status, recent retention logs, and a retention dry-run in one evidence-ready report. |

## Health & CI Testing
| Script | Intent |
|---|---|
| `smoke_check.sh` | Runs fast baseline smoke checks against HTTP endpoints and LLM connectivity. |
| `golden_path_smoke.sh` | End-to-end user smoke test relying on standard pre-seeded test fixtures. |
| `a11y_smoke.sh` | Automated accessibility test leveraging Playwright to find WCAG compliance errors. |
| `kiosk_resilience_check.sh` | Runs kiosk/PWA endpoint checks and captures unstable-network upload drill outcomes in a timestamped report. |
| `telemetry_stabilization_evidence.sh` | Captures telemetry split Slice 7 evidence (parity + smoke + optional rollback drill) into timestamped artifacts. |
| `stability_release_evidence.sh` | Captures Day 0-30 stability evidence pack artifacts (guardrails, smoke, a11y, restore, kiosk, release lint + scorecard + evidence index), with optional skip flags for non-docker environments. |
| `stability_phase1_closeout.sh` | Runs one full closeout cycle for stability Phase 1 + telemetry Slice 7, enforces the runtime lock `release` profile, validates required artifacts, and writes cycle summary output. |
| `ops_readiness_check.sh` | Fast operator readiness gate (runtime lock profile + CSP rollout contract + teach-class contracts + policy-mode guard + docs/inventory/backlog truth checks + posture snapshot). |
| `security_posture_snapshot.py` | Renders a compact operator-facing snapshot of active security posture, transitional items, and critical flags from an env file. |
| `test_teacher_admin.sh`| CI gate validating teacher and admin interface functionality. |
| `run_bandit.sh` | Python security linter enforcing safe coding practices. |
| `lint_release_artifact.py` | Validates zip release packages before GH Release publishing. |

## Curriculum Engineering
| Script | Intent |
|---|---|
| `import_coursepacks.sh` | Automates the creation of classrooms from standard curriculum courses. |
| `rebuild_coursepack.sh` | Convenience wrapper to safely rebuild a class layout after markdown changes. |
| `load_demo_coursepack.sh`| Loads the standard quickstart demo into a local testing database. |
| `content_preflight.sh` | Verifies course markdown, images, and YAML formatting before import. |
| `validate_coursepack.py` | Extensive deep-linting of curriculum content structure. |
| `coursepack_sdk.py` | Single entry point for local validate/build/package coursepack workflows. |
| `new_course_scaffold.py` | Generates boilerplates for new curriculum courses. |
| `quote_lesson_frontmatter.py`| Ensures YAML frontmatter compatibility across rendering engines. |
| `generate_authoring_templates.py`| Scaffolds standard authoring template structure. |
| `generate_lesson_references.py`| Synchronizes context into the AI helper for curriculum awareness. |
| `sync_helper_references.py`| Batch-syncs helper reference markdown across course manifests with safe defaults for server ops. |
| `ingest_syllabus_md.py` | Converts external Markdown assignments into Class Hub format. |

## Architectural Budgets & Quality Gates
| Script | Intent |
|---|---|
| `check_view_size_budgets.py` | Fails CI if Django view files grow too large (enforces small, tight views). |
| `check_teacher_admin_hotspot_budgets.py` | Caps growth in governance-heavy teacher/admin/RBAC hotspot files so complexity cannot silently re-concentrate. |
| `check_view_function_budgets.py`| Fails CI if a single function exceeds line count budgets. |
| `check_compose_port_exposure.py`| Security linter ensuring Docker Compose doesn't leak internal DB ports. |
| `check_frontend_static_refs.py` | Verifies all HTML assets exist in the static tree. |
| `check_no_inline_template_css.py`| Prevents `<style>` blocks in Django templates (enforces CSS isolation). |
| `check_no_inline_template_js.py` | Prevents `<script>` logic in Django templates (enforces JS isolation). |
| `check_no_new_wildcard_view_imports.py`| Blocks `from .views import *` antipatterns. |
| `check_no_service_imports_from_views.py`| Enforces architecture dependency layout (views cannot import from each other). |
| `check_no_dynamic_service_all_exports.py`| Limits module `__all__` exports. |
| `check_csp_runtime_contract.py` | Enforces staged CSP rollout rules in env files (no inline-script overrides, style canary only with strict script lock). |
| `check_no_latest_tags.py` | Enforces explicit Compose image pinning policy: no `:latest`, no floating runtime tags, exact version tags or digests only. |
| `check_rbac_endpoint_guards.py` | Enforces capability-specific RBAC guard helpers on critical endpoints. |
| `check_teacher_endpoint_capability_map.py` | Enforces explicit capability contracts for all teacher/API-teacher routes. |
| `check_teacher_top_tasks_contract.py` | Enforces `/teach` top-task choreography wiring against `docs/TEACHER_TOP_TASKS.md` contracts. |
| `check_teach_class_template_contract.py` | Enforces `/teach/class` template decomposition contracts (root-size budget + required include section anchors). |
| `check_teach_class_section_budgets.py` | Enforces line budgets for `/teach/class` section partials and section service modules so complexity stays prunable. |
| `check_teacher_roster_service_contract.py` | Enforces `/teach/class` dashboard service decomposition contracts (`teacher_roster_class.py` orchestration + section builders in `teacher_dashboard_sections/*`). |
| `check_teacher_policy_mode_contract.py` | Enforces that policy/RBAC tools remain gated behind superuser + advanced mode semantics. |
| `check_lesson_course_slug_consistency.py` | Enforces that lesson front matter `course`/`course_slug` values match each course folder slug. |
| `check_i18n_family_visible_contract.py` | Enforces bounded localization contracts for family-visible routes (`/student` + `/teach?portal_mode=day`) across docs, tests, templates, and required Spanish/Somali msgids. |
| `check_press_capture_backlog_contract.py` | Enforces press/screenshot backlog governance contracts (bounded backlog size, ownership/target metadata, and docs linkage markers). |
| `press_screenshot_audit.py` | Inventories `press/screenshots` + `docs/images/press`, flags blank/suspicious PNGs, and writes an optional JSON audit report. |
| `check_runtime_policy_lock.py` | Validates runtime lock posture with explicit profiles: `baseline` (safe/default env contract) and `release` (strict closeout lock values). |
| `check_docs_truth.py` | Verifies high-signal docs claims (registry-backed status notes, private LLM + remote-compute topology/control docs, stale wording bans, runbook/troubleshooting operator wording, risk-register metrics, and screenshot tracker truth) stay in sync with repo state. |

## LLM / AI Helper Tooling
| Script | Intent |
|---|---|
| `eval_helper.py` | Evaluation harness testing the response quality of the AI tutor configuration. |
| `run_helper_classroom_eval.sh` | One-command classroom-realistic helper eval runner (supports authenticated student bootstrap; writes raw results + summary artifacts and optional pass-rate gate). |
| `add_helper_allowed_topics.py` | CLI tool to append safe topics to the LLM interaction guardrails. |
