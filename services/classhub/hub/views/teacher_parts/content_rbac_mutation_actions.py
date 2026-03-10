"""RBAC mutation actions shared by teacher endpoints and approval workflows."""

from __future__ import annotations

from ...models import (
    ClassStaffModuleScopeGrant,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationCustomRoleCapability,
    RbacPolicyChangeRequest,
)
from ...services.rbac_policy_bundle import apply_rbac_policy_payload
from .content_rbac_payload_parsers import (
    CUSTOM_ROLE_CAPABILITY_VALUES,
    CUSTOM_ROLE_SLUG_RE,
    EFFECT_VALUES,
    SCOPED_CAPABILITY_VALUES,
    resolve_accessible_org_for_user,
    resolve_staff_user,
    target_user_has_org_membership,
)
from .shared import _parse_positive_int, staff_classroom_or_none


def apply_scope_grant_upsert(*, actor_user, payload: dict):
    classroom = staff_classroom_or_none(actor_user, payload.get("classroom_id"))
    if classroom is None:
        raise ValueError("Class not found.")
    target_user = resolve_staff_user(str(payload.get("target_user_id") or ""))
    if target_user is None:
        raise ValueError("Staff user not found.")
    if not target_user_has_org_membership(target_user, organization_id=classroom.organization_id):
        raise ValueError("Target user must be active in the class organization.")
    capability = str(payload.get("capability") or "")
    if capability not in SCOPED_CAPABILITY_VALUES:
        raise ValueError("Unsupported scoped-grant capability.")
    effect = str(payload.get("effect") or "")
    if effect not in EFFECT_VALUES:
        raise ValueError("Unsupported grant effect.")
    module_start = _parse_positive_int(str(payload.get("module_start") or ""), min_value=0, max_value=50_000)
    module_end = _parse_positive_int(str(payload.get("module_end") or ""), min_value=0, max_value=50_000)
    if module_start is None or module_end is None or module_end < module_start:
        raise ValueError("Invalid module range.")
    is_active = bool(payload.get("is_active"))
    grant, created = ClassStaffModuleScopeGrant.objects.get_or_create(
        classroom=classroom,
        user=target_user,
        capability=capability,
        effect=effect,
        module_order_start=module_start,
        module_order_end=module_end,
        defaults={"is_active": is_active},
    )
    if not created and grant.is_active != is_active:
        grant.is_active = is_active
        grant.save(update_fields=["is_active", "updated_at"])
    return grant, created


def apply_scope_grant_set_active(*, actor_user, payload: dict):
    grant_id = _parse_positive_int(str(payload.get("grant_id") or ""), min_value=1, max_value=2_147_483_647)
    if grant_id is None:
        raise ValueError("Grant id is required.")
    grant = ClassStaffModuleScopeGrant.objects.select_related("classroom").filter(id=grant_id).first()
    if grant is None:
        raise ValueError("Grant not found.")
    if staff_classroom_or_none(actor_user, grant.classroom_id) is None:
        raise ValueError("Class not found.")
    is_active = bool(payload.get("is_active"))
    if grant.is_active != is_active:
        grant.is_active = is_active
        grant.save(update_fields=["is_active", "updated_at"])
    return grant


def apply_custom_role_upsert(*, actor_user, payload: dict):
    org = resolve_accessible_org_for_user(actor_user, str(payload.get("organization_id") or ""))
    if org is None:
        raise ValueError("Organization not found.")
    slug = str(payload.get("slug") or "").strip().lower()
    if not CUSTOM_ROLE_SLUG_RE.match(slug):
        raise ValueError("Invalid custom role slug.")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Custom role name is required.")
    description = str(payload.get("description") or "").strip()
    is_active = bool(payload.get("is_active"))
    role, created = OrganizationCustomRole.objects.get_or_create(
        organization=org,
        slug=slug,
        defaults={"name": name[:120], "description": description[:500], "is_active": is_active},
    )
    changed_fields: list[str] = []
    if role.name != name[:120]:
        role.name = name[:120]
        changed_fields.append("name")
    if role.description != description[:500]:
        role.description = description[:500]
        changed_fields.append("description")
    if role.is_active != is_active:
        role.is_active = is_active
        changed_fields.append("is_active")
    if changed_fields:
        role.save(update_fields=changed_fields + ["updated_at"])
    return role, created


