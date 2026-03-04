"""RBAC audit operations helpers for teacher tools."""

from django.db.models import Q

from ...models import AuditEvent
from .shared import _parse_positive_int

_AUDIT_ACTION_CHOICES = (
    ("all", "All RBAC + org policy actions"),
    ("rbac.scope_grant.", "Scoped grants"),
    ("rbac.simulate", "RBAC simulations"),
    ("organization.role_capability.", "Org role capability templates"),
    ("organization.membership.", "Organization memberships"),
)
_AUDIT_ACTION_PREFIXES = tuple(prefix for prefix, _label in _AUDIT_ACTION_CHOICES if prefix != "all")


def _parse_limit(raw_value: str) -> int:
    parsed = _parse_positive_int(raw_value, min_value=1, max_value=250)
    if parsed is None:
        return 50
    return parsed


def _scoped_audit_queryset(*, class_ids: list[int], org_ids: list[int]):
    queryset = AuditEvent.objects.select_related("actor_user", "classroom")
    if not class_ids and not org_ids:
        return queryset.none()
    if class_ids and org_ids:
        return queryset.filter(
            Q(classroom_id__in=class_ids)
            | Q(classroom__isnull=True, metadata__organization_id__in=org_ids)
        )
    if class_ids:
        return queryset.filter(classroom_id__in=class_ids)
    return queryset.filter(classroom__isnull=True, metadata__organization_id__in=org_ids)


def build_rbac_audit_context(*, classes, state: dict) -> dict:
    class_ids = [int(c.id) for c in classes]
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    selected_action = str(state.get("rbac_audit_action") or "all").strip() or "all"
    selected_class_id_raw = str(state.get("rbac_audit_class_id") or "").strip()
    selected_limit = _parse_limit(str(state.get("rbac_audit_limit") or "50").strip())

    queryset = _scoped_audit_queryset(class_ids=class_ids, org_ids=org_ids)
    if selected_class_id_raw:
        class_id = _parse_positive_int(selected_class_id_raw, min_value=1, max_value=2_147_483_647)
        if class_id is not None:
            queryset = queryset.filter(classroom_id=class_id)
    if selected_action == "all":
        action_filter = Q()
        for prefix in _AUDIT_ACTION_PREFIXES:
            action_filter |= Q(action__startswith=prefix)
        queryset = queryset.filter(action_filter)
    elif selected_action in _AUDIT_ACTION_PREFIXES:
        queryset = queryset.filter(action__startswith=selected_action)
    else:
        selected_action = "all"
        action_filter = Q()
        for prefix in _AUDIT_ACTION_PREFIXES:
            action_filter |= Q(action__startswith=prefix)
        queryset = queryset.filter(action_filter)

    events = list(queryset.order_by("-created_at", "-id")[:selected_limit])
    return {
        "rbac_audit_events": events,
        "rbac_audit_action_choices": _AUDIT_ACTION_CHOICES,
        "rbac_audit_action": selected_action,
        "rbac_audit_class_id": selected_class_id_raw,
        "rbac_audit_limit": str(selected_limit),
    }
