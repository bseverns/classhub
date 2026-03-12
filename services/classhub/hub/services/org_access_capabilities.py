"""Capability policy public API for organization-scoped staff access.

This module remains the stable import surface while evaluation internals are
split into dedicated modules.
"""

from __future__ import annotations

from .org_access_capabilities_policy import (
    evaluate_staff_capability,
    staff_can,
    staff_default_organization,
)
from .org_access_capabilities_shared import (
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
    require_org_membership_for_staff,
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
    "StaffCapabilityDecision",
    "active_staff_memberships_queryset",
    "evaluate_staff_capability",
    "require_org_membership_for_staff",
    "staff_can",
    "staff_default_organization",
]
