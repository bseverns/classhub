"""Bulk RBAC simulation helpers for teacher tools."""

from ...services.org_access import evaluate_staff_capability
from .shared import _parse_positive_int, staff_classroom_or_none


def build_bulk_simulation_result(*, request, state: dict, staff_users, capability_values: set[str], max_rows: int = 250):
    class_id_raw = str(state.get("rbac_bulk_class_id") or "").strip()
    capability = str(state.get("rbac_bulk_capability") or "").strip().lower()
    if not class_id_raw or capability not in capability_values:
        return None
    classroom = staff_classroom_or_none(request.user, class_id_raw)
    if classroom is None:
        return None

    module_id = None
    module_id_raw = str(state.get("rbac_bulk_module_id") or "").strip()
    if module_id_raw:
        module_id = _parse_positive_int(module_id_raw, min_value=1, max_value=2_147_483_647)
        if module_id is None:
            return None

    rows = []
    allowed_count = 0
    denied_count = 0
    for account in list(staff_users)[:max_rows]:
        decision = evaluate_staff_capability(
            account,
            capability,
            classroom=classroom,
            module_id=module_id,
        )
        if decision.allowed:
            allowed_count += 1
        else:
            denied_count += 1
        rows.append(
            {
                "user_id": int(account.id),
                "username": str(account.username),
                "is_superuser": bool(account.is_superuser),
                "allowed": bool(decision.allowed),
                "reason": decision.reason,
                "role": decision.role,
                "organization_id": decision.organization_id,
                "classroom_id": decision.classroom_id,
                "module_id": decision.module_id,
            }
        )
    return {
        "classroom_id": int(classroom.id),
        "classroom_name": str(classroom.name),
        "capability": capability,
        "module_id": module_id,
        "rows": rows,
        "allowed_count": allowed_count,
        "denied_count": denied_count,
        "is_truncated": len(staff_users) > max_rows,
    }
