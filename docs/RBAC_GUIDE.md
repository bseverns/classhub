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
- `CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=1`: enforce module-range grants for:
  - `submission.view`
  - `submission.delete`

Grant model:
- `ClassStaffModuleScopeGrant` rows are per class, user, capability, module-order range.
- If no grants exist for a user/class/capability, role allow still applies (backward-compatible).
- If grants exist, at least one matching active range is required.

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
- denies: `unauthenticated`, `not_staff`, `membership_required`, `no_membership_for_class_org`, `role_missing_capability`, `scoped_grant_denied`, `invalid_module_scope`, `unknown_capability`
- allows: `superuser`, `role_allows_capability`, `role_allows_capability_no_scoped_grants`, `scoped_grant_allows`, `legacy_no_membership_fallback`

Use these reason codes when triaging access issues and when writing tests.

## CI guardrails

RBAC drift guard:
- `scripts/check_rbac_endpoint_guards.py`
- statically asserts key endpoint functions include required permission helpers and avoid forbidden coarse helpers.

Flow coverage guard:
- `scripts/check_test_inventory_coverage.py`
- ensures anchor RBAC tests remain present during refactors.

## Related docs
- [ORG_BOUNDARY_EXPLAINER.md](ORG_BOUNDARY_EXPLAINER.md)
- [RBAC_CAPABILITIES_RFC.md](RBAC_CAPABILITIES_RFC.md)
- [SECURITY.md](SECURITY.md)
- [DECISIONS.md](DECISIONS.md)
