"""Shared helper utilities for RBAC view endpoints."""

from __future__ import annotations

from django.db.models import Q

from ...models import OrganizationMembership, RbacPolicyChangeRequest
from .shared import (
    _audit,
    _safe_internal_redirect,
    _with_notice,
    settings,
    staff_accessible_classes_ranked,
)

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


def rbac_policy_approval_required() -> bool:
    return bool(getattr(settings, "CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED", False))


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


def change_request_org_scope_id(change: RbacPolicyChangeRequest) -> int | None:
    if change.organization_id:
        return int(change.organization_id)
    if change.classroom_id and change.classroom and change.classroom.organization_id:
        return int(change.classroom.organization_id)
    return None


def can_review_change_request(*, reviewer, change: RbacPolicyChangeRequest) -> bool:
    if reviewer.is_superuser:
        return True
    org_id = change_request_org_scope_id(change)
    if org_id is None:
        return False
    return OrganizationMembership.objects.filter(
        user=reviewer,
        organization_id=org_id,
        role__in=(OrganizationMembership.ROLE_OWNER, OrganizationMembership.ROLE_ADMIN),
        is_active=True,
        organization__is_active=True,
    ).exists()


def rbac_pending_change_requests(*, classes):
    class_ids = [int(c.id) for c in classes]
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    queryset = RbacPolicyChangeRequest.objects.select_related(
        "requested_by",
        "reviewed_by",
        "organization",
        "classroom",
    ).filter(status=RbacPolicyChangeRequest.STATUS_PENDING)
    if class_ids and org_ids:
        queryset = queryset.filter(
            Q(classroom_id__in=class_ids)
            | Q(classroom__isnull=True, organization_id__in=org_ids)
        )
    elif class_ids:
        queryset = queryset.filter(classroom_id__in=class_ids)
    elif org_ids:
        queryset = queryset.filter(classroom__isnull=True, organization_id__in=org_ids)
    else:
        return []
    return list(queryset.order_by("-created_at", "-id")[:100])


def queue_policy_change_request(
    request,
    *,
    request_type: str,
    payload: dict,
    summary: str,
    classroom=None,
    organization=None,
):
    change = RbacPolicyChangeRequest.objects.create(
        request_type=request_type,
        status=RbacPolicyChangeRequest.STATUS_PENDING,
        requested_by=request.user,
        organization=organization,
        classroom=classroom,
        summary=summary[:255],
        payload=payload,
    )
    _audit(
        request,
        action="rbac.policy_change.requested",
        classroom=classroom,
        target_type="RbacPolicyChangeRequest",
        target_id=str(change.id),
        summary=f"Queued RBAC policy change request {change.request_type}",
        metadata={
            "request_id": change.id,
            "request_type": change.request_type,
            "organization_id": change.organization_id,
            "classroom_id": change.classroom_id,
        },
    )
    return change


def simulation_redirect_extra(decision):
    return {
        "rbac_sim_result": "1",
        "rbac_sim_allowed": "1" if decision.allowed else "0",
        "rbac_sim_reason": decision.reason,
        "rbac_sim_role": decision.role,
        "rbac_sim_org_id": str(decision.organization_id or ""),
        "rbac_sim_classroom_id": str(decision.classroom_id or ""),
        "rbac_sim_module_resolved": str(decision.module_id or ""),
    }


def scoped_change_request_or_none(*, actor_user, request_id: int):
    classes, _assigned = staff_accessible_classes_ranked(actor_user)
    class_ids = [int(c.id) for c in classes]
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    queryset = RbacPolicyChangeRequest.objects.select_related("requested_by", "organization", "classroom")
    if class_ids and org_ids:
        queryset = queryset.filter(
            Q(classroom_id__in=class_ids)
            | Q(classroom__isnull=True, organization_id__in=org_ids)
        )
    elif class_ids:
        queryset = queryset.filter(classroom_id__in=class_ids)
    elif org_ids:
        queryset = queryset.filter(classroom__isnull=True, organization_id__in=org_ids)
    else:
        return None
    return queryset.filter(id=request_id).first()


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
