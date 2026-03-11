"""Outcome snapshot and certificate eligibility helpers for /teach/class."""

from __future__ import annotations

from ...models import StudentIdentity
from .outcomes_rollup import build_outcome_rollup
from .shared import int_setting


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
    "build_outcome_snapshot",
]
