"""Superuser org and org-membership management endpoints."""

from .shared import (
    Organization,
    OrganizationMembership,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    get_user_model,
    require_POST,
    staff_member_required,
)


def _org_form_values(request):
    return {
        "org_admin": "1",
        "org_name": (request.POST.get("org_name") or "").strip(),
        "org_membership_org_id": (request.POST.get("org_membership_org_id") or "").strip(),
        "org_membership_user_id": (request.POST.get("org_membership_user_id") or "").strip(),
        "org_membership_role": (request.POST.get("org_membership_role") or "").strip(),
        "org_membership_active": "1" if (request.POST.get("org_membership_active") or "").strip() == "1" else "0",
    }


def _require_superuser(request):
    if request.user.is_superuser:
        return None
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error="Only superusers can manage organizations.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


def _membership_error(request, message: str, form_values: dict):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def _parse_membership_ids(form_values: dict):
    try:
        return int(form_values["org_membership_org_id"]), int(form_values["org_membership_user_id"])
    except Exception:
        return None, None


def _resolve_org_and_staff_user(org_id: int, user_id: int):
    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return None, None
    User = get_user_model()
    user = User.objects.filter(id=user_id, is_staff=True).first()
    if user is None:
        return org, None
    return org, user


def _upsert_membership(*, org, user, role: str, is_active: bool):
    membership, created = OrganizationMembership.objects.get_or_create(
        organization=org,
        user=user,
        defaults={"role": role, "is_active": is_active},
    )
    changed_fields: list[str] = []
    if membership.role != role:
        membership.role = role
        changed_fields.append("role")
    if membership.is_active != is_active:
        membership.is_active = is_active
        changed_fields.append("is_active")
    if changed_fields:
        membership.save(update_fields=changed_fields + ["updated_at"])
    return membership, created


@staff_member_required
@require_POST
def teach_create_organization(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    form_values = _org_form_values(request)
    name = form_values["org_name"]
    if not name:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Organization name is required.", extra=form_values),
            fallback="/teach",
        )
    if len(name) > 200:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Organization name must be 200 characters or fewer.", extra=form_values),
            fallback="/teach",
        )
    if Organization.objects.filter(name__iexact=name).exists():
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="An organization with that name already exists.", extra=form_values),
            fallback="/teach",
        )

    org = Organization.objects.create(name=name, is_active=True)
    _audit(
        request,
        action="organization.create",
        target_type="Organization",
        target_id=str(org.id),
        summary=f"Created organization {org.name}",
        metadata={"organization_id": org.id, "organization_name": org.name, "is_active": org.is_active},
    )
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=f"Created organization '{org.name}'.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_set_organization_active(request, org_id: int):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Organization not found.", extra={"org_admin": "1"}),
            fallback="/teach",
        )

    is_active = (request.POST.get("is_active") or "").strip() == "1"
    if org.is_active != is_active:
        org.is_active = is_active
        org.save(update_fields=["is_active", "updated_at"])
    _audit(
        request,
        action="organization.set_active",
        target_type="Organization",
        target_id=str(org.id),
        summary=f"Set organization active={org.is_active} for {org.name}",
        metadata={"organization_id": org.id, "organization_name": org.name, "is_active": org.is_active},
    )
    status_label = "active" if org.is_active else "inactive"
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=f"Set organization '{org.name}' {status_label}.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_upsert_organization_membership(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    form_values = _org_form_values(request)
    role = form_values["org_membership_role"]
    is_active = form_values["org_membership_active"] == "1"
    org_id, user_id = _parse_membership_ids(form_values)
    if org_id is None or user_id is None:
        return _membership_error(request, "Select both an organization and staff user.", form_values)

    valid_roles = {value for value, _label in OrganizationMembership.ROLE_CHOICES}
    if role not in valid_roles:
        return _membership_error(request, "Select a valid organization role.", form_values)

    org, user = _resolve_org_and_staff_user(org_id, user_id)
    if org is None:
        return _membership_error(request, "Organization not found.", form_values)
    if user is None:
        return _membership_error(request, "Staff user not found.", form_values)

    membership, created = _upsert_membership(org=org, user=user, role=role, is_active=is_active)

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


__all__ = [
    "teach_create_organization",
    "teach_set_organization_active",
    "teach_upsert_organization_membership",
]
