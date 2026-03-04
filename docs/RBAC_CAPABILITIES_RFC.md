# Granular RBAC Capabilities RFC

## Summary
ClassHub currently uses organization roles (`owner`, `admin`, `teacher`, `viewer`) with coarse permissions. This RFC defines a capability-driven RBAC model that supports district-grade policy needs while preserving current behavior during rollout.

Core outcomes:
- express permissions as capabilities (verbs), not only role names,
- allow scoped access (class/module) where needed,
- keep existing role behavior stable until policies are explicitly customized.

## What to do now
1. Implement Phase 1 capability evaluator that maps existing roles to capability checks.
2. Route legacy access helpers through the evaluator.
3. Add API-safe, class-scoped capability checks for teacher actions.
4. Introduce custom role persistence only after evaluator is stable.

## Verification signal
A staff user with role `viewer` can load class data but cannot perform manage/delete actions, and a `teacher` can still perform current class operations with no regression.

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

### 3) Scope model
Phase targets:
- Phase 1: organization/class scope (module scope argument supported by evaluator contract, no custom module grants yet).
- Phase 2: explicit scoped grants for module ranges and object-specific constraints.

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

## Rollout plan

### Phase 1: Evaluator + wrappers
- keep existing helper function signatures,
- internally route to `staff_can(...capability...)`,
- add tests for parity against current behavior.

### Phase 2: Scoped grants
- add module/class scoped grants with deny-by-default overrides,
- include conflict-resolution order:
  - explicit deny > explicit allow > template role fallback.

Current implementation note:
- module-range grants are implemented with `ClassStaffModuleScopeGrant` and now support `allow` and `deny` effects.
- evaluator precedence follows: explicit deny > explicit allow > role fallback.

### Phase 3: Policy administration UX
- add admin/operator screens for custom role definitions,
- add policy simulation UI for "why was access denied?" debugging.

Current implementation note:
- operator simulation is currently available via:
  - API: `POST /api/v1/teacher/rbac/simulate`
  - command: `simulate_rbac_access`
- full in-product policy simulation UI is still pending.

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
