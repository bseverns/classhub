# Decentralized Coursepack Registry RFC

## Status

- Closed for the current release line on `main` as of 2026-06-20.
- Local authoring/package tooling is live and should be treated as the shipped source-of-truth workflow.
- Live import/export flows are also real on `main`, including:
  - local SDK validation/build/package via `scripts/coursepack_sdk.py`
  - live coursepack import via `import_coursepack`
  - browser/admin import paths for repo-style coursepack ZIPs and teacher source files
  - downloadable scratch-built coursepack ZIP generation from teacher source uploads
- Static registry/distribution metadata is now live in a bounded static-index slice:
  - the SDK can emit checksum sidecars for built artifacts,
  - the SDK can create/update a machine-readable JSON registry index,
  - the SDK can validate/list/fetch registry entries with checksum + byte-size verification,
  - index entries support relative artifact URLs so the same index can be hosted from Git-backed static files or object storage,
  - operators now have a concrete static publishing guide,
  - ClassHub can now import directly from a registry index with `manage.py import_coursepack_registry`,
  - superusers can now import from a registry index through `/teach` and `/admin`,
  - remote registry fetches now use explicit timeout and byte-size controls for indexes, checksum sidecars, and artifact downloads,
  - remote artifact downloads verify checksum sidecars and stream SHA-256 calculation instead of reading the full artifact into memory first,
  - registry-backed imports now emit explicit audit provenance metadata,
  - `/teach` now includes a filtered content/import audit surface for recent packaging and import operations,
  - operators can deep-link into a selected audit row and inspect stored provenance metadata without leaving `/teach`,
  - class dashboards now include shortcuts into the class-scoped audit feed.
- Remote registry service, signed discovery API, and desktop GUI authoring remain parked future work and should not be implied as active roadmap commitments without a concrete operator need.

## Closure

This RFC is implemented for the current release line. Phase 1 and the bounded Phase 2 static-index slice are complete.

Remaining items are deferred product/governance decisions, not active implementation commitments:

1. Optional signed-artifact policy if checksum-only trust proves insufficient.
2. Hosted registry service only if static file distribution creates a real bottleneck.
3. Desktop authoring app only if CLI plus browser import proves insufficient for actual educators.

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

## Current status (June 2026)

Implemented now:
- `scripts/validate_coursepack.py` validates manifest/front-matter structure.
- `scripts/coursepack_sdk.py` provides a single local authoring entry point:
  - `validate`: lint one coursepack or all coursepacks
  - `build`: validate + package a portable `.zip` artifact
  - `package`: package only (skip validation)
- `docs/COURSE_AUTHORING.md` now documents SDK usage as the primary local workflow.

Parked future work:
- Remote registry service/API for signed discovery and sync orchestration.
- Desktop GUI app for drag-drop authoring/packaging.
- District-grade signed artifact verification and trust policy management.

## Proposed phases

### Phase 1: Local Authoring SDK (live)
- Keep tooling file-first and Git-native.
- Enforce deterministic validation gates (schema, links, density flags, file boundaries).
- Produce reproducible zip artifacts for import/export workflows.

### Phase 2: Registry metadata + index

Status: bounded static-index slice is now live.

- Define a machine-readable index format:
  - slug
  - version
  - checksum
  - compatibility metadata (`ui_level`, program profile)
  - source URL
- Allow orgs to host index files in GitHub/GitLab or internal object storage.

Implemented now:
- `scripts/coursepack_sdk.py build ... --registry-index <path>` creates or updates a static registry JSON file.
- Built artifacts now emit sibling `.sha256` checksum files.
- `registry-validate`, `registry-list`, and `registry-fetch` make the index consumable rather than documentation-only.
- Relative artifact URLs let operators keep `index.json`, ZIP artifacts, and checksum files together in a static directory tree.
- `docs/COURSEPACK_REGISTRY_PUBLISHING.md` now documents the recommended static directory layout and publishing flow.
- `python manage.py import_coursepack_registry ...` now imports a verified registry artifact directly into ClassHub using the existing safe ZIP import path.
- `/teach/import-coursepack-registry` and `/admin/hub/class/import-coursepack/` now expose browser-based registry import paths for superusers.
- Remote index/checksum/artifact fetches are timeout-bounded and byte-capped.
- Remote artifact imports stream bytes to disk while calculating SHA-256, then import only after checksum and byte-size verification pass.
- Registry-backed imports now record source metadata in audit events so operators can trace index, version, artifact URL, and verification details after the fact.

### Phase 3: Optional distribution service

Park this until static index publishing has real operator usage and a proven gap.

- Add hosted discovery/sync orchestration if static indexes become insufficient:
  - signed discovery metadata,
  - trust-policy distribution,
  - registry-side version promotion channels.

### Phase 4: Educator-facing desktop app (optional)

Park this unless the CLI + browser import path proves insufficient for actual teacher authoring workflows.

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

Current implementation note:
- The registry slice satisfies checksum verification with emitted `.sha256` sidecars plus fetch-time SHA-256 and byte-size verification.
- Remote fetches are bounded by explicit timeout and maximum byte settings; artifact verification streams instead of loading the full remote payload into memory first.
- Static index validation/listing works fully offline from local files.
- HTTP(S) index/artifact consumption is optional and uses the same static JSON contract.

## Open questions

These are the only questions worth carrying forward for implementation:

- Whether district-grade deployments need signed artifacts or whether checksum-only integrity is sufficient beyond the first registry slice.
- Whether trust policy belongs only in operator settings, only in registry metadata, or in both places with operator override.
