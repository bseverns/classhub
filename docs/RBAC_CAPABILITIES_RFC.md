# Granular RBAC Capabilities RFC

## Status

- Closed for architecture on `main` as of 2026-06-20.
- The evaluator, scoped grants, simulation tools, policy import/export, custom role persistence, and delegated approval queue foundation are all real.
- The remaining work is not core RBAC existence; it is operational polish for district-scale approval routing and higher-level administration UX.

## Closure

Treat this RFC as historical architecture rationale. Ongoing work should move under implementation docs and maturity tracking:

- keep [RBAC_GUIDE.md](RBAC_GUIDE.md) as the operator/how-to source,
- keep [FEATURE_MATURITY.md](FEATURE_MATURITY.md) as the rollout truth,
- reserve this RFC for the rationale that led to the shipped model plus the small list of remaining non-shipped polish items.

## Summary
ClassHub currently uses organization roles (`owner`, `admin`, `teacher`, `viewer`) with coarse permissions. This RFC defines a capability-driven RBAC model that supports district-grade policy needs while preserving current behavior during rollout.

Core outcomes:
- express permissions as capabilities (verbs), not only role names,
- allow scoped access (class/module) where needed,
- keep existing role behavior stable until policies are explicitly customized.

## What to do now
1. Keep role-template + scoped-grant policies stable and audited in production.
2. Keep endpoint-level RBAC guard CI checks aligned as new teacher/API routes are added.
3. Narrow remaining work to:
   - district-scale approval routing polish,
   - custom-role administration UX polish,
   - clearer operator lifecycle/runbook guidance.

## Verification signal
A staff user with role `viewer` can load class data but cannot perform manage/delete actions, and a `teacher` can still perform current class operations with no regression.

## Current implementation status (March 2026)

Implemented on `main`:
- Capability evaluator + compatibility wrappers are live.
- Endpoint checks are capability-specific across teacher and API routes.
- Org role capability templates are live via `OrganizationRoleCapability`.
- Scoped grants are live via `ClassStaffModuleScopeGrant` with `allow`/`deny` effects.
- Scoped-grant precedence is live: `deny > allow > role fallback`.
- RBAC simulation is live:
  - API: `POST /api/v1/teacher/rbac/simulate`
  - Teacher tools: `POST /teach/rbac/simulate` + bulk matrix view
  - CLI: `simulate_rbac_access`
- Policy-as-code bundle import/export is live:
  - `GET /teach/rbac/policy/export`
  - `POST /teach/rbac/policy/import`
- RBAC policy/audit ops are visible in teacher tools and audit events are emitted for grant/template changes.
- First-class custom role entities are live:
  - `OrganizationCustomRole`
  - `OrganizationCustomRoleCapability`
  - `OrganizationCustomRoleAssignment`
- Evaluator support for custom role assignments is live:
  - assigned custom-role capabilities are additive to membership-role capabilities for the same organization,
  - decision reasons include custom-role allow paths.
- Teacher RBAC tools now include custom role lifecycle actions:
  - custom role upsert
  - custom role capability upsert
  - custom role assignment upsert
- Policy-as-code import/export now carries custom role sections:
  - `custom_roles[]`
  - `custom_role_assignments[]`
- Delegated approval workflow foundation is live (feature-flagged):
  - `CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=1`
  - policy mutations queue `RbacPolicyChangeRequest` and require separate reviewer approval.

Still parked/future polish:
- Hardened district-scale approval routing (multi-step approvers, notification routing, SLA escalation).
- More polished custom-role administration UX beyond the current operator tooling surface.

## Problem statement
Current model is strong for early-stage operations but too coarse for larger institutions. It cannot express policy variants like:
- "TA can review submissions but cannot delete data",
- "Curriculum coach can edit modules 1-3 only",
- "Data steward can export audits but not modify roster."

## Non-goals (this RFC)
- replacing Django auth,
- introducing per-request policy DSLs,
- shipping a full district policy UI in Phase 1.

## Proposed architecture

