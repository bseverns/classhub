"""Export payload shaping helpers for RBAC policy bundles."""

from __future__ import annotations

from ..models import (
    ClassStaffModuleScopeGrant,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationRoleCapability,
)
from .org_access import staff_accessible_classes_ranked
from .rbac_policy_bundle_schema import POLICY_SCHEMA_VERSION


def _role_capability_payload(org_rows):
    grouped: dict[int, dict] = {}
    for row in org_rows:
        bucket = grouped.setdefault(
            int(row.organization_id),
            {
                "name": row.organization.name,
                "role_capabilities": [],
            },
        )
        bucket["role_capabilities"].append(
            {
                "role": row.role,
                "capability": row.capability,
                "is_active": bool(row.is_active),
            }
        )
    return list(grouped.values())


def _scoped_grant_payload(grant_rows):
    payload = []
    for row in grant_rows:
        payload.append(
            {
                "class_join_code": row.classroom.join_code,
                "class_name": row.classroom.name,
                "username": row.user.username,
                "capability": row.capability,
                "effect": row.effect,
                "module_order_start": int(row.module_order_start),
                "module_order_end": int(row.module_order_end),
                "is_active": bool(row.is_active),
            }
        )
    return payload


def _custom_role_payload(rows):
    payload = []
    for row in rows:
        payload.append(
            {
                "organization_name": row.organization.name,
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "is_active": bool(row.is_active),
                "capabilities": [
                    {
                        "capability": cap.capability,
                        "is_active": bool(cap.is_active),
                    }
                    for cap in row.capabilities.all()
                ],
            }
        )
    return payload


def _custom_role_assignment_payload(rows):
    payload = []
    for row in rows:
        payload.append(
            {
                "organization_name": row.organization.name,
                "role_slug": row.role.slug,
                "username": row.user.username,
                "is_active": bool(row.is_active),
            }
        )
    return payload


def build_policy_export_payload(actor_user, *, exported_at: str) -> dict:
    classes, _assigned = staff_accessible_classes_ranked(actor_user)
    class_ids = [int(c.id) for c in classes]
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    role_caps = list(
        OrganizationRoleCapability.objects.select_related("organization")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "role", "capability", "id")
    )
    scope_grants = list(
        ClassStaffModuleScopeGrant.objects.select_related("classroom", "user")
        .filter(classroom_id__in=class_ids)
        .order_by(
            "classroom__name",
            "user__username",
            "capability",
            "effect",
            "module_order_start",
            "module_order_end",
            "id",
        )
    )
    custom_roles = list(
        OrganizationCustomRole.objects.select_related("organization")
        .prefetch_related("capabilities")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "slug", "id")
    )
    custom_role_assignments = list(
        OrganizationCustomRoleAssignment.objects.select_related("organization", "role", "user")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "role__slug", "user__username", "id")
    )
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "exported_at": exported_at,
        "exported_by": actor_user.username,
        "organizations": _role_capability_payload(role_caps),
        "scoped_grants": _scoped_grant_payload(scope_grants),
        "custom_roles": _custom_role_payload(custom_roles),
        "custom_role_assignments": _custom_role_assignment_payload(custom_role_assignments),
    }


__all__ = ["build_policy_export_payload"]
