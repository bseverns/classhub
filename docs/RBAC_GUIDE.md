# RBAC Guide (Current Behavior)

## Summary
This page explains the RBAC model that is active in ClassHub today:
- org boundaries decide class visibility,
- capabilities decide allowed actions,
- optional scoped grants can narrow module access.

Use this as the operational reference. The RFC remains the future-looking design doc.

## What to do now
1. Choose boundary mode:
   - `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1` for strict production.
   - `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0` only during migration.
2. Verify every staff account has an active org membership with the intended role.
3. Keep `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=0` unless you need module-range limits.
4. Run RBAC drift checks in CI:
   - `python scripts/check_rbac_endpoint_guards.py`
   - `python scripts/check_teacher_endpoint_capability_map.py`
   - `python scripts/check_test_inventory_coverage.py`

## Verification signal
For one class in one org:
- `viewer` can read class/submission screens but cannot mutate policy/roster.
- `teacher` can manage policy/roster and review submissions.
- module-range grants (when enabled) block out-of-range submission actions.

## Capability model

Capability keys:
- `class.view`
- `class.manage`
- `class.create`
- `roster.manage`
- `submission.view`
- `submission.delete`
- `policy.manage`
- `syllabus.export`

Role template mapping:

| Role | class.view | class.manage | class.create | roster.manage | submission.view | submission.delete | policy.manage | syllabus.export |
|---|---|---|---|---|---|---|---|---|
| `owner` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `admin` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `teacher` | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No |
| `viewer` | Yes | No | No | No | Yes | No | No | No |

## Boundary modes and fallback

`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1`:
- no active membership -> deny staff class access/actions.

`REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`:
- no active membership -> legacy fallback (broad class access and core manage capabilities).
- keep this mode temporary; it is less strict.

Superuser behavior:
- superusers bypass org/capability checks.

## Scoped module grants

Feature flag:
- `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=0` (default): role template behavior only.
- `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1`: enforce scoped grants for:
  - `submission.view`
  - `submission.delete`
  - `roster.manage` (class-wide via range `0-0`)
  - `policy.manage` (class-wide via range `0-0`)

Grant model:
- `ClassStaffModuleScopeGrant` rows are per class, user, capability, module-order range.
- Each row has an `effect`:
  - `allow`: grants access in the range.
  - `deny`: blocks access in the range.
- If no grants exist for a user/class/capability, role allow still applies (backward-compatible).
- If grants exist, precedence is:
  - explicit deny > explicit allow > role fallback
- Overlapping allow+deny ranges deny access where overlap exists.

## Endpoint guard policy

Use the narrowest helper that matches intent:

| Intent | Required helper |
|---|---|
| Read class page | `staff_can_access_classroom` |
| Class-level write (legacy broad) | `staff_can_manage_classroom` |
| Roster changes (rename, merge, delete student data, cert download) | `staff_can_manage_roster` |
| Policy/config changes (lock, rotate code, retention, landing settings) | `staff_can_manage_policy` |
| Submission/gallery read | `staff_can_view_submissions` |
| Submission/gallery destructive moderation | `staff_can_delete_submissions` |
| Global syllabus export | `staff_can_export_syllabi` |

Current hardening rule:
- avoid using coarse manage checks for policy/roster-specific write endpoints when dedicated helpers exist.

## Decision reasons (deny/allow debugging)

`evaluate_staff_capability(...)` returns machine-readable reasons, including:
- denies: `unauthenticated`, `not_staff`, `membership_required`, `no_membership_for_class_org`, `role_missing_capability`, `scoped_grant_denied`, `scoped_grant_explicit_deny`, `invalid_module_scope`, `unknown_capability`
- allows: `superuser`, `role_allows_capability`, `role_allows_capability_no_scoped_grants`, `scoped_grant_allows`, `legacy_no_membership_fallback`

Use these reason codes when triaging access issues and when writing tests.

## Simulation tools

Teacher API simulation endpoint:
- `POST /api/v1/teacher/rbac/simulate`
- Requires staff auth + OTP and org-level export capability.
- Returns a machine-readable decision payload for a target staff user and scope.

CLI simulation command:
- `python services/classhub/manage.py simulate_rbac_access --username <staff_username> --capability submission.view --class-id <id> --module-id <id> --json`
- Useful for operational triage and policy debugging in shell-first workflows.

Teacher portal simulation and grant management:
- `POST /teach/rbac/simulate`
- `POST /teach/rbac/module-scope-grant/upsert`
- `POST /teach/rbac/module-scope-grant/set-active`
- `GET /teach/rbac/policy/export`
- `POST /teach/rbac/policy/import`
- These portal actions are available only to staff with syllabus-export capability and are audited for operator traceability.

Teacher portal bulk simulation matrix:
- `GET /teach?rbac_tools=1&rbac_bulk_class_id=<id>&rbac_bulk_capability=<capability>[&rbac_bulk_module_id=<id>]`
- Returns a read-only per-staff allow/deny table with reason/role metadata for the selected class scope.
- Matrix rows are constrained to staff in the selected class org boundary (plus superusers) and capped at 250 rows.

## Policy change audit coverage

Scoped module grant create/update/delete actions in Django admin emit audit events:
- `rbac.scope_grant.create`
- `rbac.scope_grant.update`
- `rbac.scope_grant.delete`

Teacher portal RBAC tools emit:
- `rbac.scope_grant.portal_upsert`
- `rbac.scope_grant.portal_set_active`
- `rbac.simulate.portal`
- `organization.role_capability.upsert`
- `organization.membership.upsert`

These records include capability, effect, module range, and target user/class identifiers.

Teacher RBAC audit operations panel:
- `GET /teach?rbac_tools=1&rbac_audit_action=<prefix>&rbac_audit_class_id=<id>&rbac_audit_limit=<n>`
- shows recent RBAC/org-policy audit events scoped to accessible classes/orgs.

Policy-as-code format:
- schema version: `classhub.rbac_policy.v1`
- sections:
  - `organizations[]` with `name` + `role_capabilities[]`
  - `scoped_grants[]` with `class_join_code`, `username`, `capability`, `effect`, range, and active flag
- class-wide scoped capabilities (`roster.manage`, `policy.manage`) must use `module_order_start=0` and `module_order_end=0`.

## CI guardrails

RBAC drift guard:
- `scripts/check_rbac_endpoint_guards.py`
- statically asserts key endpoint functions include required permission helpers and avoid forbidden coarse helpers.

Teacher route-map capability guard:
- `scripts/check_teacher_endpoint_capability_map.py`
- enforces explicit capability contracts for every `/teach*` and `/api/v1/teacher*` route and checks mapped views still contain expected guard tokens.

Flow coverage guard:
- `scripts/check_test_inventory_coverage.py`
- ensures anchor RBAC tests remain present during refactors.

## Related docs
- [ORG_BOUNDARY_EXPLAINER.md](ORG_BOUNDARY_EXPLAINER.md)
- [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md)
- [SECURITY.md](SECURITY.md)
- [DECISIONS.md](DECISIONS.md)
