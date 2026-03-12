"""Shared helpers for superuser org-management endpoints."""

from .shared import (
    Organization,
    OrganizationMembership,
    OrganizationRoleCapability,
    _safe_internal_redirect,
    _with_notice,
    get_user_model,
)


def org_form_values(request):
    return {
        "org_admin": "1",
        "org_name": (request.POST.get("org_name") or "").strip(),
        "org_membership_org_id": (request.POST.get("org_membership_org_id") or "").strip(),
        "org_membership_user_id": (request.POST.get("org_membership_user_id") or "").strip(),
        "org_membership_role": (request.POST.get("org_membership_role") or "").strip(),
        "org_membership_active": "1" if (request.POST.get("org_membership_active") or "").strip() == "1" else "0",
        "org_rolecap_org_id": (request.POST.get("org_rolecap_org_id") or "").strip(),
        "org_rolecap_role": (request.POST.get("org_rolecap_role") or "").strip(),
        "org_rolecap_capability": (request.POST.get("org_rolecap_capability") or "").strip(),
        "org_rolecap_active": "1" if (request.POST.get("org_rolecap_active") or "").strip() == "1" else "0",
    }


def require_superuser(request):
    if request.user.is_superuser:
        return None
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error="Only superusers can manage organizations.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


def organization_error(request, message: str, extra: dict | None = None):
    payload = {"org_admin": "1"}
    if extra:
        payload.update(extra)
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=payload),
        fallback="/teach",
    )


def membership_error(request, message: str, form_values: dict):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def role_capability_error(request, message: str, form_values: dict):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def parse_membership_ids(form_values: dict):
    try:
        return int(form_values["org_membership_org_id"]), int(form_values["org_membership_user_id"])
    except Exception:
        return None, None


def resolve_org_and_staff_user(org_id: int, user_id: int):
    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return None, None
    User = get_user_model()
    user = User.objects.filter(id=user_id, is_staff=True).first()
    if user is None:
        return org, None
    return org, user


def upsert_membership(*, org, user, role: str, is_active: bool):
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


def parse_role_capability_form(form_values: dict):
    role = form_values["org_rolecap_role"]
    capability = form_values["org_rolecap_capability"]
    is_active = form_values["org_rolecap_active"] == "1"
    try:
        org_id = int(form_values["org_rolecap_org_id"])
    except Exception:
        org_id = 0
    return org_id, role, capability, is_active


def upsert_role_capability(*, org, role: str, capability: str, is_active: bool):
    row, created = OrganizationRoleCapability.objects.get_or_create(
        organization=org,
        role=role,
        capability=capability,
        defaults={"is_active": is_active},
    )
    if row.is_active != is_active:
        row.is_active = is_active
        row.save(update_fields=["is_active", "updated_at"])
    return row, created


__all__ = [
    "membership_error",
    "org_form_values",
    "organization_error",
    "parse_membership_ids",
    "parse_role_capability_form",
    "require_superuser",
    "resolve_org_and_staff_user",
    "role_capability_error",
    "upsert_membership",
    "upsert_role_capability",
]
