"""Module/class scope helpers for capability grants."""

from __future__ import annotations

from ..models import Class, Module
from .org_access_capabilities_shared import (
    CAP_POLICY_MANAGE,
    CAP_ROSTER_MANAGE,
    CAP_SUBMISSION_DELETE,
    CAP_SUBMISSION_VIEW,
)

MODULE_RANGE_GRANT_CAPABILITIES = frozenset(
    {
        CAP_SUBMISSION_VIEW,
        CAP_SUBMISSION_DELETE,
    }
)
CLASS_SCOPE_GRANT_CAPABILITIES = frozenset(
    {
        CAP_ROSTER_MANAGE,
        CAP_POLICY_MANAGE,
    }
)
SCOPED_GRANT_CAPABILITIES = MODULE_RANGE_GRANT_CAPABILITIES | CLASS_SCOPE_GRANT_CAPABILITIES


def module_scope_is_valid(*, classroom: Class | None, module_id: int | None) -> bool:
    if module_id is None:
        return True
    try:
        parsed_module_id = int(module_id)
    except Exception:
        return False
    if parsed_module_id <= 0:
        return False
    if classroom is None:
        return False
    return Module.objects.filter(id=parsed_module_id, classroom_id=classroom.id).exists()


def module_scope_order(*, classroom: Class, module_id: int) -> int | None:
    try:
        parsed_module_id = int(module_id)
    except Exception:
        return None
    if parsed_module_id <= 0:
        return None
    row = (
        Module.objects.filter(
            id=parsed_module_id,
            classroom_id=classroom.id,
        )
        .only("order_index")
        .first()
    )
    if row is None:
        return None
    return int(row.order_index)


__all__ = [
    "CLASS_SCOPE_GRANT_CAPABILITIES",
    "MODULE_RANGE_GRANT_CAPABILITIES",
    "SCOPED_GRANT_CAPABILITIES",
    "module_scope_is_valid",
    "module_scope_order",
]
