"""Organization-scoped staff access helpers.

Legacy compatibility:
- Staff users without explicit org memberships keep global class access.
- Once a user has active org memberships, class access is restricted to those orgs.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db.models import QuerySet

from ..models import Class, ClassStaffAssignment, Module, Organization, OrganizationMembership

CAP_CLASS_VIEW = "class.view"
CAP_CLASS_MANAGE = "class.manage"
CAP_CLASS_CREATE = "class.create"
CAP_ROSTER_MANAGE = "roster.manage"
CAP_SUBMISSION_VIEW = "submission.view"
CAP_SUBMISSION_DELETE = "submission.delete"
CAP_POLICY_MANAGE = "policy.manage"
CAP_SYLLABUS_EXPORT = "syllabus.export"

_KNOWN_CAPABILITIES = frozenset(
    {
        CAP_CLASS_VIEW,
        CAP_CLASS_MANAGE,
        CAP_CLASS_CREATE,
        CAP_ROSTER_MANAGE,
        CAP_SUBMISSION_VIEW,
        CAP_SUBMISSION_DELETE,
        CAP_POLICY_MANAGE,
        CAP_SYLLABUS_EXPORT,
    }
)

_ROLE_PRECEDENCE = (
    OrganizationMembership.ROLE_OWNER,
    OrganizationMembership.ROLE_ADMIN,
    OrganizationMembership.ROLE_TEACHER,
    OrganizationMembership.ROLE_VIEWER,
)

_ROLE_CAPABILITIES = {
    OrganizationMembership.ROLE_OWNER: frozenset(_KNOWN_CAPABILITIES),
    OrganizationMembership.ROLE_ADMIN: frozenset(_KNOWN_CAPABILITIES),
    OrganizationMembership.ROLE_TEACHER: frozenset(
        {
            CAP_CLASS_VIEW,
            CAP_CLASS_MANAGE,
            CAP_CLASS_CREATE,
            CAP_ROSTER_MANAGE,
            CAP_SUBMISSION_VIEW,
            CAP_SUBMISSION_DELETE,
            CAP_POLICY_MANAGE,
        }
    ),
    OrganizationMembership.ROLE_VIEWER: frozenset(
        {
            CAP_CLASS_VIEW,
            CAP_SUBMISSION_VIEW,
        }
    ),
}

_LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS = frozenset(
    {
        CAP_CLASS_VIEW,
        CAP_CLASS_MANAGE,
        CAP_CLASS_CREATE,
    }
)

_MANAGE_ROLES = {
    role
    for role, capabilities in _ROLE_CAPABILITIES.items()
    if CAP_CLASS_MANAGE in capabilities
}
_SYLLABUS_EXPORT_ROLES = {
    role
    for role, capabilities in _ROLE_CAPABILITIES.items()
    if CAP_SYLLABUS_EXPORT in capabilities
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


@dataclass(frozen=True)
class StaffCapabilityDecision:
    allowed: bool
    capability: str
    reason: str
    role: str = ""
    organization_id: int | None = None
    classroom_id: int | None = None
    module_id: int | None = None


def _module_scope_is_valid(*, classroom: Class | None, module_id: int | None) -> bool:
    if module_id is None:
        return True
    try:
        parsed_module_id = int(module_id)
    except Exception:
        return False
    if parsed_module_id <= 0:
        return False
    if classroom is None:
        return False
    return Module.objects.filter(id=parsed_module_id, classroom_id=classroom.id).exists()


def _highest_role_with_capability(*, roles: set[str], capability: str) -> str:
    for role in _ROLE_PRECEDENCE:
        if role in roles and capability in _ROLE_CAPABILITIES.get(role, ()):
            return role
    return ""


def evaluate_staff_capability(
    user,
    capability: str,
    *,
    classroom: Class | None = None,
    module_id: int | None = None,
) -> StaffCapabilityDecision:
    normalized_capability = (capability or "").strip().lower()
    if classroom is None:
        classroom_id = None
    else:
        try:
            classroom_id = int(classroom.id)
        except Exception:
            classroom_id = None
    if module_id is None:
        module_scope_id = None
    else:
        try:
            module_scope_id = int(module_id)
        except Exception:
            module_scope_id = -1

    if normalized_capability not in _KNOWN_CAPABILITIES:
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="unknown_capability",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if not getattr(user, "is_authenticated", False):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="unauthenticated",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )
    if not getattr(user, "is_staff", False):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="not_staff",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if not _module_scope_is_valid(classroom=classroom, module_id=module_scope_id):
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="invalid_module_scope",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if getattr(user, "is_superuser", False):
        return StaffCapabilityDecision(
            allowed=True,
            capability=normalized_capability,
            reason="superuser",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    memberships = _active_memberships_queryset(user)
    if not memberships.exists():
        if _require_org_membership_for_staff():
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="membership_required",
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        allowed = normalized_capability in _LEGACY_CAPABILITIES_WITHOUT_MEMBERSHIPS
        return StaffCapabilityDecision(
            allowed=allowed,
            capability=normalized_capability,
            reason="legacy_no_membership_fallback" if allowed else "legacy_no_membership_denied",
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )

    if classroom is not None:
        if classroom.organization_id is None:
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="classroom_missing_org",
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        memberships = memberships.filter(organization_id=classroom.organization_id)
        if not memberships.exists():
            return StaffCapabilityDecision(
                allowed=False,
                capability=normalized_capability,
                reason="no_membership_for_class_org",
                organization_id=classroom.organization_id,
                classroom_id=classroom_id,
                module_id=module_scope_id,
            )
        organization_id = int(classroom.organization_id)
    else:
        organization_id = None

    role_values = set(str(role) for role in memberships.values_list("role", flat=True))
    allowed_role = _highest_role_with_capability(roles=role_values, capability=normalized_capability)
    if not allowed_role:
        return StaffCapabilityDecision(
            allowed=False,
            capability=normalized_capability,
            reason="role_missing_capability",
            organization_id=organization_id,
            classroom_id=classroom_id,
            module_id=module_scope_id,
        )
    return StaffCapabilityDecision(
        allowed=True,
        capability=normalized_capability,
        reason="role_allows_capability",
        role=allowed_role,
        organization_id=organization_id,
        classroom_id=classroom_id,
        module_id=module_scope_id,
    )


def staff_can(
    user,
    capability: str,
    *,
    classroom: Class | None = None,
    module_id: int | None = None,
) -> bool:
    return evaluate_staff_capability(
        user,
        capability,
        classroom=classroom,
        module_id=module_id,
    ).allowed


def staff_can_access_classroom(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return staff_can(user, CAP_CLASS_VIEW, classroom=classroom)


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
    return staff_can(user, CAP_CLASS_CREATE)


def staff_can_manage_classroom(user, classroom: Class | None) -> bool:
    if classroom is None:
        return False
    return staff_can(user, CAP_CLASS_MANAGE, classroom=classroom)


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
    "staff_can_manage_classroom",
    "staff_classroom_or_none",
    "staff_default_organization",
    "staff_has_explicit_memberships",
]
