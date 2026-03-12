"""Organization-scoped staff access helpers.

Default posture:
- Production-safe mode requires active org memberships for staff class access.

Fallback compatibility:
- If `REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=0`, staff users without memberships keep
  legacy global class access.
- Once a user has active org memberships, class access is restricted to those orgs.
"""

from __future__ import annotations

from django.db.models import QuerySet

from ..models import Class, ClassStaffAssignment
from .org_access_capabilities import (
    CAP_CLASS_CREATE,
    CAP_CLASS_MANAGE,
    CAP_CLASS_VIEW,
    CAP_POLICY_MANAGE,
    CAP_ROSTER_MANAGE,
    CAP_SUBMISSION_DELETE,
    CAP_SUBMISSION_VIEW,
    CAP_SYLLABUS_EXPORT,
    StaffCapabilityDecision,
    active_staff_memberships_queryset,
    evaluate_staff_capability,
    require_org_membership_for_staff,
    staff_can,
    staff_default_organization,
)


def staff_has_explicit_memberships(user) -> bool:
    return active_staff_memberships_queryset(user).exists()


def staff_accessible_classes_queryset(user) -> QuerySet[Class]:
    if not getattr(user, "is_authenticated", False):
        return Class.objects.none()
    if not getattr(user, "is_staff", False):
        return Class.objects.none()
    if getattr(user, "is_superuser", False):
        return Class.objects.all()

    memberships = active_staff_memberships_queryset(user)
    if not memberships.exists():
        if require_org_membership_for_staff():
            # Strict boundary mode still exposes legacy unscoped classes so
            # older deployments can operate while org bindings are completed.
            return Class.objects.filter(organization__isnull=True)
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
    return staff_can(user, CAP_CLASS_VIEW, classroom=classroom)


def staff_can_create_classes(user) -> bool:
    return staff_can(user, CAP_CLASS_CREATE)


def staff_can_manage_classroom(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return staff_can(user, CAP_CLASS_MANAGE, classroom=classroom)


def staff_can_manage_roster(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return staff_can(user, CAP_ROSTER_MANAGE, classroom=classroom)


def staff_can_manage_policy(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return staff_can(user, CAP_POLICY_MANAGE, classroom=classroom)


def staff_can_view_submissions(
    user,
    classroom: Class | None,
    *,
    module_id: int | None = None,
) -> bool:
    if classroom is None:
        return False
    return staff_can(
        user,
        CAP_SUBMISSION_VIEW,
        classroom=classroom,
        module_id=module_id,
    )


def staff_can_delete_submissions(
    user,
    classroom: Class | None,
    *,
    module_id: int | None = None,
) -> bool:
    if classroom is None:
        return False
    return staff_can(
        user,
        CAP_SUBMISSION_DELETE,
        classroom=classroom,
        module_id=module_id,
    )


def staff_can_export_syllabi(user) -> bool:
    return staff_can(user, CAP_SYLLABUS_EXPORT)


__all__ = [
    "CAP_CLASS_CREATE",
    "CAP_CLASS_MANAGE",
    "CAP_CLASS_VIEW",
    "CAP_POLICY_MANAGE",
    "CAP_ROSTER_MANAGE",
    "CAP_SUBMISSION_DELETE",
    "CAP_SUBMISSION_VIEW",
    "CAP_SYLLABUS_EXPORT",
    "StaffCapabilityDecision",
    "evaluate_staff_capability",
    "staff_can",
    "staff_assigned_class_ids",
    "staff_accessible_classes_queryset",
    "staff_accessible_classes_ranked",
    "staff_can_export_syllabi",
    "staff_can_access_classroom",
    "staff_can_create_classes",
    "staff_can_delete_submissions",
    "staff_can_manage_classroom",
    "staff_can_manage_policy",
    "staff_can_manage_roster",
    "staff_can_view_submissions",
    "staff_classroom_or_none",
    "staff_default_organization",
    "staff_has_explicit_memberships",
]
