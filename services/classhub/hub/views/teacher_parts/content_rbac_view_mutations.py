"""RBAC mutation endpoint handlers for teacher home."""

from __future__ import annotations

from ...models import ClassStaffModuleScopeGrant, RbacPolicyChangeRequest
from .content_rbac_access import rbac_tools_enabled_for_user
from .content_rbac_mutation_actions import (
    apply_custom_role_assignment_upsert as _apply_custom_role_assignment_upsert,
    apply_custom_role_capability_upsert as _apply_custom_role_capability_upsert,
    apply_custom_role_upsert as _apply_custom_role_upsert,
    apply_scope_grant_set_active as _apply_scope_grant_set_active,
    apply_scope_grant_upsert as _apply_scope_grant_upsert,
)
from .content_rbac_payload_parsers import (
    parse_custom_role_assignment_payload as _parse_custom_role_assignment_payload,
    parse_custom_role_capability_payload as _parse_custom_role_capability_payload,
    parse_custom_role_upsert_payload as _parse_custom_role_upsert_payload,
    parse_scope_grant_payload as _parse_scope_grant_payload,
    resolve_accessible_org_for_user as _resolve_accessible_org_for_user,
)
from .content_rbac_view_helpers import (
    queue_policy_change_request,
    rbac_policy_approval_required,
    rbac_redirect,
    require_rbac_tools_access,
)
from .shared import (
    _audit,
    _parse_positive_int,
    require_POST,
    staff_classroom_or_none,
    staff_member_required,
)


@staff_member_required
@require_POST
def teach_upsert_module_scope_grant(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied

    payload, error = _parse_scope_grant_payload(request)
    if payload is None:
        return rbac_redirect(request, error=error)

    if rbac_policy_approval_required():
        change = queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_UPSERT,
            payload=payload,
            summary=f"Scoped grant upsert {payload['capability']} ({payload['effect']})",
            classroom=staff_classroom_or_none(request.user, payload["classroom_id"]),
        )
        return rbac_redirect(request, notice=f"Scoped grant request queued (#{change.id}).")

    grant, created = _apply_scope_grant_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="rbac.scope_grant.portal_upsert",
        classroom=grant.classroom,
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal upsert scoped grant {grant.capability} ({grant.effect})",
        metadata={
            "created": bool(created),
            "user_id": grant.user_id,
            "capability": grant.capability,
            "effect": grant.effect,
            "module_order_start": grant.module_order_start,
            "module_order_end": grant.module_order_end,
            "is_active": bool(grant.is_active),
        },
    )
    return rbac_redirect(request, notice="Scoped grant saved.")


@staff_member_required
@require_POST
def teach_set_module_scope_grant_active(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied

    payload = {
        "grant_id": request.POST.get("rbac_grant_id") or "",
        "is_active": (request.POST.get("rbac_grant_active") or "0").strip() == "1",
    }
    grant_id = _parse_positive_int(str(payload.get("grant_id") or ""), min_value=1, max_value=2_147_483_647)
    if grant_id is None:
        return rbac_redirect(request, error="Grant id is required.")
    grant = ClassStaffModuleScopeGrant.objects.select_related("classroom").filter(id=grant_id).first()
    if grant is None:
        return rbac_redirect(request, error="Grant not found.")
    if staff_classroom_or_none(request.user, grant.classroom_id) is None:
        return rbac_redirect(request, error="Class not found.")

    if rbac_policy_approval_required():
        change = queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_SET_ACTIVE,
            payload=payload,
            summary=f"Scoped grant set active={payload['is_active']}",
            classroom=grant.classroom,
        )
        return rbac_redirect(request, notice=f"Scoped grant status request queued (#{change.id}).")

    try:
        grant = _apply_scope_grant_set_active(actor_user=request.user, payload=payload)
    except ValueError as exc:
        return rbac_redirect(request, error=str(exc))
    _audit(
        request,
        action="rbac.scope_grant.portal_set_active",
        classroom=grant.classroom,
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal set scoped grant active={grant.is_active}",
        metadata={"is_active": bool(grant.is_active)},
    )
    return rbac_redirect(request, notice="Scoped grant status updated.")


@staff_member_required
@require_POST
def teach_upsert_custom_role(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_upsert_payload(request)
    if payload is None:
        return rbac_redirect(request, error=error)

    if rbac_policy_approval_required():
        change = queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT,
            payload=payload,
            summary=f"Custom role upsert {payload['slug']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return rbac_redirect(request, notice=f"Custom role request queued (#{change.id}).")

    role, created = _apply_custom_role_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role.portal_upsert",
        target_type="OrganizationCustomRole",
        target_id=str(role.id),
        summary=f"Portal upsert custom role {role.slug}",
        metadata={
            "organization_id": role.organization_id,
            "slug": role.slug,
            "created": bool(created),
            "is_active": bool(role.is_active),
        },
    )
    return rbac_redirect(request, notice="Custom role saved.")


@staff_member_required
@require_POST
def teach_upsert_custom_role_capability(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_capability_payload(request)
    if payload is None:
        return rbac_redirect(request, error=error)

    if rbac_policy_approval_required():
        change = queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_CAPABILITY_UPSERT,
            payload=payload,
            summary=f"Custom role capability upsert {payload['slug']} -> {payload['capability']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return rbac_redirect(request, notice=f"Custom role capability request queued (#{change.id}).")

    row, created = _apply_custom_role_capability_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role_capability.portal_upsert",
        target_type="OrganizationCustomRoleCapability",
        target_id=str(row.id),
        summary=f"Portal upsert custom role capability {row.role.slug} -> {row.capability}",
        metadata={
            "organization_id": row.role.organization_id,
            "role_slug": row.role.slug,
            "capability": row.capability,
            "created": bool(created),
            "is_active": bool(row.is_active),
        },
    )
    return rbac_redirect(request, notice="Custom role capability saved.")


@staff_member_required
@require_POST
def teach_upsert_custom_role_assignment(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_assignment_payload(request)
    if payload is None:
        return rbac_redirect(request, error=error)

    if rbac_policy_approval_required():
        change = queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_ASSIGNMENT_UPSERT,
            payload=payload,
            summary=f"Custom role assignment upsert {payload['slug']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return rbac_redirect(request, notice=f"Custom role assignment request queued (#{change.id}).")

    assignment, created = _apply_custom_role_assignment_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role_assignment.portal_upsert",
        target_type="OrganizationCustomRoleAssignment",
        target_id=str(assignment.id),
        summary=f"Portal upsert custom role assignment for user {assignment.user_id}",
        metadata={
            "organization_id": assignment.organization_id,
            "role_slug": assignment.role.slug,
            "user_id": assignment.user_id,
            "created": bool(created),
            "is_active": bool(assignment.is_active),
        },
    )
    return rbac_redirect(request, notice="Custom role assignment saved.")


__all__ = [
    "teach_set_module_scope_grant_active",
    "teach_upsert_custom_role",
    "teach_upsert_custom_role_assignment",
    "teach_upsert_custom_role_capability",
    "teach_upsert_module_scope_grant",
]
