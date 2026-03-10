"""RBAC tools for teacher home (scoped grants + simulation + custom roles)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from ...models import (
    ClassStaffModuleScopeGrant,
    Organization,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationMembership,
    OrganizationRoleCapability,
    RbacPolicyChangeRequest,
)
from ...services.org_access import evaluate_staff_capability
from .content_rbac_audit import build_rbac_audit_context
from .content_rbac_bulk import build_bulk_simulation_result
from .content_rbac_mutation_actions import (
    apply_change_request_approved as _apply_change_request_approved,
    apply_custom_role_assignment_upsert as _apply_custom_role_assignment_upsert,
    apply_custom_role_capability_upsert as _apply_custom_role_capability_upsert,
    apply_custom_role_upsert as _apply_custom_role_upsert,
    apply_scope_grant_set_active as _apply_scope_grant_set_active,
    apply_scope_grant_upsert as _apply_scope_grant_upsert,
)
from .content_rbac_payload_parsers import (
    SIMULATION_CAPABILITY_VALUES as _SIMULATION_CAPABILITY_VALUES,
    parse_custom_role_assignment_payload as _parse_custom_role_assignment_payload,
    parse_custom_role_capability_payload as _parse_custom_role_capability_payload,
    parse_custom_role_upsert_payload as _parse_custom_role_upsert_payload,
    parse_scope_grant_payload as _parse_scope_grant_payload,
    parse_simulation_payload as _parse_simulation_payload,
    resolve_accessible_org_for_user as _resolve_accessible_org_for_user,
)
from .content_rbac_state import (
    rbac_form_state,
    rbac_scope_grants,
    rbac_simulation_result,
    rbac_staff_users,
)
from .shared import (
    _audit,
    _parse_positive_int,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    settings,
    staff_accessible_classes_ranked,
    staff_can_export_syllabi,
    staff_classroom_or_none,
    staff_member_required,
    timezone,
)

_RBAC_STATE_KEYS = (
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

_RBAC_STATE_DEFAULTS = {
    "rbac_grant_active": "1",
    "rbac_audit_action": "all",
    "rbac_audit_limit": "50",
    "rbac_custom_role_active": "1",
    "rbac_custom_role_cap_active": "1",
    "rbac_custom_role_assign_active": "1",
    "rbac_change_review_decision": "approve",
}


def rbac_tools_enabled_for_user(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def rbac_tools_requested(request) -> bool:
    return (request.GET.get("rbac_tools") or "").strip() == "1"


def _rbac_policy_approval_required() -> bool:
    return bool(getattr(settings, "CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED", False))


def _rbac_state_extra(request, *, extra: dict | None = None) -> dict:
    payload = {"rbac_tools": "1"}
    for key in _RBAC_STATE_KEYS:
        value = request.POST.get(key)
        if value is None:
            value = request.GET.get(key)
        text = (value or _RBAC_STATE_DEFAULTS.get(key, "")).strip()
        if text:
            payload[key] = text
    payload.update(extra or {})
    return payload


def _rbac_redirect(request, *, notice: str = "", error: str = "", extra: dict | None = None):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra=_rbac_state_extra(request, extra=extra)),
        fallback="/teach",
    )


def _change_request_org_scope_id(change: RbacPolicyChangeRequest) -> int | None:
    if change.organization_id:
        return int(change.organization_id)
    if change.classroom_id and change.classroom and change.classroom.organization_id:
        return int(change.classroom.organization_id)
    return None


def _can_review_change_request(*, reviewer, change: RbacPolicyChangeRequest) -> bool:
    if reviewer.is_superuser:
        return True
    org_id = _change_request_org_scope_id(change)
    if org_id is None:
        return False
    return OrganizationMembership.objects.filter(
        user=reviewer,
        organization_id=org_id,
        role__in=(OrganizationMembership.ROLE_OWNER, OrganizationMembership.ROLE_ADMIN),
        is_active=True,
        organization__is_active=True,
    ).exists()


def _rbac_pending_change_requests(*, classes):
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


def _queue_policy_change_request(
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


def build_rbac_tools_context(*, request, classes) -> dict:
    if not rbac_tools_enabled_for_user(request.user):
        return {
            "rbac_tools_enabled": False,
            "rbac_tools_active": False,
        }
    state = rbac_form_state(request)
    staff_users = rbac_staff_users(classes)
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    organizations = list(
        Organization.objects.filter(id__in=org_ids, is_active=True).order_by("name", "id").only("id", "name")
    )
    custom_roles = list(
        OrganizationCustomRole.objects.select_related("organization")
        .prefetch_related("capabilities")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "slug", "id")
    )
    custom_role_assignments = list(
        OrganizationCustomRoleAssignment.objects.select_related("organization", "role", "user")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "role__slug", "user__username", "id")
    )
    bulk_simulation_result = build_bulk_simulation_result(
        request=request,
        capability_values=_SIMULATION_CAPABILITY_VALUES,
        staff_users=staff_users,
        state=state,
    )
    audit_context = build_rbac_audit_context(classes=classes, state=state)

    return {
        "rbac_tools_enabled": True,
        "rbac_tools_active": rbac_tools_requested(request),
        "rbac_classes": classes,
        "rbac_orgs": organizations,
        "rbac_staff_users": staff_users,
        "rbac_scope_grants": rbac_scope_grants(classes),
        "rbac_custom_roles": custom_roles,
        "rbac_custom_role_assignments": custom_role_assignments,
        "rbac_pending_change_requests": _rbac_pending_change_requests(classes=classes),
        "rbac_policy_approval_required": _rbac_policy_approval_required(),
        "rbac_scoped_capability_choices": ClassStaffModuleScopeGrant.CAPABILITY_CHOICES,
        "rbac_simulation_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        "rbac_effect_choices": ClassStaffModuleScopeGrant.EFFECT_CHOICES,
        "rbac_custom_role_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        **state,
        "rbac_simulation_result": rbac_simulation_result(request),
        "rbac_bulk_simulation_result": bulk_simulation_result,
        **audit_context,
    }


def _require_rbac_tools_access(request):
    if staff_can_export_syllabi(request.user):
        return None
    return _rbac_redirect(request, error="RBAC tools require owner/admin role.")


@staff_member_required
@require_POST
def teach_upsert_module_scope_grant(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied

    payload, error = _parse_scope_grant_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    if _rbac_policy_approval_required():
        change = _queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_UPSERT,
            payload=payload,
            summary=f"Scoped grant upsert {payload['capability']} ({payload['effect']})",
            classroom=staff_classroom_or_none(request.user, payload["classroom_id"]),
        )
        return _rbac_redirect(request, notice=f"Scoped grant request queued (#{change.id}).")

    grant, created = _apply_scope_grant_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="rbac.scope_grant.portal_upsert",
        classroom=grant.classroom,
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal upsert scoped grant {grant.capability} ({grant.effect})",
        metadata={
            "created": bool(created),
            "user_id": grant.user_id,
            "capability": grant.capability,
            "effect": grant.effect,
            "module_order_start": grant.module_order_start,
            "module_order_end": grant.module_order_end,
            "is_active": bool(grant.is_active),
        },
    )
    return _rbac_redirect(request, notice="Scoped grant saved.")


@staff_member_required
@require_POST
def teach_set_module_scope_grant_active(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied

    payload = {
        "grant_id": request.POST.get("rbac_grant_id") or "",
        "is_active": (request.POST.get("rbac_grant_active") or "0").strip() == "1",
    }
    grant_id = _parse_positive_int(str(payload.get("grant_id") or ""), min_value=1, max_value=2_147_483_647)
    if grant_id is None:
        return _rbac_redirect(request, error="Grant id is required.")
    grant = ClassStaffModuleScopeGrant.objects.select_related("classroom").filter(id=grant_id).first()
    if grant is None:
        return _rbac_redirect(request, error="Grant not found.")
    if staff_classroom_or_none(request.user, grant.classroom_id) is None:
        return _rbac_redirect(request, error="Class not found.")

    if _rbac_policy_approval_required():
        change = _queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_SCOPE_GRANT_SET_ACTIVE,
            payload=payload,
            summary=f"Scoped grant set active={payload['is_active']}",
            classroom=grant.classroom,
        )
        return _rbac_redirect(request, notice=f"Scoped grant status request queued (#{change.id}).")

    try:
        grant = _apply_scope_grant_set_active(actor_user=request.user, payload=payload)
    except ValueError as exc:
        return _rbac_redirect(request, error=str(exc))
    _audit(
        request,
        action="rbac.scope_grant.portal_set_active",
        classroom=grant.classroom,
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal set scoped grant active={grant.is_active}",
        metadata={"is_active": bool(grant.is_active)},
    )
    return _rbac_redirect(request, notice="Scoped grant status updated.")


@staff_member_required
@require_POST
def teach_upsert_custom_role(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_upsert_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    if _rbac_policy_approval_required():
        change = _queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT,
            payload=payload,
            summary=f"Custom role upsert {payload['slug']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return _rbac_redirect(request, notice=f"Custom role request queued (#{change.id}).")

    role, created = _apply_custom_role_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role.portal_upsert",
        target_type="OrganizationCustomRole",
        target_id=str(role.id),
        summary=f"Portal upsert custom role {role.slug}",
        metadata={
            "organization_id": role.organization_id,
            "slug": role.slug,
            "created": bool(created),
            "is_active": bool(role.is_active),
        },
    )
    return _rbac_redirect(request, notice="Custom role saved.")


@staff_member_required
@require_POST
def teach_upsert_custom_role_capability(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_capability_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    if _rbac_policy_approval_required():
        change = _queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_CAPABILITY_UPSERT,
            payload=payload,
            summary=f"Custom role capability upsert {payload['slug']} -> {payload['capability']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return _rbac_redirect(request, notice=f"Custom role capability request queued (#{change.id}).")

    row, created = _apply_custom_role_capability_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role_capability.portal_upsert",
        target_type="OrganizationCustomRoleCapability",
        target_id=str(row.id),
        summary=f"Portal upsert custom role capability {row.role.slug} -> {row.capability}",
        metadata={
            "organization_id": row.role.organization_id,
            "role_slug": row.role.slug,
            "capability": row.capability,
            "created": bool(created),
            "is_active": bool(row.is_active),
        },
    )
    return _rbac_redirect(request, notice="Custom role capability saved.")


@staff_member_required
@require_POST
def teach_upsert_custom_role_assignment(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    payload, error = _parse_custom_role_assignment_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    if _rbac_policy_approval_required():
        change = _queue_policy_change_request(
            request,
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_ASSIGNMENT_UPSERT,
            payload=payload,
            summary=f"Custom role assignment upsert {payload['slug']}",
            organization=_resolve_accessible_org_for_user(request.user, str(payload["organization_id"])),
        )
        return _rbac_redirect(request, notice=f"Custom role assignment request queued (#{change.id}).")

    assignment, created = _apply_custom_role_assignment_upsert(actor_user=request.user, payload=payload)
    _audit(
        request,
        action="organization.custom_role_assignment.portal_upsert",
        target_type="OrganizationCustomRoleAssignment",
        target_id=str(assignment.id),
        summary=f"Portal upsert custom role assignment for user {assignment.user_id}",
        metadata={
            "organization_id": assignment.organization_id,
            "role_slug": assignment.role.slug,
            "user_id": assignment.user_id,
            "created": bool(created),
            "is_active": bool(assignment.is_active),
        },
    )
    return _rbac_redirect(request, notice="Custom role assignment saved.")


def _simulation_redirect_extra(decision):
    return {
        "rbac_sim_result": "1",
        "rbac_sim_allowed": "1" if decision.allowed else "0",
        "rbac_sim_reason": decision.reason,
        "rbac_sim_role": decision.role,
        "rbac_sim_org_id": str(decision.organization_id or ""),
        "rbac_sim_classroom_id": str(decision.classroom_id or ""),
        "rbac_sim_module_resolved": str(decision.module_id or ""),
    }


@staff_member_required
@require_POST
def teach_simulate_rbac_access(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied

    payload, error = _parse_simulation_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    decision = evaluate_staff_capability(
        payload["target_user"],
        payload["capability"],
        classroom=payload["classroom"],
        module_id=payload["module_id"],
    )
    _audit(
        request,
        action="rbac.simulate.portal",
        classroom=payload["classroom"],
        target_type="User",
        target_id=str(payload["target_user"].id),
        summary=f"Portal simulated RBAC decision for user {payload['target_user'].id}",
        metadata={
            "capability": payload["capability"],
            "class_id": payload["classroom"].id if payload["classroom"] else None,
            "module_id": payload["module_id"],
            "decision": {
                "allowed": bool(decision.allowed),
                "reason": decision.reason,
                "role": decision.role,
                "organization_id": decision.organization_id,
                "classroom_id": decision.classroom_id,
                "module_id": decision.module_id,
            },
        },
    )
    return _rbac_redirect(
        request,
        notice="RBAC simulation complete.",
        extra=_simulation_redirect_extra(decision),
    )


def _scoped_change_request_or_none(*, actor_user, request_id: int):
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


@staff_member_required
@require_POST
def teach_review_rbac_change_request(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied
    if not _rbac_policy_approval_required():
        return _rbac_redirect(request, error="RBAC policy approval workflow is not enabled.")

    request_id = _parse_positive_int(request.POST.get("rbac_change_review_id") or "", min_value=1, max_value=2_147_483_647)
    if request_id is None:
        return _rbac_redirect(request, error="Change request id is required.")
    decision = (request.POST.get("rbac_change_review_decision") or "").strip().lower()
    if decision not in {"approve", "reject"}:
        return _rbac_redirect(request, error="Decision must be approve or reject.")
    review_note = (request.POST.get("rbac_change_review_note") or "").strip()[:500]

    change = _scoped_change_request_or_none(actor_user=request.user, request_id=request_id)
    if change is None:
        return _rbac_redirect(request, error="Change request not found.")
    if change.status != RbacPolicyChangeRequest.STATUS_PENDING:
        return _rbac_redirect(request, error="Change request is already resolved.")
    if change.requested_by_id == request.user.id:
        return _rbac_redirect(request, error="Requesters cannot approve their own policy changes.")
    if not _can_review_change_request(reviewer=request.user, change=change):
        return _rbac_redirect(request, error="Only org owners/admins (or superusers) can review change requests.")

    if decision == "reject":
        change.status = RbacPolicyChangeRequest.STATUS_REJECTED
        change.reviewed_by = request.user
        change.reviewed_at = timezone.now()
        change.review_note = review_note
        change.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
        _audit(
            request,
            action="rbac.policy_change.rejected",
            classroom=change.classroom,
            target_type="RbacPolicyChangeRequest",
            target_id=str(change.id),
            summary=f"Rejected RBAC policy change request {change.request_type}",
            metadata={"request_type": change.request_type, "review_note": review_note},
        )
        return _rbac_redirect(request, notice=f"Rejected change request #{change.id}.")

    try:
        with transaction.atomic():
            apply_notice = _apply_change_request_approved(actor_user=request.user, change_request=change)
            change.status = RbacPolicyChangeRequest.STATUS_APPROVED
            change.reviewed_by = request.user
            change.reviewed_at = timezone.now()
            change.review_note = review_note
            change.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    except ValueError as exc:
        return _rbac_redirect(request, error=str(exc))

    _audit(
        request,
        action="rbac.policy_change.approved",
        classroom=change.classroom,
        target_type="RbacPolicyChangeRequest",
        target_id=str(change.id),
        summary=f"Approved RBAC policy change request {change.request_type}",
        metadata={"request_type": change.request_type, "review_note": review_note},
    )
    return _rbac_redirect(request, notice=f"Approved change request #{change.id}. {apply_notice}")


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
