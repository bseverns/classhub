# Script Index

This directory contains operational tools, CI guardrails, and quality gates for the Class Hub stack. 

These tools are designed to be run from the repository root: `bash scripts/script_name.sh`.

Operator shortcut:
- `make smoke-full` runs golden stack smoke (`system_doctor --smoke-mode golden`) and accessibility smoke in one command.

## Core Operations & Deployment
| Script | Intent |
|---|---|
| `deploy_with_smoke.sh` | Safely deploys the stack and runs mandatory smoke checks. Reverts if checks fail. |
| `system_doctor.sh` | Comprehensive health check evaluating containers, endpoints, and curriculum state. |
| `quickstart_stack.sh` | Guided one-command stack bootstrap (env prep, compose up, migrations, optional admin + demo + doctor). |
| `bootstrap_day1.sh` | Day-1 server provisioning tool (installs Docker, configures users, structure). |
| `migration_gate.sh` | CI/CD gate ensuring uncommitted or failed Django migrations block deployment. |
| `validate_env_secrets.sh`| Validates `.env` secrets for production readiness (catches unescaped characters). |
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
| `stability_release_evidence.sh` | Captures Day 0-30 stability evidence pack artifacts (guardrails, smoke, a11y, restore, kiosk, release lint + scorecard), with optional skip flags for non-docker environments. |
| `stability_phase1_closeout.sh` | Runs one full closeout cycle for stability Phase 1 + telemetry Slice 7, enforces the runtime lock `release` profile, validates required artifacts, and writes cycle summary output. |
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
| `ingest_syllabus_md.py` | Converts external Markdown assignments into Class Hub format. |

## Architectural Budgets & Quality Gates
| Script | Intent |
|---|---|
| `check_view_size_budgets.py` | Fails CI if Django view files grow too large (enforces small, tight views). |
| `check_view_function_budgets.py`| Fails CI if a single function exceeds line count budgets. |
| `check_compose_port_exposure.py`| Security linter ensuring Docker Compose doesn't leak internal DB ports. |
| `check_frontend_static_refs.py` | Verifies all HTML assets exist in the static tree. |
| `check_no_inline_template_css.py`| Prevents `<style>` blocks in Django templates (enforces CSS isolation). |
| `check_no_inline_template_js.py` | Prevents `<script>` logic in Django templates (enforces JS isolation). |
| `check_no_new_wildcard_view_imports.py`| Blocks `from .views import *` antipatterns. |
| `check_no_service_imports_from_views.py`| Enforces architecture dependency layout (views cannot import from each other). |
| `check_no_dynamic_service_all_exports.py`| Limits module `__all__` exports. |
| `check_no_latest_tags.py` | Enforces explicit version pinning in Dockerfiles and Compose files. |
| `check_rbac_endpoint_guards.py` | Enforces capability-specific RBAC guard helpers on critical endpoints. |
| `check_teacher_endpoint_capability_map.py` | Enforces explicit capability contracts for all teacher/API-teacher routes. |
| `check_teacher_top_tasks_contract.py` | Enforces `/teach` top-task choreography wiring against `docs/TEACHER_TOP_TASKS.md` contracts. |
| `check_teach_class_template_contract.py` | Enforces `/teach/class` template decomposition contracts (root-size budget + required include section anchors). |
| `check_teach_class_section_budgets.py` | Enforces line budgets for `/teach/class` section partials and section service modules so complexity stays prunable. |
| `check_teacher_roster_service_contract.py` | Enforces `/teach/class` dashboard service decomposition contracts (`teacher_roster_class.py` orchestration + section builders in `teacher_dashboard_sections/*`). |
| `check_press_capture_backlog_contract.py` | Enforces press/screenshot backlog governance contracts (bounded backlog size, ownership/target metadata, and docs linkage markers). |
| `check_runtime_policy_lock.py` | Validates runtime lock posture with explicit profiles: `baseline` (safe/default env contract) and `release` (strict closeout lock values). |
| `check_docs_truth.py` | Verifies high-signal docs claims (risk-register metrics + screenshot tracker truth) stay in sync with repo state. |

## LLM / AI Helper Tooling
| Script | Intent |
|---|---|
| `eval_helper.py` | Evaluation harness testing the response quality of the AI tutor configuration. |
| `add_helper_allowed_topics.py` | CLI tool to append safe topics to the LLM interaction guardrails. |
