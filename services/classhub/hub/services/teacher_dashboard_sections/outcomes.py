"""Outcome/certificate section context builders for /teach/class."""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from ...models import StudentIdentity, StudentOutcomeEvent
from ..telemetry_reads import student_outcome_events_queryset
from .shared import int_setting


def build_outcome_rollup(
    *,
    classroom,
    students: list[StudentIdentity],
    active_window_days: int = 30,
    include_class_metrics: bool = False,
    include_outcome_windows: bool = False,
) -> dict:
    student_ids = [int(student.id) for student in students]
    events_qs = student_outcome_events_queryset().filter(classroom_id=int(classroom.id))
    sessions_by_student: dict[int, int] = {}
    artifacts_by_student: dict[int, int] = {}
    milestones_by_student: dict[int, int] = {}
    if student_ids:
        for row in (
            events_qs.filter(student_id__in=student_ids)
            .values("student_id", "event_type")
            .annotate(total=models.Count("id"))
        ):
            student_id = int(row["student_id"])
            total = int(row["total"] or 0)
            event_type = str(row["event_type"] or "")
            if event_type == StudentOutcomeEvent.EVENT_SESSION_COMPLETED:
                sessions_by_student[student_id] = total
            elif event_type == StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED:
                artifacts_by_student[student_id] = total
            elif event_type == StudentOutcomeEvent.EVENT_MILESTONE_EARNED:
                milestones_by_student[student_id] = total

    outcome_windows: dict[int, tuple[str, str]] = {}
    if include_outcome_windows and student_ids:
        for row in (
            events_qs.filter(student_id__in=student_ids)
            .values("student_id")
            .annotate(first=models.Min("created_at"), last=models.Max("created_at"))
        ):
            student_id = int(row["student_id"])
            first = row.get("first")
            last = row.get("last")
            outcome_windows[student_id] = (
                first.isoformat() if first else "",
                last.isoformat() if last else "",
            )

    total_sessions = 0
    total_artifacts = 0
    total_milestones = 0
    active_students = 0
    if include_class_metrics:
        active_since = timezone.now() - timedelta(days=max(int(active_window_days or 0), 1))
        total_sessions = events_qs.filter(
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
        ).count()
        total_artifacts = events_qs.filter(
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
        ).count()
        total_milestones = events_qs.filter(
            event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
        ).count()
        active_students = (
            events_qs.filter(
                created_at__gte=active_since,
                student_id__isnull=False,
            )
            .values("student_id")
            .distinct()
            .count()
        )

    return {
        "sessions_by_student": sessions_by_student,
        "artifacts_by_student": artifacts_by_student,
        "milestones_by_student": milestones_by_student,
        "outcome_windows": outcome_windows,
        "total_sessions": int(total_sessions),
        "total_artifacts": int(total_artifacts),
        "total_milestones": int(total_milestones),
        "active_students": int(active_students),
    }


def build_certificate_eligibility_rows(
    *,
    classroom,
    students: list[StudentIdentity] | None = None,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> dict:
    certificate_min_sessions = (
        int_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8)
        if certificate_min_sessions is None
        else max(int(certificate_min_sessions), 1)
    )
    certificate_min_artifacts = (
        int_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6)
        if certificate_min_artifacts is None
        else max(int(certificate_min_artifacts), 1)
    )
    if students is None:
        students = list(
            StudentIdentity.objects.filter(classroom=classroom)
            .only("id", "display_name")
            .order_by("display_name", "id")
        )
    rollup = build_outcome_rollup(classroom=classroom, students=students)
    sessions_by_student: dict[int, int] = rollup["sessions_by_student"]
    artifacts_by_student: dict[int, int] = rollup["artifacts_by_student"]
    milestones_by_student: dict[int, int] = rollup["milestones_by_student"]

    eligible_students = 0
    rows: list[dict] = []
    for student in students:
        student_id = int(student.id)
        session_count = int(sessions_by_student.get(student_id, 0))
        artifact_count = int(artifacts_by_student.get(student_id, 0))
        milestone_count = int(milestones_by_student.get(student_id, 0))
        certificate_eligible = (
            session_count >= certificate_min_sessions and artifact_count >= certificate_min_artifacts
        )
        if certificate_eligible:
            eligible_students += 1
        rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "session_count": session_count,
                "artifact_count": artifact_count,
                "milestone_count": milestone_count,
                "certificate_eligible": certificate_eligible,
            }
        )
    return {
        "rows": rows,
        "eligible_students": int(eligible_students),
        "total_students": len(students),
        "certificate_min_sessions": int(certificate_min_sessions),
        "certificate_min_artifacts": int(certificate_min_artifacts),
    }


def build_outcome_snapshot(*, classroom, students: list[StudentIdentity]) -> dict:
    window_days = int_setting("CLASSHUB_OUTCOME_WINDOW_DAYS", 30)
    top_students_limit = int_setting("CLASSHUB_OUTCOME_TOP_STUDENTS", 5)
    certificate_min_sessions = int_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8)
    certificate_min_artifacts = int_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6)
    rollup = build_outcome_rollup(
        classroom=classroom,
        students=students,
        active_window_days=window_days,
        include_class_metrics=True,
    )
    sessions_by_student: dict[int, int] = rollup["sessions_by_student"]
    artifacts_by_student: dict[int, int] = rollup["artifacts_by_student"]
    milestones_by_student: dict[int, int] = rollup["milestones_by_student"]

    eligible_students = 0
    rows: list[dict] = []
    for student in students:
        sid = int(student.id)
        sessions = sessions_by_student.get(sid, 0)
        artifacts = artifacts_by_student.get(sid, 0)
        milestones = milestones_by_student.get(sid, 0)
        eligible = sessions >= certificate_min_sessions and artifacts >= certificate_min_artifacts
        if eligible:
            eligible_students += 1
        if sessions or artifacts or milestones:
            rows.append(
                {
                    "display_name": student.display_name,
                    "session_count": sessions,
                    "artifact_count": artifacts,
                    "milestone_count": milestones,
                    "certificate_eligible": eligible,
                }
            )
    rows.sort(
        key=lambda row: (
            -int(row["session_count"]),
            -int(row["artifact_count"]),
            -int(row["milestone_count"]),
            str(row["display_name"]).lower(),
        )
    )

    return {
        "window_days": window_days,
        "total_sessions": int(rollup["total_sessions"]),
        "total_artifacts": int(rollup["total_artifacts"]),
        "total_milestones": int(rollup["total_milestones"]),
        "active_students": int(rollup["active_students"]),
        "eligible_students": int(eligible_students),
        "total_students": len(students),
        "certificate_min_sessions": certificate_min_sessions,
        "certificate_min_artifacts": certificate_min_artifacts,
        "top_students": rows[:top_students_limit],
    }


__all__ = [
    "build_certificate_eligibility_rows",
    "build_outcome_rollup",
    "build_outcome_snapshot",
]
