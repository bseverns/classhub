"""Compatibility facade for RBAC teacher-home endpoints and context helpers."""

from __future__ import annotations

from .content_rbac_access import rbac_tools_enabled_for_user, rbac_tools_requested
from .content_rbac_view_context import build_rbac_tools_context
from .content_rbac_view_mutations import (
    teach_set_module_scope_grant_active,
    teach_upsert_custom_role,
    teach_upsert_custom_role_assignment,
    teach_upsert_custom_role_capability,
    teach_upsert_module_scope_grant,
)
from .content_rbac_view_review import teach_review_rbac_change_request, teach_simulate_rbac_access

__all__ = [
    "build_rbac_tools_context",
    "rbac_tools_enabled_for_user",
    "rbac_tools_requested",
    "teach_review_rbac_change_request",
    "teach_set_module_scope_grant_active",
    "teach_simulate_rbac_access",
    "teach_upsert_custom_role",
    "teach_upsert_custom_role_assignment",
    "teach_upsert_custom_role_capability",
    "teach_upsert_module_scope_grant",
]
