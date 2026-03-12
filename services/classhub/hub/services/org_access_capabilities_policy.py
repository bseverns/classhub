"""Policy evaluation and convenience accessors for org access capabilities."""

from __future__ import annotations

from ..models import Class, ClassStaffModuleScopeGrant, Organization, OrganizationMembership
from .org_access_capabilities_roles import (
    LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS,
    custom_role_capability_overrides,
    highest_role_with_capability,
    highest_role_with_custom_capability,
    membership_role_capabilities,
    org_role_capability_overrides,
)
from .org_access_capabilities_scope import (
    MODULE_RANGE_GRANT_CAPABILITIES,
    SCOPED_GRANT_CAPABILITIES,
    module_scope_is_valid,
    module_scope_order,
)
from .org_access_capabilities_shared import (
    CAP_CLASS_CREATE,
    KNOWN_CAPABILITIES,
    StaffCapabilityDecision,
    active_staff_memberships_queryset,
    require_org_membership_for_staff,
    scoped_module_grants_enabled,
)


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

    if normalized_capability not in KNOWN_CAPABILITIES:
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

    if not module_scope_is_valid(classroom=classroom, module_id=module_scope_id):
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
        allowed = normalized_capability in LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS
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
        allowed = normalized_capability in LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS
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
    capability_overrides = org_role_capability_overrides(override_org_ids)
    custom_capability_overrides = custom_role_capability_overrides(
        user,
        organization_ids=override_org_ids,
    )
    allowed_role = highest_role_with_capability(
        memberships=membership_rows,
        capability=normalized_capability,
        overrides=capability_overrides,
    )
    custom_allowed_role = highest_role_with_custom_capability(
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

    if classroom is not None and scoped_module_grants_enabled() and normalized_capability in SCOPED_GRANT_CAPABILITIES:
        module_order = None
        if normalized_capability in MODULE_RANGE_GRANT_CAPABILITIES:
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
            module_order = module_scope_order(classroom=classroom, module_id=module_scope_id)
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
    capability_overrides = org_role_capability_overrides(override_org_ids)
    custom_capability_overrides = custom_role_capability_overrides(user, organization_ids=override_org_ids)
    eligible = [
        membership
        for membership in memberships
        if (
            CAP_CLASS_CREATE
            in membership_role_capabilities(
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
    "evaluate_staff_capability",
    "staff_can",
    "staff_default_organization",
]
