"""Shared constants and primitives for org access capability evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db.models import QuerySet

from ..models import OrganizationMembership

CAP_CLASS_VIEW = "class.view"
CAP_CLASS_MANAGE = "class.manage"
CAP_CLASS_CREATE = "class.create"
CAP_ROSTER_MANAGE = "roster.manage"
CAP_SUBMISSION_VIEW = "submission.view"
CAP_SUBMISSION_DELETE = "submission.delete"
CAP_POLICY_MANAGE = "policy.manage"
CAP_SYLLABUS_EXPORT = "syllabus.export"

KNOWN_CAPABILITIES = frozenset(
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


@dataclass(frozen=True)
class StaffCapabilityDecision:
    allowed: bool
    capability: str
    reason: str
    role: str = ""
    organization_id: int | None = None
    classroom_id: int | None = None
    module_id: int | None = None


def require_org_membership_for_staff() -> bool:
    return bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False))


def scoped_module_grants_enabled() -> bool:
    return bool(getattr(settings, "CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED", False))


def active_staff_memberships_queryset(user) -> QuerySet[OrganizationMembership]:
    if not getattr(user, "is_authenticated", False):
        return OrganizationMembership.objects.none()
    if not getattr(user, "is_staff", False):
        return OrganizationMembership.objects.none()
    return OrganizationMembership.objects.filter(
        user=user,
        is_active=True,
        organization__is_active=True,
    )


__all__ = [
    "CAP_CLASS_CREATE",
    "CAP_CLASS_MANAGE",
    "CAP_CLASS_VIEW",
    "CAP_POLICY_MANAGE",
    "CAP_ROSTER_MANAGE",
    "CAP_SUBMISSION_DELETE",
    "CAP_SUBMISSION_VIEW",
    "CAP_SYLLABUS_EXPORT",
    "KNOWN_CAPABILITIES",
    "StaffCapabilityDecision",
    "active_staff_memberships_queryset",
    "require_org_membership_for_staff",
    "scoped_module_grants_enabled",
]
