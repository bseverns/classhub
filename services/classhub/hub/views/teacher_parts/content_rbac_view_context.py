"""RBAC teacher-home context payload assembly."""

from __future__ import annotations

from ...models import (
    ClassStaffModuleScopeGrant,
    Organization,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationRoleCapability,
)
from .content_rbac_access import rbac_tools_enabled_for_user, rbac_tools_requested
from .content_rbac_audit import build_rbac_audit_context
from .content_rbac_bulk import build_bulk_simulation_result
from .content_rbac_payload_parsers import SIMULATION_CAPABILITY_VALUES as _SIMULATION_CAPABILITY_VALUES
from .content_rbac_state import (
    rbac_form_state,
    rbac_scope_grants,
    rbac_simulation_result,
    rbac_staff_users,
)
from .content_rbac_view_helpers import (
    rbac_pending_change_requests,
    rbac_policy_approval_required,
)


def build_rbac_tools_context(*, request, classes) -> dict:
    if not rbac_tools_enabled_for_user(request.user):
        return {
            "rbac_tools_enabled": False,
            "rbac_tools_active": False,
        }
    state = rbac_form_state(request)
    staff_users = rbac_staff_users(classes)
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    organizations = list(
        Organization.objects.filter(id__in=org_ids, is_active=True).order_by("name", "id").only("id", "name")
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
    bulk_simulation_result = build_bulk_simulation_result(
        request=request,
        capability_values=_SIMULATION_CAPABILITY_VALUES,
        staff_users=staff_users,
        state=state,
    )
    audit_context = build_rbac_audit_context(classes=classes, state=state)

    return {
        "rbac_tools_enabled": True,
        "rbac_tools_active": rbac_tools_requested(request),
        "rbac_classes": classes,
        "rbac_orgs": organizations,
        "rbac_staff_users": staff_users,
        "rbac_scope_grants": rbac_scope_grants(classes),
        "rbac_custom_roles": custom_roles,
        "rbac_custom_role_assignments": custom_role_assignments,
        "rbac_pending_change_requests": rbac_pending_change_requests(classes=classes),
        "rbac_policy_approval_required": rbac_policy_approval_required(),
        "rbac_scoped_capability_choices": ClassStaffModuleScopeGrant.CAPABILITY_CHOICES,
        "rbac_simulation_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        "rbac_effect_choices": ClassStaffModuleScopeGrant.EFFECT_CHOICES,
        "rbac_custom_role_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        **state,
        "rbac_simulation_result": rbac_simulation_result(request),
        "rbac_bulk_simulation_result": bulk_simulation_result,
        **audit_context,
    }


__all__ = ["build_rbac_tools_context"]
