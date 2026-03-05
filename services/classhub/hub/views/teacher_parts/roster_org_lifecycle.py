"""Superuser organization lifecycle endpoints."""

from .shared import (
    Organization,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_member_required,
)


def _require_superuser(request):
    if request.user.is_superuser:
        return None
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error="Only superusers can manage organizations.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


def _organization_error(request, message: str):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra={"org_admin": "1"}),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_rename_organization(request, org_id: int):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    org = Organization.objects.filter(id=org_id).first()
    if org is None:
        return _organization_error(request, "Organization not found.")
    new_name = (request.POST.get("org_rename_name") or "").strip()
    if not new_name:
        return _organization_error(request, "Organization name is required.")
    if len(new_name) > 200:
        return _organization_error(request, "Organization name must be 200 characters or fewer.")
    duplicate = Organization.objects.filter(name__iexact=new_name).exclude(id=org.id).exists()
    if duplicate:
        return _organization_error(request, "An organization with that name already exists.")
    if org.name == new_name:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", notice=f"Organization '{org.name}' is unchanged.", extra={"org_admin": "1"}),
            fallback="/teach",
        )

    prior_name = org.name
    org.name = new_name
    org.save(update_fields=["name", "updated_at"])
    _audit(
        request,
        action="organization.rename",
        target_type="Organization",
        target_id=str(org.id),
        summary=f"Renamed organization {prior_name} to {org.name}",
        metadata={
            "organization_id": org.id,
            "prior_name": prior_name,
            "organization_name": org.name,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=f"Renamed organization '{prior_name}' to '{org.name}'.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


__all__ = [
    "teach_rename_organization",
]
