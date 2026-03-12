"""Superuser organization lifecycle endpoints."""

from .shared import (
    Class,
    HttpResponse,
    Organization,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_member_required,
)
from .roster_orgs_shared import org_form_values, organization_error, require_superuser


@staff_member_required
@require_POST
def teach_create_organization(request):
    denied = require_superuser(request)
    if denied is not None:
        return denied

    form_values = org_form_values(request)
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
    denied = require_superuser(request)
    if denied is not None:
        return denied

    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return organization_error(request, "Organization not found.")

    is_active = (request.POST.get("is_active") or "").strip() == "1"
    if not is_active:
        class_count = Class.objects.filter(organization=org).count()
        if class_count > 0:
            label = "class" if class_count == 1 else "classes"
            return organization_error(
                request,
                f"Cannot archive '{org.name}' while {class_count} {label} still belong to it. Move classes first.",
            )
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


__all__ = [
    "teach_create_organization",
    "teach_set_organization_active",
]
