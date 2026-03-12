"""Capability policy evaluator for organization-scoped staff access."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db.models import F, QuerySet

from ..models import (
    Class,
    ClassStaffModuleScopeGrant,
    Module,
    Organization,
    OrganizationCustomRoleAssignment,
    OrganizationRoleCapability,
    OrganizationMembership,
)

CAP_CLASS_VIEW = "class.view"
CAP_CLASS_MANAGE = "class.manage"
CAP_CLASS_CREATE = "class.create"
CAP_ROSTER_MANAGE = "roster.manage"
CAP_SUBMISSION_VIEW = "submission.view"
CAP_SUBMISSION_DELETE = "submission.delete"
CAP_POLICY_MANAGE = "policy.manage"
CAP_SYLLABUS_EXPORT = "syllabus.export"

_KNOWN_CAPABILITIES = frozenset(
    {
        CAP_CLASS_VIEW,
        CAP_CLASS_MANAGE,
        CAP_CLASS_CREATE,
        CAP_ROSTER_MANAGE,
        CAP_SUBMISSION_VIEW,
        CAP_SUBMISSION_DELETE,
        CAP_POLICY_MANAGE,
        CAP_SYLLABUS_EXPORT,
    }
)

_ROLE_PRECEDENCE = (
    OrganizationMembership.ROLE_OWNER,
    OrganizationMembership.ROLE_ADMIN,
    OrganizationMembership.ROLE_TEACHER,
    OrganizationMembership.ROLE_VIEWER,
)

_DEFAULT_ROLE_CAPABILITIES = {
    OrganizationMembership.ROLE_OWNER: frozenset(_KNOWN_CAPABILITIES),
    OrganizationMembership.ROLE_ADMIN: frozenset(_KNOWN_CAPABILITIES),
    OrganizationMembership.ROLE_TEACHER: frozenset(
        {
            CAP_CLASS_VIEW,
            CAP_CLASS_MANAGE,
            CAP_CLASS_CREATE,
            CAP_ROSTER_MANAGE,
            CAP_SUBMISSION_VIEW,
            CAP_SUBMISSION_DELETE,
            CAP_POLICY_MANAGE,
        }
    ),
    OrganizationMembership.ROLE_VIEWER: frozenset(
        {
            CAP_CLASS_VIEW,
            CAP_SUBMISSION_VIEW,
        }
    ),
}

_LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS = frozenset(
    {
        CAP_CLASS_VIEW,
        CAP_CLASS_MANAGE,
        CAP_CLASS_CREATE,
        CAP_ROSTER_MANAGE,
        CAP_SUBMISSION_VIEW,
        CAP_SUBMISSION_DELETE,
        CAP_POLICY_MANAGE,
    }
)
_MODULE_RANGE_GRANT_CAPABILITIES = frozenset(
    {
        CAP_SUBMISSION_VIEW,
        CAP_SUBMISSION_DELETE,
    }
)
_CLASS_SCOPE_GRANT_CAPABILITIES = frozenset(
    {
        CAP_ROSTER_MANAGE,
        CAP_POLICY_MANAGE,
    }
)
_SCOPED_GRANT_CAPABILITIES = _MODULE_RANGE_GRANT_CAPABILITIES | _CLASS_SCOPE_GRANT_CAPABILITIES


@dataclass(frozen=True)
class StaffCapabilityDecision:
    allowed: bool
    capability: str
    reason: str
    role: str = ""
    organization_id: int | None = None
    classroom_id: int | None = None
    module_id: int | None = None


def require_org_membership_for_staff() -> bool:
    return bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False))


def scoped_module_grants_enabled() -> bool:
    return bool(getattr(settings, "CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED", False))


def active_staff_memberships_queryset(user) -> QuerySet[OrganizationMembership]:
    if not getattr(user, "is_authenticated", False):
        return OrganizationMembership.objects.none()
    if not getattr(user, "is_staff", False):
        return OrganizationMembership.objects.none()
    return OrganizationMembership.objects.filter(
        user=user,
        is_active=True,
        organization__is_active=True,
    )


def _module_scope_is_valid(*, classroom: Class | None, module_id: int | None) -> bool:
    if module_id is None:
        return True
    try:
        parsed_module_id = int(module_id)
    except Exception:
        return False
    if parsed_module_id <= 0:
        return False
    if classroom is None:
        return False
    return Module.objects.filter(id=parsed_module_id, classroom_id=classroom.id).exists()


def _module_scope_order(*, classroom: Class, module_id: int) -> int | None:
    try:
        parsed_module_id = int(module_id)
    except Exception:
        return None
    if parsed_module_id <= 0:
        return None
    row = (
        Module.objects.filter(
            id=parsed_module_id,
            classroom_id=classroom.id,
        )
        .only("order_index")
        .first()
    )
    if row is None:
        return None
    return int(row.order_index)


def _org_role_capability_overrides(organization_ids: set[int]) -> dict[int, dict[str, frozenset[str]]]:
    if not organization_ids:
        return {}
    rows = OrganizationRoleCapability.objects.filter(
        organization_id__in=organization_ids,
        is_active=True,
    ).values_list("organization_id", "role", "capability")
    by_org: dict[int, dict[str, set[str]]] = {}
    for organization_id, role, capability in rows:
        org_bucket = by_org.setdefault(int(organization_id), {})
        org_bucket.setdefault(str(role), set()).add(str(capability))
    return {
        org_id: {role: frozenset(caps) for role, caps in role_map.items()}
        for org_id, role_map in by_org.items()
    }


def _membership_role_capabilities(
    *,
    role: str,
    organization_id: int,
    overrides: dict[int, dict[str, frozenset[str]]],
) -> frozenset[str]:
    org_overrides = overrides.get(int(organization_id), {})
    if role in org_overrides:
        return org_overrides[role]
    return _DEFAULT_ROLE_CAPABILITIES.get(role, frozenset())


def _custom_role_capability_overrides(
    user,
    *,
    organization_ids: set[int],
) -> dict[int, frozenset[str]]:
    if not organization_ids:
        return {}
    rows = (
        OrganizationCustomRoleAssignment.objects.filter(
            user=user,
            organization_id__in=organization_ids,
            is_active=True,
            organization__is_active=True,
            role__is_active=True,
            role__capabilities__is_active=True,
        )
        .filter(role__organization_id=F("organization_id"))
        .values_list("organization_id", "role__capabilities__capability")
    )
    by_org: dict[int, set[str]] = {}
    for organization_id, capability in rows:
        by_org.setdefault(int(organization_id), set()).add(str(capability))
    return {org_id: frozenset(caps) for org_id, caps in by_org.items()}


def _highest_role_with_capability(
    *,
    memberships: list[dict[str, int | str]],
    capability: str,
    overrides: dict[int, dict[str, frozenset[str]]],
) -> str:
    for role in _ROLE_PRECEDENCE:
        for row in memberships:
            if str(row.get("role")) != role:
                continue
            organization_id = int(row.get("organization_id") or 0)
            if capability in _membership_role_capabilities(
                role=role,
                organization_id=organization_id,
                overrides=overrides,
            ):
                return role
    return ""


def _highest_role_with_custom_capability(
    *,
    memberships: list[dict[str, int | str]],
    capability: str,
    custom_overrides: dict[int, frozenset[str]],
) -> str:
    for role in _ROLE_PRECEDENCE:
        for row in memberships:
            if str(row.get("role")) != role:
                continue
            organization_id = int(row.get("organization_id") or 0)
            custom_caps = custom_overrides.get(organization_id, frozenset())
            if capability in custom_caps:
                return role
    return ""


def evaluate_staff_capability(
    user,
    capability: str,
    *,
    classroom: Class | None = None,
    module_id: int | None = None,
) -> StaffCapabilityDecision:
    normalized_capability = (capability or "").strip().lower()
    if classroom is None:
        classroom_id = None
    else:
        try:
            classroom_id = int(classroom.id)
        except Exception:
            classroom_id = None
    if module_id is None:
        module_scope_id = None
    else:
        try:
            module_scope_id = int(module_id)
        except Exception:
            module_scope_id = -1

    if normalized_capability not in _KNOWN_CAPABILITIES:
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="unknown_capability",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if not getattr(user, "is_authenticated", False):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="unauthenticated",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )
    if not getattr(user, "is_staff", False):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="not_staff",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if not _module_scope_is_valid(classroom=classroom, module_id=module_scope_id):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="invalid_module_scope",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if getattr(user, "is_superuser", False):
        return StaffCapabilityDecision(
            allowed=True,
            capability=normalized_capability,
            reason="superuser",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if classroom is not None and classroom.organization_id is None:
        # Preserve management access for legacy classes that predate org
        # boundaries. These classes are unscoped by design until migrated.
        allowed = normalized_capability in _LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS
        return StaffCapabilityDecision(
            allowed=allowed,
            capability=normalized_capability,
            reason="legacy_unscoped_classroom_fallback" if allowed else "legacy_unscoped_classroom_denied",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    memberships = active_staff_memberships_queryset(user)
    if not memberships.exists():
        if require_org_membership_for_staff():
            if normalized_capability == CAP_CLASS_CREATE and not Organization.objects.filter(is_active=True).exists():
                return StaffCapabilityDecision(
                    allowed=True,
                    capability=normalized_capability,
                    reason="bootstrap_no_organizations",
                    classroom_id=classroom_id,
                    module_id=module_scope_id,
                )
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="membership_required",
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        allowed = normalized_capability in _LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS
        return StaffCapabilityDecision(
            allowed=allowed,
            capability=normalized_capability,
            reason="legacy_no_membership_fallback" if allowed else "legacy_no_membership_denied",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if classroom is not None:
        if classroom.organization_id is None:
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="classroom_missing_org",
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        memberships = memberships.filter(organization_id=classroom.organization_id)
        if not memberships.exists():
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="no_membership_for_class_org",
                organization_id=classroom.organization_id,
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        organization_id = int(classroom.organization_id)
    else:
        organization_id = None

    membership_rows = list(memberships.values("organization_id", "role"))
    override_org_ids = {int(row["organization_id"]) for row in membership_rows if row.get("organization_id")}
    capability_overrides = _org_role_capability_overrides(override_org_ids)
    custom_capability_overrides = _custom_role_capability_overrides(
        user,
        organization_ids=override_org_ids,
    )
    allowed_role = _highest_role_with_capability(
        memberships=membership_rows,
        capability=normalized_capability,
        overrides=capability_overrides,
    )
    custom_allowed_role = _highest_role_with_custom_capability(
        memberships=membership_rows,
        capability=normalized_capability,
        custom_overrides=custom_capability_overrides,
    )
    if not allowed_role and not custom_allowed_role:
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="role_missing_capability",
            organization_id=organization_id,
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )
    effective_role = allowed_role or custom_allowed_role
    allowed_by_custom_role = bool(custom_allowed_role and not allowed_role)

    if classroom is not None and scoped_module_grants_enabled() and normalized_capability in _SCOPED_GRANT_CAPABILITIES:
        module_order = None
        if normalized_capability in _MODULE_RANGE_GRANT_CAPABILITIES:
            if module_scope_id is None:
                return StaffCapabilityDecision(
                    allowed=True,
                    capability=normalized_capability,
                    reason="custom_role_allows_capability" if allowed_by_custom_role else "role_allows_capability",
                    role=effective_role,
                    organization_id=organization_id,
                    classroom_id=classroom_id,
                    module_id=module_scope_id,
                )
            module_order = _module_scope_order(classroom=classroom, module_id=module_scope_id)
            if module_order is None:
                return StaffCapabilityDecision(
                    allowed=False,
                    capability=normalized_capability,
                    reason="invalid_module_scope",
                    organization_id=organization_id,
                    classroom_id=classroom_id,
                    module_id=module_scope_id,
                )
        else:
            # Class-scoped capabilities use 0-0 range as class-wide sentinel.
            module_order = 0
        grants_qs = ClassStaffModuleScopeGrant.objects.filter(
            classroom=classroom,
            user=user,
            capability=normalized_capability,
            is_active=True,
        )
        if not grants_qs.exists():
            return StaffCapabilityDecision(
                allowed=True,
                capability=normalized_capability,
                reason=(
                    "custom_role_allows_capability_no_scoped_grants"
                    if allowed_by_custom_role
                    else "role_allows_capability_no_scoped_grants"
                ),
                role=effective_role,
                organization_id=organization_id,
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        grant_denies = grants_qs.filter(
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start__lte=module_order,
            module_order_end__gte=module_order,
        ).exists()
        if grant_denies:
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="scoped_grant_explicit_deny",
                role=effective_role,
                organization_id=organization_id,
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        grant_allows = grants_qs.filter(
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start__lte=module_order,
            module_order_end__gte=module_order,
        ).exists()
        if not grant_allows:
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="scoped_grant_denied",
                role=effective_role,
                organization_id=organization_id,
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        return StaffCapabilityDecision(
            allowed=True,
            capability=normalized_capability,
            reason="scoped_grant_allows",
            role=effective_role,
            organization_id=organization_id,
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )
    return StaffCapabilityDecision(
        allowed=True,
        capability=normalized_capability,
        reason="custom_role_allows_capability" if allowed_by_custom_role else "role_allows_capability",
        role=effective_role,
        organization_id=organization_id,
        classroom_id=classroom_id,
        module_id=module_scope_id,
    )


def staff_can(
    user,
    capability: str,
    *,
    classroom: Class | None = None,
    module_id: int | None = None,
) -> bool:
    return evaluate_staff_capability(
        user,
        capability,
        classroom=classroom,
        module_id=module_id,
    ).allowed


def staff_default_organization(user) -> Organization | None:
    if not getattr(user, "is_authenticated", False):
        return None
    if not getattr(user, "is_staff", False):
        return None
    memberships = list(active_staff_memberships_queryset(user).select_related("organization"))
    if not memberships:
        return None
    override_org_ids = {int(m.organization_id) for m in memberships if m.organization_id}
    capability_overrides = _org_role_capability_overrides(override_org_ids)
    custom_capability_overrides = _custom_role_capability_overrides(user, organization_ids=override_org_ids)
    eligible = [
        membership
        for membership in memberships
        if (
            CAP_CLASS_CREATE
            in _membership_role_capabilities(
                role=membership.role,
                organization_id=int(membership.organization_id),
                overrides=capability_overrides,
            )
            or CAP_CLASS_CREATE
            in custom_capability_overrides.get(int(membership.organization_id), frozenset())
        )
    ]
    if not eligible:
        return None
    role_rank = {
        OrganizationMembership.ROLE_OWNER: 0,
        OrganizationMembership.ROLE_ADMIN: 1,
        OrganizationMembership.ROLE_TEACHER: 2,
    }
    ranked = sorted(
        eligible,
        key=lambda m: (role_rank.get(m.role, 9), m.organization_id),
    )
    return ranked[0].organization


__all__ = [
    "CAP_CLASS_CREATE",
    "CAP_CLASS_MANAGE",
    "CAP_CLASS_VIEW",
    "CAP_POLICY_MANAGE",
    "CAP_ROSTER_MANAGE",
    "CAP_SUBMISSION_DELETE",
    "CAP_SUBMISSION_VIEW",
    "CAP_SYLLABUS_EXPORT",
    "StaffCapabilityDecision",
    "active_staff_memberships_queryset",
    "evaluate_staff_capability",
    "require_org_membership_for_staff",
    "staff_can",
    "staff_default_organization",
]
