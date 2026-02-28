# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning where practical.

## [Unreleased]

### Added
- `/privacy` page and student-facing privacy controls (export/delete/end session).
- Cross-class media isolation for lesson assets/videos with test coverage.
- Classroom storage quota (`CLASSHUB_CLASSROOM_QUOTA_MB`) to prevent disk exhaustion.
- Headless Student API endpoints (`/api/v1/student/*`) with rate limiting + no-store headers.
- Curriculum operations documentation, import helper script, and example crontab for backups/retention.
- "Content visibility model" section in `SECURITY.md` documenting public-curriculum / private-artifact stance.
- `ops/logrotate/classhub` config to rotate cron job logs.
- Privacy flow E2E test suite (`test_privacy_flow.py`, 9 tests).
- CodeQL workflow for Python static analysis in CI.
- Bandit high-confidence/high-severity SAST scan in CI.

### Fixed
- Student "Delete my work" (`/student/delete-work`) crashed with 500 because `StudentEvent.delete()` was called without the required `allow_retention_delete()` context manager.
- Media isolation URL matching now handles trailing slashes in teacher-entered lesson URLs.
- API heartbeat (`last_seen_at`) throttled to once per 60 seconds to prevent DB churn from polling.

### Changed
- `psycopg[binary]` re-pinned to `==3.2.1` for deployment reproducibility.
- Default CSP report-only policies are now stricter (no `'unsafe-inline'`) in both services.
