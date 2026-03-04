"""RBAC tools for teacher home (scoped grants + simulation)."""

from ...models import ClassStaffModuleScopeGrant, OrganizationMembership
from ...services.org_access import evaluate_staff_capability
from .content_rbac_bulk import build_bulk_simulation_result
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
    get_user_model,
    require_POST,
    staff_can_export_syllabi,
    staff_classroom_or_none,
    staff_member_required,
)


_CAPABILITY_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.CAPABILITY_CHOICES}
_EFFECT_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.EFFECT_CHOICES}


def rbac_tools_enabled_for_user(user) -> bool:
    return staff_can_export_syllabi(user)


def rbac_tools_requested(request) -> bool:
    return (request.GET.get("rbac_tools") or "").strip() == "1"


def _rbac_state_extra(request, *, extra: dict | None = None) -> dict:
    payload = {
        "rbac_tools": "1",
        "rbac_class_id": (request.POST.get("rbac_class_id") or request.GET.get("rbac_class_id") or "").strip(),
        "rbac_user_id": (request.POST.get("rbac_user_id") or request.GET.get("rbac_user_id") or "").strip(),
        "rbac_capability": (request.POST.get("rbac_capability") or request.GET.get("rbac_capability") or "").strip(),
        "rbac_effect": (request.POST.get("rbac_effect") or request.GET.get("rbac_effect") or "").strip(),
        "rbac_module_start": (request.POST.get("rbac_module_start") or request.GET.get("rbac_module_start") or "").strip(),
        "rbac_module_end": (request.POST.get("rbac_module_end") or request.GET.get("rbac_module_end") or "").strip(),
        "rbac_grant_active": (request.POST.get("rbac_grant_active") or request.GET.get("rbac_grant_active") or "1").strip(),
        "rbac_sim_user_id": (request.POST.get("rbac_sim_user_id") or request.GET.get("rbac_sim_user_id") or "").strip(),
        "rbac_sim_class_id": (request.POST.get("rbac_sim_class_id") or request.GET.get("rbac_sim_class_id") or "").strip(),
        "rbac_sim_capability": (request.POST.get("rbac_sim_capability") or request.GET.get("rbac_sim_capability") or "").strip(),
        "rbac_sim_module_id": (request.POST.get("rbac_sim_module_id") or request.GET.get("rbac_sim_module_id") or "").strip(),
        "rbac_bulk_class_id": (request.POST.get("rbac_bulk_class_id") or request.GET.get("rbac_bulk_class_id") or "").strip(),
        "rbac_bulk_capability": (
            request.POST.get("rbac_bulk_capability") or request.GET.get("rbac_bulk_capability") or ""
        ).strip(),
        "rbac_bulk_module_id": (request.POST.get("rbac_bulk_module_id") or request.GET.get("rbac_bulk_module_id") or "").strip(),
    }
    payload.update(extra or {})
    return payload


def _rbac_redirect(request, *, notice: str = "", error: str = "", extra: dict | None = None):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra=_rbac_state_extra(request, extra=extra)),
        fallback="/teach",
    )


def _resolve_staff_user(user_id_raw: str):
    user_id = _parse_positive_int(user_id_raw, min_value=1, max_value=2_147_483_647)
    if user_id is None:
        return None
    User = get_user_model()
    return User.objects.filter(id=user_id, is_staff=True, is_active=True).only("id", "username").first()


def _target_user_has_org_membership(user, *, classroom) -> bool:
    if user.is_superuser:
        return True
    if not classroom.organization_id:
        return True
    return OrganizationMembership.objects.filter(
        user=user,
        organization_id=classroom.organization_id,
        is_active=True,
        organization__is_active=True,
    ).exists()


def build_rbac_tools_context(*, request, classes) -> dict:
    if not rbac_tools_enabled_for_user(request.user):
        return {
            "rbac_tools_enabled": False,
            "rbac_tools_active": False,
        }
    state = rbac_form_state(request)
    staff_users = rbac_staff_users(classes)
    bulk_simulation_result = build_bulk_simulation_result(
        request=request,
        capability_values=_CAPABILITY_VALUES,
        staff_users=staff_users,
        state=state,
    )

    return {
        "rbac_tools_enabled": True,
        "rbac_tools_active": rbac_tools_requested(request),
        "rbac_classes": classes,
        "rbac_staff_users": staff_users,
        "rbac_scope_grants": rbac_scope_grants(classes),
        "rbac_capability_choices": ClassStaffModuleScopeGrant.CAPABILITY_CHOICES,
        "rbac_effect_choices": ClassStaffModuleScopeGrant.EFFECT_CHOICES,
        **state,
        "rbac_simulation_result": rbac_simulation_result(request),
        "rbac_bulk_simulation_result": bulk_simulation_result,
    }


def _require_rbac_tools_access(request):
    if staff_can_export_syllabi(request.user):
        return None
    return _rbac_redirect(request, error="RBAC tools require owner/admin role.")


