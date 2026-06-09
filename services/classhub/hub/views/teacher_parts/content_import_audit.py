"""Content/import audit helpers for teacher tools."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from django.db.models import Q

from ...models import AuditEvent
from .shared import _parse_positive_int

_AUDIT_ACTION_CHOICES = (
    ("all", "All content + import actions"),
    ("coursepack.registry.import", "Registry imports"),
    ("admin.coursepack_", "Admin import flows"),
    ("class.content_import", "Class content imports"),
    ("teacher_syllabus_import.", "Syllabus compile"),
    ("teacher_templates.", "Authoring templates"),
    ("syllabus_export.", "Syllabus exports"),
)
_AUDIT_ACTION_PREFIXES = tuple(prefix for prefix, _label in _AUDIT_ACTION_CHOICES if prefix != "all")
_DEFAULT_ACTION = "all"
_DEFAULT_LIMIT = "50"


def _parse_limit(raw_value: str) -> int:
    parsed = _parse_positive_int(raw_value, min_value=1, max_value=250)
    if parsed is None:
        return 50
    return parsed


def _scoped_audit_queryset(*, class_ids: list[int], user_id: int):
    queryset = AuditEvent.objects.select_related("actor_user", "classroom")
    if not class_ids and not user_id:
        return queryset.none()
    filters = Q()
    if class_ids:
        filters |= Q(classroom_id__in=class_ids)
    if user_id:
        filters |= Q(classroom__isnull=True, actor_user_id=user_id)
    return queryset.filter(filters)


def _content_audit_default_context() -> dict:
    return {
        "content_audit_events": [],
        "content_audit_rows": [],
        "content_audit_action_choices": _AUDIT_ACTION_CHOICES,
        "content_audit_action": _DEFAULT_ACTION,
        "content_audit_class_id": "",
        "content_audit_limit": _DEFAULT_LIMIT,
        "content_audit_event_id": "",
        "content_audit_open": False,
        "content_audit_selected_event": None,
        "content_audit_selected_metadata_json": "",
    }


def _content_audit_open(*, action: str, class_id: str, limit: str, event_id: str) -> bool:
    return bool(class_id or event_id or action != _DEFAULT_ACTION or limit != _DEFAULT_LIMIT)


def _content_audit_query_string(*, action: str, class_id: str, limit: str, event_id: int | None = None) -> str:
    params = {
        "portal_mode": "setup",
        "advanced": "1",
        "content_audit_action": action,
        "content_audit_class_id": class_id,
        "content_audit_limit": limit,
    }
    if event_id:
        params["content_audit_event_id"] = str(event_id)
    return urlencode(params)


def _content_audit_row(*, event, action: str, class_id: str, limit: str, selected_event_id: int | None) -> dict:
    return {
        "event": event,
        "inspect_url": f"/teach?{_content_audit_query_string(action=action, class_id=class_id, limit=limit, event_id=event.id)}#content-import-audit",
        "selected": bool(selected_event_id and event.id == selected_event_id),
    }


def _content_audit_action_queryset(queryset, selected_action: str):
    if selected_action == _DEFAULT_ACTION:
        action_filter = Q()
        for prefix in _AUDIT_ACTION_PREFIXES:
            action_filter |= Q(action__startswith=prefix)
        return queryset.filter(action_filter), selected_action
    if selected_action in _AUDIT_ACTION_PREFIXES:
        return queryset.filter(action__startswith=selected_action), selected_action
    action_filter = Q()
    for prefix in _AUDIT_ACTION_PREFIXES:
        action_filter |= Q(action__startswith=prefix)
    return queryset.filter(action_filter), _DEFAULT_ACTION


def _content_audit_selected_metadata_json(selected_event) -> str:
    if selected_event is None:
        return ""
    return json.dumps(selected_event.metadata or {}, indent=2, sort_keys=True, ensure_ascii=False)


def build_content_import_audit_context(*, classes, state: dict, user) -> dict:
    if not user.is_superuser:
        return _content_audit_default_context()

    class_ids = [int(c.id) for c in classes]
    selected_action = str(state.get("content_audit_action") or _DEFAULT_ACTION).strip() or _DEFAULT_ACTION
    selected_class_id_raw = str(state.get("content_audit_class_id") or "").strip()
    selected_limit = _parse_limit(str(state.get("content_audit_limit") or _DEFAULT_LIMIT).strip())
    selected_event_id_raw = str(state.get("content_audit_event_id") or "").strip()
    selected_event_id = _parse_positive_int(selected_event_id_raw, min_value=1, max_value=2_147_483_647)

    queryset = _scoped_audit_queryset(class_ids=class_ids, user_id=int(user.id))
    if selected_class_id_raw:
        class_id = _parse_positive_int(selected_class_id_raw, min_value=1, max_value=2_147_483_647)
        if class_id is not None:
            queryset = queryset.filter(classroom_id=class_id)
    queryset, selected_action = _content_audit_action_queryset(queryset, selected_action)

    selected_event = None
    if selected_event_id is not None:
        selected_event = queryset.filter(id=selected_event_id).first()
    events = list(queryset.order_by("-created_at", "-id")[:selected_limit])
    selected_limit_raw = str(selected_limit)
    return {
        "content_audit_events": events,
        "content_audit_rows": [
            _content_audit_row(
                event=event,
                action=selected_action,
                class_id=selected_class_id_raw,
                limit=selected_limit_raw,
                selected_event_id=selected_event_id,
            )
            for event in events
        ],
        "content_audit_action_choices": _AUDIT_ACTION_CHOICES,
        "content_audit_action": selected_action,
        "content_audit_class_id": selected_class_id_raw,
        "content_audit_limit": selected_limit_raw,
        "content_audit_event_id": selected_event_id_raw,
        "content_audit_open": _content_audit_open(
            action=selected_action,
            class_id=selected_class_id_raw,
            limit=selected_limit_raw,
            event_id=selected_event_id_raw,
        ),
        "content_audit_selected_event": selected_event,
        "content_audit_selected_metadata_json": _content_audit_selected_metadata_json(selected_event),
    }


__all__ = ["build_content_import_audit_context"]
