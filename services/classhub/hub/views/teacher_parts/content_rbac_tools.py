"""Compatibility exports for RBAC teacher endpoints.

Primary implementation now lives in:
- content_rbac_view_endpoints.py
- content_rbac_payload_parsers.py
- content_rbac_mutation_actions.py
"""

from .content_rbac_view_endpoints import (
    build_rbac_tools_context,
    rbac_tools_enabled_for_user,
    rbac_tools_requested,
    teach_review_rbac_change_request,
    teach_set_module_scope_grant_active,
    teach_simulate_rbac_access,
    teach_upsert_custom_role,
    teach_upsert_custom_role_assignment,
    teach_upsert_custom_role_capability,
    teach_upsert_module_scope_grant,
)

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
