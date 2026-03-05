# Decentralized Coursepack Registry RFC

## Summary
ClassHub should treat curriculum as versioned source code, not only LMS-uploaded artifacts.
This RFC defines a phased path:
- local authoring + lint/package SDK,
- optional shared registry distribution,
- LMS import as a deployment target, not the authoring source of truth.

## Why this aligns with ClassHub
- Supports staff turnover survivability: curriculum survives outside the LMS database.
- Supports disaster recovery: Git-hosted coursepacks can be restored onto new infrastructure.
- Supports inspectability: changes are diffable, reviewable, and reversible.
- Supports non-technical educators through guided local tooling instead of ad-hoc YAML editing.

## Current status (March 2026)

Implemented now:
- `scripts/validate_coursepack.py` validates manifest/front-matter structure.
- `scripts/coursepack_sdk.py` provides a single local authoring entry point:
  - `validate`: lint one coursepack or all coursepacks
  - `build`: validate + package a portable `.zip` artifact
  - `package`: package only (skip validation)
- `docs/COURSE_AUTHORING.md` now documents SDK usage as the primary local workflow.

Not implemented yet:
- Remote registry service/API for signed or indexed coursepack discovery.
- Desktop GUI app for drag-drop authoring/packaging.
- Semantic version and release-channel metadata schema for coursepacks.

## Proposed phases

### Phase 1: Local Authoring SDK (live)
- Keep tooling file-first and Git-native.
- Enforce deterministic validation gates (schema, links, density flags, file boundaries).
- Produce reproducible zip artifacts for import/export workflows.

### Phase 2: Registry metadata + index
- Define a machine-readable index format:
  - slug
  - version
  - checksum
  - compatibility metadata (`ui_level`, program profile)
  - source URL
- Allow orgs to host index files in GitHub/GitLab or internal object storage.

### Phase 3: Optional distribution service
- Add optional pull/sync tooling for operators:
  - fetch pinned version by checksum,
  - verify integrity before import,
  - keep audit log of imported versions.

### Phase 4: Educator-facing desktop app (optional)
- Wrap SDK commands with guided UI:
  - create/edit lesson stubs
  - run lint checks
  - build/publish artifacts
- Keep CLI parity so operators can automate in CI.

## Validation and trust requirements
- Every packaged artifact must include checksum verification.
- Validation must stay deterministic and offline-capable.
- No mandatory telemetry collection in authoring tools.
- Registry sync/import operations must remain auditable.

## Open questions
- Should coursepack versions use SemVer, date-based tags, or both?
- Should signed artifacts be required for district deployments?
- Where should trust policies live: org-level settings, registry metadata, or both?
