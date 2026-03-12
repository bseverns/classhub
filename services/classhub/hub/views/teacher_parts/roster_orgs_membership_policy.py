"""Superuser organization membership and role-capability endpoints."""

from .shared import (
    HttpResponse,
    Organization,
    OrganizationMembership,
    OrganizationRoleCapability,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_member_required,
)
from .roster_orgs_shared import (
    membership_error,
    org_form_values,
    parse_membership_ids,
    parse_role_capability_form,
    require_superuser as _require_superuser,
    resolve_org_and_staff_user,
    role_capability_error,
    upsert_membership,
    upsert_role_capability,
)


@staff_member_required
@require_POST
def teach_upsert_organization_membership(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    form_values = org_form_values(request)
    role = form_values["org_membership_role"]
    is_active = form_values["org_membership_active"] == "1"
    org_id, user_id = parse_membership_ids(form_values)
    if org_id is None or user_id is None:
        return membership_error(request, "Select both an organization and staff user.", form_values)

    valid_roles = {value for value, _label in OrganizationMembership.ROLE_CHOICES}
    if role not in valid_roles:
        return membership_error(request, "Select a valid organization role.", form_values)

    org, user = resolve_org_and_staff_user(org_id, user_id)
    if org is None:
        return membership_error(request, "Organization not found.", form_values)
    if user is None:
        return membership_error(request, "Staff user not found.", form_values)

    membership, created = upsert_membership(org=org, user=user, role=role, is_active=is_active)

    status_label = "active" if membership.is_active else "inactive"
    _audit(
        request,
        action="organization.membership.upsert",
        target_type="OrganizationMembership",
        target_id=str(membership.id),
        summary=f"Set org membership for {user.username} in {org.name}",
        metadata={
            "membership_id": membership.id,
            "organization_id": org.id,
            "organization_name": org.name,
            "user_id": user.id,
            "username": user.username,
            "role": membership.role,
            "is_active": membership.is_active,
            "created": created,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            "/teach",
            notice=f"Set {user.username} as {membership.get_role_display()} in {org.name} ({status_label}).",
            extra={"org_admin": "1"},
        ),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_upsert_org_role_capability(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    form_values = org_form_values(request)
    org_id, role, capability, is_active = parse_role_capability_form(form_values)
    if not org_id:
        return role_capability_error(request, "Select an organization.", form_values)

    valid_roles = {value for value, _label in OrganizationMembership.ROLE_CHOICES}
    if role not in valid_roles:
        return role_capability_error(request, "Select a valid role.", form_values)
    valid_capabilities = {value for value, _label in OrganizationRoleCapability.CAPABILITY_CHOICES}
    if capability not in valid_capabilities:
        return role_capability_error(request, "Select a valid capability.", form_values)

    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return role_capability_error(request, "Organization not found.", form_values)

    row, created = upsert_role_capability(org=org, role=role, capability=capability, is_active=is_active)
    _audit(
        request,
        action="organization.role_capability.upsert",
        target_type="OrganizationRoleCapability",
        target_id=str(row.id),
        summary=f"Set role capability {role} -> {capability} in {org.name}",
        metadata={
            "organization_id": org.id,
            "organization_name": org.name,
            "role": role,
            "capability": capability,
            "is_active": row.is_active,
            "created": created,
        },
    )
    status_label = "active" if row.is_active else "inactive"
    return _safe_internal_redirect(
        request,
        _with_notice(
            "/teach",
            notice=f"Set {org.name} {role} capability {capability} ({status_label}).",
            extra={"org_admin": "1"},
        ),
        fallback="/teach",
    )


__all__ = [
    "teach_upsert_org_role_capability",
    "teach_upsert_organization_membership",
]
