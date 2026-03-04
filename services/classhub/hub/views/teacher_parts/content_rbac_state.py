"""RBAC tools state/context helpers for teacher home."""

from ...models import ClassStaffModuleScopeGrant
from .shared import get_user_model, models


def rbac_staff_users(classes):
    class_org_ids = {int(c.organization_id) for c in classes if c.organization_id}
    User = get_user_model()
    staff_users_qs = User.objects.filter(is_staff=True, is_active=True)
    if class_org_ids:
        staff_users_qs = staff_users_qs.filter(
            models.Q(is_superuser=True)
            | models.Q(
                classhub_organization_memberships__organization_id__in=class_org_ids,
                classhub_organization_memberships__is_active=True,
                classhub_organization_memberships__organization__is_active=True,
            )
        ).distinct()
    else:
        staff_users_qs = staff_users_qs.filter(is_superuser=True)
    return list(staff_users_qs.order_by("username", "id").only("id", "username", "is_superuser"))


def rbac_scope_grants(classes):
    class_ids = [int(c.id) for c in classes]
    if not class_ids:
        return []
    return list(
        ClassStaffModuleScopeGrant.objects.select_related("classroom", "user")
        .filter(classroom_id__in=class_ids)
        .order_by("classroom__name", "user__username", "capability", "effect", "module_order_start", "id")
    )


def rbac_simulation_result(request):
    if (request.GET.get("rbac_sim_result") or "").strip() != "1":
        return None
    return {
        "allowed": (request.GET.get("rbac_sim_allowed") or "").strip() == "1",
        "reason": (request.GET.get("rbac_sim_reason") or "").strip(),
        "role": (request.GET.get("rbac_sim_role") or "").strip(),
        "capability": (request.GET.get("rbac_sim_capability") or "").strip(),
        "classroom_id": (request.GET.get("rbac_sim_classroom_id") or "").strip(),
        "module_id": (request.GET.get("rbac_sim_module_resolved") or "").strip(),
        "organization_id": (request.GET.get("rbac_sim_org_id") or "").strip(),
    }


def rbac_form_state(request):
    return {
        "rbac_class_id": (request.GET.get("rbac_class_id") or "").strip(),
        "rbac_user_id": (request.GET.get("rbac_user_id") or "").strip(),
        "rbac_capability": (request.GET.get("rbac_capability") or ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW).strip(),
        "rbac_effect": (request.GET.get("rbac_effect") or ClassStaffModuleScopeGrant.EFFECT_ALLOW).strip(),
        "rbac_module_start": (request.GET.get("rbac_module_start") or "0").strip(),
        "rbac_module_end": (request.GET.get("rbac_module_end") or "0").strip(),
        "rbac_grant_active": (request.GET.get("rbac_grant_active") or "1").strip(),
        "rbac_sim_user_id": (request.GET.get("rbac_sim_user_id") or "").strip(),
        "rbac_sim_class_id": (request.GET.get("rbac_sim_class_id") or "").strip(),
        "rbac_sim_capability": (
            request.GET.get("rbac_sim_capability") or ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW
        ).strip(),
        "rbac_sim_module_id": (request.GET.get("rbac_sim_module_id") or "").strip(),
        "rbac_bulk_class_id": (request.GET.get("rbac_bulk_class_id") or "").strip(),
        "rbac_bulk_capability": (
            request.GET.get("rbac_bulk_capability") or ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW
        ).strip(),
        "rbac_bulk_module_id": (request.GET.get("rbac_bulk_module_id") or "").strip(),
        "rbac_audit_action": (request.GET.get("rbac_audit_action") or "all").strip(),
        "rbac_audit_class_id": (request.GET.get("rbac_audit_class_id") or "").strip(),
        "rbac_audit_limit": (request.GET.get("rbac_audit_limit") or "50").strip(),
    }
