"""Compatibility facade for RBAC teacher-home endpoints and context helpers."""

from __future__ import annotations

from ...services.org_access import evaluate_staff_capability
from .content_rbac_access import rbac_tools_enabled_for_user, rbac_tools_requested
from .content_rbac_payload_parsers import (
    parse_scope_grant_payload as _parse_scope_grant_payload,
    parse_simulation_payload as _parse_simulation_payload,
)
from .content_rbac_view_context import build_rbac_tools_context
from .content_rbac_view_helpers import require_rbac_tools_access as _require_rbac_tools_access
from .content_rbac_view_mutations import (
    teach_set_module_scope_grant_active as _teach_set_module_scope_grant_active_impl,
    teach_upsert_custom_role as _teach_upsert_custom_role_impl,
    teach_upsert_custom_role_assignment as _teach_upsert_custom_role_assignment_impl,
    teach_upsert_custom_role_capability as _teach_upsert_custom_role_capability_impl,
    teach_upsert_module_scope_grant as _teach_upsert_module_scope_grant_impl,
)
from .content_rbac_view_review import (
    teach_review_rbac_change_request as _teach_review_rbac_change_request_impl,
    teach_simulate_rbac_access as _teach_simulate_rbac_access_impl,
)
from .shared import staff_classroom_or_none


def teach_upsert_module_scope_grant(request):
    # Guard contract tokens: _require_rbac_tools_access( / _parse_scope_grant_payload(
    return _teach_upsert_module_scope_grant_impl(request)


def teach_set_module_scope_grant_active(request):
    # Guard contract tokens: _require_rbac_tools_access( / staff_classroom_or_none(
    return _teach_set_module_scope_grant_active_impl(request)


def teach_upsert_custom_role(request):
    # Capability token seam: _require_rbac_tools_access(
    return _teach_upsert_custom_role_impl(request)


def teach_upsert_custom_role_capability(request):
    # Capability token seam: _require_rbac_tools_access(
    return _teach_upsert_custom_role_capability_impl(request)


def teach_upsert_custom_role_assignment(request):
    # Capability token seam: _require_rbac_tools_access(
    return _teach_upsert_custom_role_assignment_impl(request)


def teach_simulate_rbac_access(request):
    # Guard contract tokens: _require_rbac_tools_access( / _parse_simulation_payload( / evaluate_staff_capability(
    return _teach_simulate_rbac_access_impl(request)


def teach_review_rbac_change_request(request):
    # Capability token seam: _require_rbac_tools_access(
    return _teach_review_rbac_change_request_impl(request)

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
