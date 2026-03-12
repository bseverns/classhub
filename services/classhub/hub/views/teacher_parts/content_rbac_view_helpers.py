"""Compatibility facade for RBAC teacher-home helper utilities."""

from __future__ import annotations

from .content_rbac_view_change_requests import (
    can_review_change_request,
    queue_policy_change_request,
    rbac_pending_change_requests,
    rbac_policy_approval_required,
    scoped_change_request_or_none,
    simulation_redirect_extra,
)
from .content_rbac_view_state import (
    rbac_redirect,
    rbac_state_extra,
    require_rbac_tools_access,
)

__all__ = [
    "can_review_change_request",
    "queue_policy_change_request",
    "rbac_pending_change_requests",
    "rbac_policy_approval_required",
    "rbac_redirect",
    "rbac_state_extra",
    "require_rbac_tools_access",
    "scoped_change_request_or_none",
    "simulation_redirect_extra",
]
