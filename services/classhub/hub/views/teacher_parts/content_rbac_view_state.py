"""RBAC tools state/redirect helper utilities for teacher home."""

from __future__ import annotations

from .shared import _safe_internal_redirect, _with_notice

RBAC_STATE_KEYS = (
    "rbac_class_id",
    "rbac_user_id",
    "rbac_capability",
    "rbac_effect",
    "rbac_module_start",
    "rbac_module_end",
    "rbac_grant_active",
    "rbac_sim_user_id",
    "rbac_sim_class_id",
    "rbac_sim_capability",
    "rbac_sim_module_id",
    "rbac_bulk_class_id",
    "rbac_bulk_capability",
    "rbac_bulk_module_id",
    "rbac_audit_action",
    "rbac_audit_class_id",
    "rbac_audit_limit",
    "rbac_custom_role_org_id",
    "rbac_custom_role_slug",
    "rbac_custom_role_name",
    "rbac_custom_role_description",
    "rbac_custom_role_active",
    "rbac_custom_role_cap_org_id",
    "rbac_custom_role_cap_slug",
    "rbac_custom_role_capability",
    "rbac_custom_role_cap_active",
    "rbac_custom_role_assign_org_id",
    "rbac_custom_role_assign_slug",
    "rbac_custom_role_assign_user_id",
    "rbac_custom_role_assign_active",
    "rbac_change_review_id",
    "rbac_change_review_decision",
    "rbac_change_review_note",
)

RBAC_STATE_DEFAULTS = {
    "rbac_grant_active": "1",
    "rbac_audit_action": "all",
    "rbac_audit_limit": "50",
    "rbac_custom_role_active": "1",
    "rbac_custom_role_cap_active": "1",
    "rbac_custom_role_assign_active": "1",
    "rbac_change_review_decision": "approve",
}


def rbac_state_extra(request, *, extra: dict | None = None) -> dict:
    payload = {"rbac_tools": "1"}
    for key in RBAC_STATE_KEYS:
        value = request.POST.get(key)
        if value is None:
            value = request.GET.get(key)
        text = (value or RBAC_STATE_DEFAULTS.get(key, "")).strip()
        if text:
            payload[key] = text
    payload.update(extra or {})
    return payload


def rbac_redirect(request, *, notice: str = "", error: str = "", extra: dict | None = None):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra=rbac_state_extra(request, extra=extra)),
        fallback="/teach",
    )


def require_rbac_tools_access(request, *, enabled_for_user):
    if enabled_for_user(request.user):
        return None
    return rbac_redirect(request, error="RBAC tools require superuser access.")


__all__ = [
    "rbac_redirect",
    "rbac_state_extra",
    "require_rbac_tools_access",
]
