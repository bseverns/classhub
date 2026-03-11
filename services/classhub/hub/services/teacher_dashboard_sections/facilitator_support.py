"""Facilitator support board section builder for /teach/class."""

from __future__ import annotations

from django.utils import timezone

from ...models import Module, StudentIdentity
from .facilitator_support_builders import (
    build_delete_request_rows,
    build_idle_rows,
    build_module_material_lookups,
    build_stuck_rows,
    build_upload_error_rows,
)
from .shared import int_setting


def build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:
    now = timezone.now()
    classroom_id = int(classroom.id)
    module_titles, material_lookup = build_module_material_lookups(
        classroom=classroom,
        modules=modules,
    )

    stuck_rows = build_stuck_rows(
        classroom_id=classroom_id,
        now=now,
        students=students,
        module_titles=module_titles,
    )
    delete_request_rows = build_delete_request_rows(
        classroom_id=classroom_id,
        now=now,
        students=students,
    )

    upload_error_limit = int_setting("CLASSHUB_UPLOAD_ERROR_FEED_LIMIT", 10)
    upload_error_rows = build_upload_error_rows(
        classroom_id=classroom_id,
        students=students,
        material_lookup=material_lookup,
        upload_error_limit=upload_error_limit,
    )

    idle_minutes_threshold = int_setting("CLASSHUB_FACILITATOR_IDLE_MINUTES", 20)
    idle_rows = build_idle_rows(
        now=now,
        students=students,
        idle_minutes_threshold=idle_minutes_threshold,
        idle_list_limit=int_setting("CLASSHUB_FACILITATOR_IDLE_LIST_LIMIT", 12),
    )

    return {
        "generated_at": now,
        "stuck_rows": stuck_rows,
        "stuck_count": len(stuck_rows),
        "delete_request_rows": delete_request_rows,
        "delete_request_count": len(delete_request_rows),
        "upload_error_rows": upload_error_rows,
        "upload_error_count": len(upload_error_rows),
        "idle_rows": idle_rows,
        "idle_minutes_threshold": idle_minutes_threshold,
    }


__all__ = ["build_facilitator_support_snapshot"]
