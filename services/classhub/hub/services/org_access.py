"""Organization-scoped staff access helpers.

Legacy compatibility:
- Staff users without explicit org memberships keep global class access.
- Once a user has active org memberships, class access is restricted to those orgs.
"""

from django.conf import settings
from django.db.models import QuerySet

from ..models import Class, ClassStaffAssignment, Organization, OrganizationMembership

_MANAGE_ROLES = {
    OrganizationMembership.ROLE_OWNER,
    OrganizationMembership.ROLE_ADMIN,
    OrganizationMembership.ROLE_TEACHER,
}
_SYLLABUS_EXPORT_ROLES = {
    OrganizationMembership.ROLE_OWNER,
    OrganizationMembership.ROLE_ADMIN,
}


def _require_org_membership_for_staff() -> bool:
    return bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False))


def _active_memberships_queryset(user) -> QuerySet[OrganizationMembership]:
    if not getattr(user, "is_authenticated", False):
        return OrganizationMembership.objects.none()
    if not getattr(user, "is_staff", False):
        return OrganizationMembership.objects.none()
    return OrganizationMembership.objects.filter(
        user=user,
        is_active=True,
        organization__is_active=True,
    )


def staff_has_explicit_memberships(user) -> bool:
    return _active_memberships_queryset(user).exists()


def staff_accessible_classes_queryset(user) -> QuerySet[Class]:
    if not getattr(user, "is_authenticated", False):
        return Class.objects.none()
    if not getattr(user, "is_staff", False):
        return Class.objects.none()
    if getattr(user, "is_superuser", False):
        return Class.objects.all()

    memberships = _active_memberships_queryset(user)
    if not memberships.exists():
        if _require_org_membership_for_staff():
            return Class.objects.none()
        return Class.objects.all()
    org_ids = memberships.values_list("organization_id", flat=True)
    return Class.objects.filter(organization_id__in=org_ids)


def staff_assigned_class_ids(user, *, class_ids: list[int] | None = None) -> set[int]:
    if not getattr(user, "is_authenticated", False):
        return set()
    if not getattr(user, "is_staff", False):
        return set()
    queryset = ClassStaffAssignment.objects.filter(user=user, is_active=True)
    if class_ids is not None:
        queryset = queryset.filter(classroom_id__in=class_ids)
    return set(int(cid) for cid in queryset.values_list("classroom_id", flat=True))


def staff_accessible_classes_ranked(user) -> tuple[list[Class], set[int]]:
    classes = list(staff_accessible_classes_queryset(user).order_by("name", "id"))
    if not classes:
        return classes, set()
    class_ids = [int(c.id) for c in classes]
    assigned_ids = staff_assigned_class_ids(user, class_ids=class_ids)
    classes.sort(key=lambda c: (0 if c.id in assigned_ids else 1, c.name.lower(), c.id))
    return classes, assigned_ids


def staff_classroom_or_none(user, class_id: int) -> Class | None:
    try:
        parsed_class_id = int(class_id)
    except Exception:
        return None
    if parsed_class_id <= 0:
        return None
    return staff_accessible_classes_queryset(user).filter(id=parsed_class_id).first()


def staff_can_access_classroom(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return bool(staff_classroom_or_none(user, classroom.id))


def staff_default_organization(user) -> Organization | None:
    if not getattr(user, "is_authenticated", False):
        return None
    if not getattr(user, "is_staff", False):
        return None
    memberships = _active_memberships_queryset(user).filter(role__in=_MANAGE_ROLES).select_related("organization")
    if not memberships.exists():
        return None
    role_rank = {
        OrganizationMembership.ROLE_OWNER: 0,
        OrganizationMembership.ROLE_ADMIN: 1,
        OrganizationMembership.ROLE_TEACHER: 2,
    }
    ranked = sorted(
        memberships,
        key=lambda m: (role_rank.get(m.role, 9), m.organization_id),
    )
    return ranked[0].organization


def staff_can_create_classes(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_staff", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    memberships = _active_memberships_queryset(user)
    if not memberships.exists():
        if _require_org_membership_for_staff():
            return False
        return True
    return memberships.filter(role__in=_MANAGE_ROLES).exists()


def staff_can_manage_classroom(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_staff", False):
        return False
    if getattr(user, "is_superuser", False):
        return True

    memberships = _active_memberships_queryset(user)
    if not memberships.exists():
        if _require_org_membership_for_staff():
            return False
        return True
    if classroom.organization_id is None:
        return False
    return memberships.filter(
        organization_id=classroom.organization_id,
        role__in=_MANAGE_ROLES,
    ).exists()


def staff_can_export_syllabi(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_staff", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    memberships = _active_memberships_queryset(user)
    if not memberships.exists():
        return False
    return memberships.filter(role__in=_SYLLABUS_EXPORT_ROLES).exists()


__all__ = [
    "staff_assigned_class_ids",
    "staff_accessible_classes_queryset",
    "staff_accessible_classes_ranked",
    "staff_can_export_syllabi",
    "staff_can_access_classroom",
    "staff_can_create_classes",
    "staff_can_manage_classroom",
    "staff_classroom_or_none",
    "staff_default_organization",
    "staff_has_explicit_memberships",
]
