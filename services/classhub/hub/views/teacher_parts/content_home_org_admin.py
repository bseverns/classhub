"""Organization/admin state and context builders for teacher home."""

from .shared import (
    Class,
    ClassStaffAssignment,
    Organization,
    OrganizationMembership,
    OrganizationRoleCapability,
    _parse_positive_int,
    models,
)


def _read_org_admin_state(request):
    org_name = (request.GET.get("org_name") or "").strip()
    org_membership_org_id = (request.GET.get("org_membership_org_id") or "").strip()
    org_membership_user_id = (request.GET.get("org_membership_user_id") or "").strip()
    org_membership_role = (request.GET.get("org_membership_role") or "").strip()
    org_membership_active = (request.GET.get("org_membership_active") or "").strip()
    org_rolecap_org_id = (request.GET.get("org_rolecap_org_id") or "").strip()
    org_rolecap_role = (request.GET.get("org_rolecap_role") or "").strip()
    org_rolecap_capability = (request.GET.get("org_rolecap_capability") or "").strip()
    org_rolecap_active = (request.GET.get("org_rolecap_active") or "").strip()
    class_assignment_class_id = (request.GET.get("class_assignment_class_id") or "").strip()
    class_assignment_user_id = (request.GET.get("class_assignment_user_id") or "").strip()
    class_assignment_active = (request.GET.get("class_assignment_active") or "").strip()
    class_assignment_bulk_user_id = (request.GET.get("class_assignment_bulk_user_id") or "").strip()
    class_move_class_id = (request.GET.get("class_move_class_id") or "").strip()
    class_move_org_id = (request.GET.get("class_move_org_id") or "").strip()
    org_admin_active = (
        (request.GET.get("org_admin") or "").strip() == "1"
        or bool(
            org_name
            or org_membership_org_id
            or org_membership_user_id
            or org_membership_role
            or org_rolecap_org_id
            or org_rolecap_role
            or org_rolecap_capability
            or class_assignment_class_id
            or class_assignment_user_id
            or class_assignment_bulk_user_id
            or class_move_class_id
            or class_move_org_id
        )
    )
    return {
        "org_name": org_name,
        "org_membership_org_id": org_membership_org_id,
        "org_membership_user_id": org_membership_user_id,
        "org_membership_role": org_membership_role,
        "org_membership_active": org_membership_active if org_membership_active in {"0", "1"} else "1",
        "org_rolecap_org_id": org_rolecap_org_id,
        "org_rolecap_role": org_rolecap_role,
        "org_rolecap_capability": org_rolecap_capability,
        "org_rolecap_active": org_rolecap_active if org_rolecap_active in {"0", "1"} else "1",
        "class_assignment_class_id": class_assignment_class_id,
        "class_assignment_user_id": class_assignment_user_id,
        "class_assignment_active": class_assignment_active if class_assignment_active in {"0", "1"} else "1",
        "class_assignment_bulk_user_id": class_assignment_bulk_user_id,
        "class_move_class_id": class_move_class_id,
        "class_move_org_id": class_move_org_id,
        "org_admin_active": org_admin_active,
    }


def _empty_class_assignment_context(org_state: dict):
    return {
        "class_staff_assignments": [],
        "org_classes": [],
        "class_assignment_class_id": org_state.get("class_assignment_class_id", ""),
        "class_assignment_user_id": org_state.get("class_assignment_user_id", ""),
        "class_assignment_active": org_state.get("class_assignment_active", "1"),
        "class_assignment_bulk_user_id": org_state.get("class_assignment_bulk_user_id", ""),
        "class_assignment_bulk_selected_class_ids": [],
        "class_move_class_id": org_state.get("class_move_class_id", ""),
        "class_move_org_id": org_state.get("class_move_org_id", ""),
    }


def _class_assignment_context(*, org_state: dict, classes: list):
    class_staff_assignments = list(
        ClassStaffAssignment.objects.select_related("classroom", "user").order_by("classroom__name", "user__username", "id")
    )
    bulk_user_id = _parse_positive_int(
        org_state.get("class_assignment_bulk_user_id", ""),
        min_value=1,
        max_value=2_147_483_647,
    )
    selected_bulk_class_ids: list[int] = []
    if bulk_user_id is not None:
        selected_bulk_class_ids = list(
            ClassStaffAssignment.objects.filter(
                user_id=bulk_user_id,
                is_active=True,
                classroom_id__in=[int(c.id) for c in classes],
            ).values_list("classroom_id", flat=True)
        )
    move_class_id = org_state.get("class_move_class_id", "")
    move_org_id = org_state.get("class_move_org_id", "")
    parsed_move_class_id = _parse_positive_int(move_class_id, min_value=1, max_value=2_147_483_647)
    if parsed_move_class_id is not None and not move_org_id:
        target_class = next((c for c in classes if int(c.id) == int(parsed_move_class_id)), None)
        if target_class is not None and target_class.organization_id:
            move_org_id = str(target_class.organization_id)
    return {
        "class_staff_assignments": class_staff_assignments,
        "org_classes": classes,
        "class_assignment_class_id": org_state["class_assignment_class_id"],
        "class_assignment_user_id": org_state["class_assignment_user_id"],
        "class_assignment_active": org_state["class_assignment_active"],
        "class_assignment_bulk_user_id": org_state["class_assignment_bulk_user_id"],
        "class_assignment_bulk_selected_class_ids": selected_bulk_class_ids,
        "class_move_class_id": move_class_id,
        "class_move_org_id": move_org_id,
    }


def _build_org_admin_context(*, user, user_model, org_state: dict, classes: list):
    if not user.is_superuser:
        return {
            "organizations": [],
            "org_memberships": [],
            "org_role_capabilities": [],
            "staff_users": [],
            **_empty_class_assignment_context(org_state),
            "org_role_choices": OrganizationMembership.ROLE_CHOICES,
            "org_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        }
    organizations = list(Organization.objects.order_by("name", "id").only("id", "name", "is_active"))
    org_class_counts: dict[int, int] = {}
    if organizations:
        org_class_counts = {
            int(row["organization_id"]): int(row["count"])
            for row in (
                Class.objects.filter(organization_id__in=[int(org.id) for org in organizations])
                .values("organization_id")
                .annotate(count=models.Count("id"))
            )
        }
    for org in organizations:
        setattr(org, "class_count", org_class_counts.get(int(org.id), 0))
    org_memberships = list(
        OrganizationMembership.objects.select_related("organization", "user").order_by(
            "organization__name",
            "user__username",
            "id",
        )
    )
    org_role_capabilities = list(
        OrganizationRoleCapability.objects.select_related("organization").order_by(
            "organization__name",
            "role",
            "capability",
            "id",
        )
    )
    staff_users = list(
        user_model.objects.filter(is_staff=True).order_by("username", "id").only(
            "id",
            "username",
            "is_active",
            "is_superuser",
        )
    )
    return {
        "organizations": organizations,
        "org_memberships": org_memberships,
        "org_role_capabilities": org_role_capabilities,
        "staff_users": staff_users,
        **_class_assignment_context(org_state=org_state, classes=classes),
        "org_role_choices": OrganizationMembership.ROLE_CHOICES,
        "org_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
    }


__all__ = [
    "_build_org_admin_context",
    "_read_org_admin_state",
]
