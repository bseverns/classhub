"""Helper signal snapshot builders for teacher dashboard tracker panels."""

from __future__ import annotations

from datetime import timedelta
import re

from django.utils import timezone

from ..models import Class, StudentEvent, StudentIdentity
from .teacher_tracker_cache import _cache_get_or_build
from .teacher_tracker_types import HelperSignalIntentRow, HelperSignalSnapshot, HelperSignalStudentRow
from .telemetry_reads import student_events_queryset


_SAFE_INTENT_RE = re.compile(r"^[a-z0-9_-]{1,32}$")


def _compute_helper_signal_snapshot(
    *,
    classroom: Class,
    students: list[StudentIdentity],
    window_hours: int = 24,
    top_students: int = 5,
) -> HelperSignalSnapshot:
    window_hours = max(int(window_hours), 1)
    top_students = max(int(top_students), 1)
    since = timezone.now() - timedelta(hours=window_hours)

    rows = list(
        student_events_queryset().filter(
            classroom_id=int(classroom.id),
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            created_at__gte=since,
        ).values("student_id", "details")
    )

    total_events = len(rows)
    intent_counts: dict[str, int] = {}
    compacted_events = 0
    follow_up_total = 0
    student_counts: dict[int, dict] = {}

    for row in rows:
        details = row.get("details")
        if not isinstance(details, dict):
            details = {}

        intent = str(details.get("intent") or "").strip().lower()
        if intent and _SAFE_INTENT_RE.fullmatch(intent):
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        if bool(details.get("conversation_compacted")):
            compacted_events += 1

        try:
            follow_count = int(details.get("follow_up_suggestions_count") or 0)
        except Exception:
            follow_count = 0
        if follow_count > 0:
            follow_up_total += follow_count

        try:
            student_id = int(row.get("student_id") or 0)
        except Exception:
            student_id = 0
        if student_id <= 0:
            continue
        bucket = student_counts.setdefault(student_id, {"chat_count": 0, "intent_counts": {}})
        bucket["chat_count"] += 1
        if intent and _SAFE_INTENT_RE.fullmatch(intent):
            intent_bucket: dict[str, int] = bucket["intent_counts"]
            intent_bucket[intent] = intent_bucket.get(intent, 0) + 1

    intent_rows: list[HelperSignalIntentRow] = [
        {"intent": intent, "count": count}
        for intent, count in sorted(intent_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    names_by_student_id = {int(st.id): st.display_name for st in students if getattr(st, "id", None)}
    busiest_students: list[HelperSignalStudentRow] = []
    for student_id, bucket in student_counts.items():
        intent_bucket: dict[str, int] = bucket.get("intent_counts") or {}
        if intent_bucket:
            primary_intent = sorted(intent_bucket.items(), key=lambda item: (-item[1], item[0]))[0][0]
        else:
            primary_intent = ""
        busiest_students.append(
            {
                "student_id": student_id,
                "display_name": names_by_student_id.get(student_id, f"Student #{student_id}"),
                "chat_count": int(bucket.get("chat_count") or 0),
                "primary_intent": primary_intent,
            }
        )
    busiest_students.sort(key=lambda row: (-row["chat_count"], row["display_name"].lower()))

    if total_events > 0:
        avg_follow = round(float(follow_up_total) / float(total_events), 1)
    else:
        avg_follow = 0.0

    return {
        "since": since,
        "window_hours": window_hours,
        "total_events": total_events,
        "intent_rows": intent_rows,
        "compacted_events": compacted_events,
        "avg_follow_up_suggestions": avg_follow,
        "busiest_students": busiest_students[:top_students],
    }


def _build_helper_signal_snapshot(
    *,
    classroom: Class,
    students: list[StudentIdentity],
    window_hours: int = 24,
    top_students: int = 5,
) -> HelperSignalSnapshot:
    student_signature = ",".join(
        f"{int(student.id)}:{student.display_name}"
        for student in students
        if getattr(student, "id", None)
    )
    return _cache_get_or_build(
        "helper-signals",
        key_parts=[
            str(int(getattr(classroom, "id", 0) or 0)),
            str(int(getattr(classroom, "session_epoch", 0) or 0)),
            str(max(int(window_hours), 1)),
            str(max(int(top_students), 1)),
            student_signature,
        ],
        builder=lambda: _compute_helper_signal_snapshot(
            classroom=classroom,
            students=students,
            window_hours=window_hours,
            top_students=top_students,
        ),
    )


__all__ = ["_build_helper_signal_snapshot"]
