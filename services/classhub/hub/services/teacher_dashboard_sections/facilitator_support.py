"""Facilitator support board section builder for /teach/class."""

from __future__ import annotations

from django.utils import timezone

from ...models import Material, Module, StudentEvent, StudentIdentity
from ..telemetry_reads import student_events_queryset
from .shared import detail_int, int_setting


def build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:
    now = timezone.now()
    module_titles = {int(module.id): str(module.title) for module in modules}
    material_rows = Material.objects.filter(module__classroom=classroom).values("id", "title", "module_id")
    material_lookup: dict[int, dict] = {}
    for row in material_rows:
        material_lookup[int(row["id"])] = {
            "title": str(row["title"] or ""),
            "module_title": module_titles.get(int(row["module_id"] or 0), ""),
        }
    student_by_id = {int(student.id): student for student in students}

    micro_event_types = {
        StudentEvent.EVENT_MICRO_CHECK_CAN_DO_THIS,
        StudentEvent.EVENT_MICRO_CHECK_STUCK,
        StudentEvent.EVENT_MICRO_CHECK_TAUGHT_SOMEONE,
    }
    activity_events = student_events_queryset().filter(
        classroom_id=int(classroom.id),
        student_id__isnull=False,
        event_type__in=list(micro_event_types | {StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED}),
    ).only("student_id", "event_type", "details", "created_at").order_by("-created_at", "-id")

    latest_signal_by_student: dict[int, StudentEvent] = {}
    latest_stuck_by_student: dict[int, StudentEvent] = {}
    latest_resolved_by_student: dict[int, StudentEvent] = {}
    for event in activity_events:
        student_id = int(event.student_id or 0)
        if student_id <= 0:
            continue
        if event.event_type in micro_event_types and student_id not in latest_signal_by_student:
            latest_signal_by_student[student_id] = event
        if event.event_type == StudentEvent.EVENT_MICRO_CHECK_STUCK and student_id not in latest_stuck_by_student:
            latest_stuck_by_student[student_id] = event
        if event.event_type == StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED and student_id not in latest_resolved_by_student:
            latest_resolved_by_student[student_id] = event

    stuck_rows: list[dict] = []
    for student_id, stuck_event in latest_stuck_by_student.items():
        student = student_by_id.get(student_id)
        if student is None:
            continue
        resolved_event = latest_resolved_by_student.get(student_id)
        if resolved_event and resolved_event.created_at >= stuck_event.created_at:
            continue
        latest_signal = latest_signal_by_student.get(student_id)
        if latest_signal and latest_signal.created_at > stuck_event.created_at and latest_signal.event_type != StudentEvent.EVENT_MICRO_CHECK_STUCK:
            continue
        module_id = detail_int(stuck_event.details, "module_id")
        waiting_minutes = max(int((now - stuck_event.created_at).total_seconds() // 60), 0)
        stuck_rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "module_id": module_id,
                "module_title": module_titles.get(module_id, ""),
                "requested_at": stuck_event.created_at,
                "waiting_minutes": waiting_minutes,
            }
        )
    stuck_rows.sort(
        key=lambda row: (
            -int(row["waiting_minutes"]),
            str(row["display_name"]).lower(),
        )
    )

    delete_request_events = (
        student_events_queryset().filter(
            classroom_id=int(classroom.id),
            student_id__isnull=False,
            event_type__in=[
                StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
                StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
            ],
        )
        .only("student_id", "event_type", "created_at")
        .order_by("-created_at", "-id")
    )
    latest_delete_request_by_student: dict[int, StudentEvent] = {}
    latest_delete_resolved_by_student: dict[int, StudentEvent] = {}
    for event in delete_request_events:
        student_id = int(event.student_id or 0)
        if student_id <= 0:
            continue
        if (
            event.event_type == StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST
            and student_id not in latest_delete_request_by_student
        ):
            latest_delete_request_by_student[student_id] = event
        if (
            event.event_type == StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED
            and student_id not in latest_delete_resolved_by_student
        ):
            latest_delete_resolved_by_student[student_id] = event

    delete_request_rows: list[dict] = []
    for student_id, request_event in latest_delete_request_by_student.items():
        student = student_by_id.get(student_id)
        if student is None:
            continue
        resolved_event = latest_delete_resolved_by_student.get(student_id)
        if resolved_event and resolved_event.created_at >= request_event.created_at:
            continue
        waiting_minutes = max(int((now - request_event.created_at).total_seconds() // 60), 0)
        delete_request_rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "requested_at": request_event.created_at,
                "waiting_minutes": waiting_minutes,
            }
        )
    delete_request_rows.sort(
        key=lambda row: (
            -int(row["waiting_minutes"]),
            str(row["display_name"]).lower(),
        )
    )

    upload_error_limit = int_setting("CLASSHUB_UPLOAD_ERROR_FEED_LIMIT", 10)
    upload_error_rows: list[dict] = []
    recent_upload_errors = (
        student_events_queryset().filter(
            classroom_id=int(classroom.id),
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD_ERROR,
            student_id__isnull=False,
        )
        .only("student_id", "details", "created_at")
        .order_by("-created_at", "-id")[:upload_error_limit]
    )
    for event in recent_upload_errors:
        student_id = int(event.student_id or 0)
        student = student_by_id.get(student_id)
        if student is None:
            continue
        details = event.details if isinstance(event.details, dict) else {}
        material_id = detail_int(details, "material_id")
        material_meta = material_lookup.get(material_id, {})
        reason_code = str(details.get("reason_code") or "").strip() or "upload_error"
        upload_error_rows.append(
            {
                "display_name": student.display_name,
                "material_title": str(material_meta.get("title") or ""),
                "module_title": str(material_meta.get("module_title") or ""),
                "reason_code": reason_code.replace("_", " "),
                "created_at": event.created_at,
            }
        )

    idle_minutes_threshold = int_setting("CLASSHUB_FACILITATOR_IDLE_MINUTES", 20)
    idle_rows: list[dict] = []
    for student in students:
        if student.last_seen_at is None:
            continue
        idle_minutes = int((now - student.last_seen_at).total_seconds() // 60)
        if idle_minutes < idle_minutes_threshold:
            continue
        idle_rows.append(
            {
                "student_id": int(student.id),
                "display_name": student.display_name,
                "idle_minutes": max(idle_minutes, 0),
                "last_seen_at": student.last_seen_at,
            }
        )
    idle_rows.sort(key=lambda row: (-int(row["idle_minutes"]), str(row["display_name"]).lower()))
    idle_rows = idle_rows[: int_setting("CLASSHUB_FACILITATOR_IDLE_LIST_LIMIT", 12)]

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