def apply_custom_role_capability_upsert(*, actor_user, payload: dict):
    org = resolve_accessible_org_for_user(actor_user, str(payload.get("organization_id") or ""))
    if org is None:
        raise ValueError("Organization not found.")
    slug = str(payload.get("slug") or "").strip().lower()
    role = OrganizationCustomRole.objects.filter(organization=org, slug=slug).first()
    if role is None:
        raise ValueError("Custom role not found.")
    capability = str(payload.get("capability") or "").strip().lower()
    if capability not in CUSTOM_ROLE_CAPABILITY_VALUES:
        raise ValueError("Invalid capability.")
    is_active = bool(payload.get("is_active"))
    row, created = OrganizationCustomRoleCapability.objects.get_or_create(
        role=role,
        capability=capability,
        defaults={"is_active": is_active},
    )
    if not created and row.is_active != is_active:
        row.is_active = is_active
        row.save(update_fields=["is_active", "updated_at"])
    return row, created


def apply_custom_role_assignment_upsert(*, actor_user, payload: dict):
    org = resolve_accessible_org_for_user(actor_user, str(payload.get("organization_id") or ""))
    if org is None:
        raise ValueError("Organization not found.")
    slug = str(payload.get("slug") or "").strip().lower()
    role = OrganizationCustomRole.objects.filter(organization=org, slug=slug).first()
    if role is None:
        raise ValueError("Custom role not found.")
    target_user = resolve_staff_user(str(payload.get("target_user_id") or ""))
    if target_user is None:
        raise ValueError("Staff user not found.")
    if not target_user_has_org_membership(target_user, organization_id=int(org.id)):
        raise ValueError("Target user must be active in the selected organization.")
    is_active = bool(payload.get("is_active"))
    assignment, created = OrganizationCustomRoleAssignment.objects.get_or_create(
        organization=org,
        user=target_user,
        role=role,
        defaults={"is_active": is_active},
    )
    if not created and assignment.is_active != is_active:
        assignment.is_active = is_active
        assignment.save(update_fields=["is_active", "updated_at"])
    return assignment, created


def apply_change_request_approved(*, actor_user, change_request: RbacPolicyChangeRequest) -> str:
    payload = change_request.payload or {}
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_UPSERT:
        grant, _created = apply_scope_grant_upsert(actor_user=actor_user, payload=payload)
        return f"Applied scoped grant #{grant.id}."
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_SET_ACTIVE:
        grant = apply_scope_grant_set_active(actor_user=actor_user, payload=payload)
        return f"Updated scoped grant #{grant.id} active={grant.is_active}."
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT:
        role, _created = apply_custom_role_upsert(actor_user=actor_user, payload=payload)
        return f"Applied custom role {role.slug}."
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_CAPABILITY_UPSERT:
        row, _created = apply_custom_role_capability_upsert(actor_user=actor_user, payload=payload)
        return f"Applied custom role capability {row.role.slug}->{row.capability}."
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_ASSIGNMENT_UPSERT:
        assignment, _created = apply_custom_role_assignment_upsert(actor_user=actor_user, payload=payload)
        return f"Applied custom role assignment #{assignment.id}."
    if change_request.request_type == RbacPolicyChangeRequest.REQUEST_POLICY_IMPORT:
        policy_payload = payload.get("policy_payload")
        if not isinstance(policy_payload, dict):
            raise ValueError("Policy request payload is missing policy JSON.")
        source_label = str(payload.get("source_label") or "approval").strip() or "approval"
        result = apply_rbac_policy_payload(
            actor_user=actor_user,
            payload=policy_payload,
            source_label=source_label,
        )
        return (
            "Applied policy import "
            f"(org rows:{result.org_rows}, grant rows:{result.grant_rows}, "
            f"custom roles:{result.custom_role_rows}, assignments:{result.custom_role_assignment_rows})."
        )
    raise ValueError("Unsupported policy change request type.")


__all__ = [
    "apply_change_request_approved",
    "apply_custom_role_assignment_upsert",
    "apply_custom_role_capability_upsert",
    "apply_custom_role_upsert",
    "apply_scope_grant_set_active",
    "apply_scope_grant_upsert",
]
