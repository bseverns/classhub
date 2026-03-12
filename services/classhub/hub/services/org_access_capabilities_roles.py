"""Role and custom capability helpers for org access policy evaluation."""

from __future__ import annotations

from django.db.models import F

from ..models import (
    OrganizationCustomRoleAssignment,
    OrganizationMembership,
    OrganizationRoleCapability,
)
from .org_access_capabilities_shared import (
    CAP_CLASS_CREATE,
    CAP_CLASS_MANAGE,
    CAP_CLASS_VIEW,
    CAP_POLICY_MANAGE,
    CAP_ROSTER_MANAGE,
    CAP_SUBMISSION_DELETE,
    CAP_SUBMISSION_VIEW,
    CAP_SYLLABUS_EXPORT,
    KNOWN_CAPABILITIES,
)

ROLE_PRECEDENCE = (
    OrganizationMembership.ROLE_OWNER,
    OrganizationMembership.ROLE_ADMIN,
    OrganizationMembership.ROLE_TEACHER,
    OrganizationMembership.ROLE_VIEWER,
)

DEFAULT_ROLE_CAPABILITIES = {
    OrganizationMembership.ROLE_OWNER: frozenset(KNOWN_CAPABILITIES),
    OrganizationMembership.ROLE_ADMIN: frozenset(KNOWN_CAPABILITIES),
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

LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS = frozenset(
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


def org_role_capability_overrides(organization_ids: set[int]) -> dict[int, dict[str, frozenset[str]]]:
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


def membership_role_capabilities(
    *,
    role: str,
    organization_id: int,
    overrides: dict[int, dict[str, frozenset[str]]],
) -> frozenset[str]:
    org_overrides = overrides.get(int(organization_id), {})
    if role in org_overrides:
        return org_overrides[role]
    return DEFAULT_ROLE_CAPABILITIES.get(role, frozenset())


def custom_role_capability_overrides(
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


def highest_role_with_capability(
    *,
    memberships: list[dict[str, int | str]],
    capability: str,
    overrides: dict[int, dict[str, frozenset[str]]],
) -> str:
    for role in ROLE_PRECEDENCE:
        for row in memberships:
            if str(row.get("role")) != role:
                continue
            organization_id = int(row.get("organization_id") or 0)
            if capability in membership_role_capabilities(
                role=role,
                organization_id=organization_id,
                overrides=overrides,
            ):
                return role
    return ""


def highest_role_with_custom_capability(
    *,
    memberships: list[dict[str, int | str]],
    capability: str,
    custom_overrides: dict[int, frozenset[str]],
) -> str:
    for role in ROLE_PRECEDENCE:
        for row in memberships:
            if str(row.get("role")) != role:
                continue
            organization_id = int(row.get("organization_id") or 0)
            custom_caps = custom_overrides.get(organization_id, frozenset())
            if capability in custom_caps:
                return role
    return ""


__all__ = [
    "LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS",
    "ROLE_PRECEDENCE",
    "custom_role_capability_overrides",
    "highest_role_with_capability",
    "highest_role_with_custom_capability",
    "membership_role_capabilities",
    "org_role_capability_overrides",
]
