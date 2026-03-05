"""Superuser class-to-organization management endpoints."""

from .shared import (
    Class,
    Organization,
    _audit,
    _parse_positive_int,
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


def _class_org_form_values(request):
    return {
        "org_admin": "1",
        "class_move_class_id": (request.POST.get("class_move_class_id") or "").strip(),
        "class_move_org_id": (request.POST.get("class_move_org_id") or "").strip(),
    }


def _class_org_error(request, message: str, form_values: dict):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_set_class_organization(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    form_values = _class_org_form_values(request)
    class_id = _parse_positive_int(form_values["class_move_class_id"], min_value=1, max_value=2_147_483_647)
    org_id = _parse_positive_int(form_values["class_move_org_id"], min_value=1, max_value=2_147_483_647)
    if class_id is None or org_id is None:
        return _class_org_error(request, "Select both a class and organization.", form_values)

    classroom = Class.objects.select_related("organization").filter(id=class_id).first()
    if classroom is None:
        return _class_org_error(request, "Class not found.", form_values)
    organization = Organization.objects.filter(id=org_id, is_active=True).first()
    if organization is None:
        return _class_org_error(request, "Organization not found or inactive.", form_values)
    if int(classroom.organization_id or 0) == int(organization.id):
        return _safe_internal_redirect(
            request,
            _with_notice(
                "/teach",
                notice=f"Class '{classroom.name}' is already in {organization.name}.",
                extra=form_values,
            ),
            fallback="/teach",
        )

    prior_organization_id = classroom.organization_id
    prior_organization_name = classroom.organization.name if classroom.organization_id else ""
    classroom.organization = organization
    classroom.save(update_fields=["organization"])
    _audit(
        request,
        action="class.organization.set",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Set class organization for {classroom.name}",
        metadata={
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "prior_organization_id": prior_organization_id,
            "prior_organization_name": prior_organization_name,
            "organization_id": organization.id,
            "organization_name": organization.name,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            "/teach",
            notice=f"Moved class '{classroom.name}' to organization '{organization.name}'.",
            extra=form_values,
        ),
        fallback="/teach",
    )


__all__ = [
    "teach_set_class_organization",
]