def _parse_scope_grant_payload(request):
    classroom = staff_classroom_or_none(request.user, request.POST.get("rbac_class_id"))
    if classroom is None:
        return None, "Class is required."

    target_user = _resolve_staff_user(request.POST.get("rbac_user_id") or "")
    if target_user is None:
        return None, "Staff user is required."
    if not _target_user_has_org_membership(target_user, classroom=classroom):
        return None, "Target user must be active in the class organization."

    capability = (request.POST.get("rbac_capability") or "").strip()
    if capability not in _CAPABILITY_VALUES:
        return None, "Unsupported capability."

    effect = (request.POST.get("rbac_effect") or "").strip()
    if effect not in _EFFECT_VALUES:
        return None, "Unsupported grant effect."

    module_start = _parse_positive_int(request.POST.get("rbac_module_start") or "", min_value=0, max_value=50_000)
    module_end = _parse_positive_int(request.POST.get("rbac_module_end") or "", min_value=0, max_value=50_000)
    if module_start is None or module_end is None:
        return None, "Module range must be whole numbers."
    if module_end < module_start:
        return None, "Module end must be greater than or equal to module start."
    return {
        "classroom": classroom,
        "target_user": target_user,
        "capability": capability,
        "effect": effect,
        "module_start": module_start,
        "module_end": module_end,
        "is_active": (request.POST.get("rbac_grant_active") or "0").strip() == "1",
    }, ""


def _upsert_scope_grant(payload: dict):
    grant, created = ClassStaffModuleScopeGrant.objects.get_or_create(
        classroom=payload["classroom"],
        user=payload["target_user"],
        capability=payload["capability"],
        effect=payload["effect"],
        module_order_start=payload["module_start"],
        module_order_end=payload["module_end"],
        defaults={"is_active": payload["is_active"]},
    )
    if not created and grant.is_active != payload["is_active"]:
        grant.is_active = payload["is_active"]
        grant.save(update_fields=["is_active", "updated_at"])
    return grant, created


@staff_member_required
@require_POST
def teach_upsert_module_scope_grant(request):
    denied = _require_rbac_tools_access(request)
    if denied is not None:
        return denied

    payload, error = _parse_scope_grant_payload(request)
    if payload is None:
        return _rbac_redirect(request, error=error)

    grant, created = _upsert_scope_grant(payload)

    _audit(
        request,
        action="rbac.scope_grant.portal_upsert",
        classroom=payload["classroom"],
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal upsert scoped grant {payload['capability']} ({payload['effect']})",
        metadata={
            "created": bool(created),
            "user_id": payload["target_user"].id,
            "capability": payload["capability"],
            "effect": payload["effect"],
            "module_order_start": payload["module_start"],
            "module_order_end": payload["module_end"],
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

    grant_id = _parse_positive_int(request.POST.get("rbac_grant_id") or "", min_value=1, max_value=2_147_483_647)
    if grant_id is None:
        return _rbac_redirect(request, error="Grant id is required.")
    grant = ClassStaffModuleScopeGrant.objects.select_related("classroom").filter(id=grant_id).first()
    if grant is None:
        return _rbac_redirect(request, error="Grant not found.")
    if staff_classroom_or_none(request.user, grant.classroom_id) is None:
        return _rbac_redirect(request, error="Class not found.")

    is_active = (request.POST.get("rbac_grant_active") or "0").strip() == "1"
    if grant.is_active != is_active:
        grant.is_active = is_active
        grant.save(update_fields=["is_active", "updated_at"])

    _audit(
        request,
        action="rbac.scope_grant.portal_set_active",
        classroom=grant.classroom,
        target_type="ClassStaffModuleScopeGrant",
        target_id=str(grant.id),
        summary=f"Portal set scoped grant active={is_active}",
        metadata={"is_active": bool(is_active)},
    )
    return _rbac_redirect(request, notice="Scoped grant status updated.")


def _parse_simulation_payload(request):
    target_user = _resolve_staff_user(request.POST.get("rbac_sim_user_id") or "")
    if target_user is None:
        return None, "Simulation target staff user is required."

    capability = (request.POST.get("rbac_sim_capability") or "").strip().lower()
    if capability not in _CAPABILITY_VALUES:
        return None, "Simulation capability must be submission.view or submission.delete."

    classroom = None
    class_id_raw = (request.POST.get("rbac_sim_class_id") or "").strip()
    if class_id_raw:
        classroom = staff_classroom_or_none(request.user, class_id_raw)
        if classroom is None:
            return None, "Simulation class not found."

    module_id = None
    module_id_raw = (request.POST.get("rbac_sim_module_id") or "").strip()
    if module_id_raw:
        module_id = _parse_positive_int(module_id_raw, min_value=1, max_value=2_147_483_647)
        if module_id is None:
            return None, "Simulation module id must be a positive integer."
        if classroom is None:
            return None, "Simulation module scope requires a class."
    return {
        "target_user": target_user,
        "capability": capability,
        "classroom": classroom,
        "module_id": module_id,
    }, ""


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


__all__ = [
    "build_rbac_tools_context",
    "rbac_tools_enabled_for_user",
    "rbac_tools_requested",
    "teach_set_module_scope_grant_active",
    "teach_simulate_rbac_access",
    "teach_upsert_module_scope_grant",
]
