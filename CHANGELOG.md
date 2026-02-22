# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning where practical.

## [Unreleased]

### Added
- CodeQL workflow for Python static analysis in CI.
- Bandit high-confidence/high-severity SAST scan in CI.

### Changed
- Default CSP report-only policies are now stricter (no `'unsafe-inline'`) in both services.
