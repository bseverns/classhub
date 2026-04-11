"""RBAC simulation and policy-review endpoint handlers."""

from __future__ import annotations

from django.db import transaction

from ...models import RbacPolicyChangeRequest
from ...services.org_access import evaluate_staff_capability
from .content_rbac_access import rbac_tools_enabled_for_user
from .content_rbac_mutation_actions import apply_change_request_approved as _apply_change_request_approved
from .content_rbac_payload_parsers import parse_simulation_payload as _parse_simulation_payload
from .content_rbac_view_helpers import (
    can_review_change_request,
    rbac_policy_approval_required,
    rbac_redirect,
    require_rbac_tools_access,
    scoped_change_request_or_none,
    simulation_redirect_extra,
)
from .shared import _audit, _parse_positive_int, require_POST, staff_member_required, timezone


@staff_member_required
@require_POST
def teach_simulate_rbac_access(request):
    denied = require_rbac_tools_access(request, enabled_for_user=rbac_tools_enabled_for_user)
    if denied is not None:
        return denied

    payload, error = _parse_simulation_payload(request)
    if payload is None:
        return rbac_redirect(request, error=error)

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
    return rbac_redirect(
        request,
        notice="RBAC simulation complete.",
        extra=simulation_redirect_extra(decision),
    )


@staff_member_required
@require_POST
def teach_review_rbac_change_request(request):
    if not rbac_policy_approval_required():
        return rbac_redirect(request, error="RBAC policy approval workflow is not enabled.")

    request_id = _parse_positive_int(request.POST.get("rbac_change_review_id") or "", min_value=1, max_value=2_147_483_647)
    if request_id is None:
        return rbac_redirect(request, error="Change request id is required.")
    decision = (request.POST.get("rbac_change_review_decision") or "").strip().lower()
    if decision not in {"approve", "reject"}:
        return rbac_redirect(request, error="Decision must be approve or reject.")
    review_note = (request.POST.get("rbac_change_review_note") or "").strip()[:500]

    change = scoped_change_request_or_none(actor_user=request.user, request_id=request_id)
    if change is None:
        return rbac_redirect(request, error="Change request not found.")
    if change.status != RbacPolicyChangeRequest.STATUS_PENDING:
        return rbac_redirect(request, error="Change request is already resolved.")
    if not (rbac_tools_enabled_for_user(request.user) or can_review_change_request(reviewer=request.user, change=change)):
        return rbac_redirect(request, error="Only org owners/admins (or superusers) can review change requests.")
    if change.requested_by_id == request.user.id:
        return rbac_redirect(request, error="Requesters cannot approve their own policy changes.")

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
        return rbac_redirect(request, notice=f"Rejected change request #{change.id}.")

    try:
        with transaction.atomic():
            apply_notice = _apply_change_request_approved(actor_user=request.user, change_request=change)
            change.status = RbacPolicyChangeRequest.STATUS_APPROVED
            change.reviewed_by = request.user
            change.reviewed_at = timezone.now()
            change.review_note = review_note
            change.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    except ValueError as exc:
        return rbac_redirect(request, error=str(exc))

    _audit(
        request,
        action="rbac.policy_change.approved",
        classroom=change.classroom,
        target_type="RbacPolicyChangeRequest",
        target_id=str(change.id),
        summary=f"Approved RBAC policy change request {change.request_type}",
        metadata={"request_type": change.request_type, "review_note": review_note},
    )
    return rbac_redirect(request, notice=f"Approved change request #{change.id}. {apply_notice}")


__all__ = [
    "teach_review_rbac_change_request",
    "teach_simulate_rbac_access",
]