### 1) Capability vocabulary
Define stable action keys:
- `class.view`
- `class.manage`
- `class.create`
- `roster.manage`
- `submission.view`
- `submission.delete`
- `policy.manage`
- `syllabus.export`

### 2) Role templates (backward compatibility baseline)
Map existing roles to capability sets:
- `owner`: full set
- `admin`: full set except ownership-only controls (future)
- `teacher`: class management + roster/submission operations
- `viewer`: read-only capabilities

This preserves current organization-role semantics while shifting checks to capability terms.

Current implementation note:
- Org-level role template overrides are active through `OrganizationRoleCapability`.

### 3) Scope model
Phase targets:
- Phase 1: organization/class scope (module scope argument supported by evaluator contract, no custom module grants yet).
- Phase 2: explicit scoped grants for module ranges and object-specific constraints.

Current implementation note:
- Scoped grants are implemented and enforceable behind `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED`.
- Scoped capabilities include:
  - `submission.view`
  - `submission.delete`
  - `roster.manage`
  - `policy.manage`

### 4) Evaluator contract
Single service entry point:
- input: user, capability, optional class/module scope
- output: allow/deny + reason metadata

All view/service permission checks should call this service (directly or via compatibility wrappers).

## Data model evolution plan

### Phase 1 (no custom-role tables required)
- evaluator + role-capability map in service layer,
- existing `OrganizationMembership.role` remains source of truth.

### Phase 2 (custom roles)
- add `Role`, `Capability`, `RoleCapability`, `ScopedGrant` tables,
- migrate role template mappings into DB-managed policy records,
- provide constrained admin UX for policy changes.

Current implementation note:
- Phase-2 custom-role persistence foundation is shipped.
- Current policy model supports additive custom role capabilities per user/org.
- Destructive migration from role templates to pure custom-role policy records remains future work.

## Remaining rollout work

### Phase 1: Evaluator + wrappers
- keep existing helper function signatures,
- internally route to `staff_can(...capability...)`,
- add tests for parity against current behavior.

Status: shipped.

### Phase 2: Scoped grants
- add module/class scoped grants with deny-by-default overrides,
- include conflict-resolution order:
  - explicit deny > explicit allow > template role fallback.

Current implementation note:
- module-range grants are implemented with `ClassStaffModuleScopeGrant` and now support `allow` and `deny` effects.
- evaluator precedence follows: explicit deny > explicit allow > role fallback.

Status: shipped.

### Phase 3: Policy administration UX
- add admin/operator screens for custom role definitions,
- add policy simulation UI for "why was access denied?" debugging.

Current implementation note:
- operator simulation is currently available via:
  - API: `POST /api/v1/teacher/rbac/simulate`
  - command: `simulate_rbac_access`
  - teacher portal single-user simulation: `POST /teach/rbac/simulate`
  - teacher portal bulk matrix simulation: `GET /teach?rbac_tools=1&rbac_bulk_class_id=<id>&rbac_bulk_capability=<capability>`

Status: simulation/policy tools are shipped; custom-role entity persistence is shipped; custom-role policy UX/automation remains future work.

## What should now be treated as done

- Capability-driven evaluator contract
- Compatibility wrappers around legacy role semantics
- Scoped allow/deny grant persistence and precedence
- RBAC simulation surfaces
- Policy-as-code import/export
- Custom role persistence model
- Delegated approval queue foundation

These should no longer be described elsewhere as hypothetical architecture.

## Risks and mitigations
- Risk: policy drift during migration.
  - Mitigation: retain legacy wrappers + parity tests.
- Risk: too many capability names.
  - Mitigation: versioned capability registry and naming conventions.
- Risk: unclear denials for staff users.
  - Mitigation: evaluator reason metadata for UI/audit logging.

## Testing plan
- Service tests:
  - superuser bypass,
  - membership-required mode,
  - role-to-capability mapping parity.
- Integration tests:
  - viewer blocked from manage endpoints,
  - teacher allowed for current manage flows,
  - export permission restricted to owner/admin.

## Security posture notes
- Keep deny-by-default behavior when org membership is required and absent.
- Never infer write permissions from read permissions.
- Preserve class boundary checks before capability checks where object ownership matters.
