"""Class outcomes CSV helpers for teacher roster surfaces."""

from __future__ import annotations

import csv
from io import StringIO

from ..models import CertificateIssuance, StudentIdentity
from .teacher_dashboard_sections.outcomes import build_outcome_rollup as _outcome_rollup_impl
from .teacher_dashboard_sections.shared import int_setting as _int_setting_impl


def _int_setting(setting_name: str, default: int, *, minimum: int = 1) -> int:
    return _int_setting_impl(setting_name, default, minimum=minimum)


def export_class_outcomes_csv(
    *,
    classroom,
    active_window_days: int = 30,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> str:
    active_window_days = max(int(active_window_days or 0), 1)
    certificate_min_sessions = (
        _int_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8)
        if certificate_min_sessions is None
        else max(int(certificate_min_sessions), 1)
    )
    certificate_min_artifacts = (
        _int_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6)
        if certificate_min_artifacts is None
        else max(int(certificate_min_artifacts), 1)
    )

    students = list(
        StudentIdentity.objects.filter(classroom=classroom)
        .only("id", "display_name")
        .order_by("display_name", "id")
    )
    student_ids = [int(student.id) for student in students]
    rollup = _outcome_rollup_impl(
        classroom=classroom,
        students=students,
        active_window_days=active_window_days,
        include_class_metrics=True,
        include_outcome_windows=True,
    )
    sessions_by_student: dict[int, int] = rollup["sessions_by_student"]
    artifacts_by_student: dict[int, int] = rollup["artifacts_by_student"]
    milestones_by_student: dict[int, int] = rollup["milestones_by_student"]
    outcome_windows: dict[int, tuple[str, str]] = rollup["outcome_windows"]

    eligible_students = 0
    issued_by_student: dict[int, str] = {}
    if student_ids:
        for row in CertificateIssuance.objects.filter(classroom=classroom, student_id__in=student_ids).values(
            "student_id",
            "issued_at",
        ):
            issued_by_student[int(row["student_id"])] = row["issued_at"].isoformat() if row.get("issued_at") else ""
    for student in students:
        sid = int(student.id)
        if (
            sessions_by_student.get(sid, 0) >= certificate_min_sessions
            and artifacts_by_student.get(sid, 0) >= certificate_min_artifacts
        ):
            eligible_students += 1

    fieldnames = [
        "row_type",
        "class_id",
        "class_name",
        "display_name",
        "session_completions",
        "artifact_submissions",
        "milestones",
        "certificate_eligible",
        "certificate_issued",
        "certificate_issued_at",
        "certificate_issued_students",
        "eligible_students",
        "total_students",
        "active_outcome_students",
        "first_outcome_at",
        "last_outcome_at",
        "certificate_min_sessions",
        "certificate_min_artifacts",
        "active_window_days",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()

    writer.writerow(
        {
            "row_type": "class_outcome_summary",
            "class_id": classroom.id,
            "class_name": classroom.name,
            "session_completions": rollup["total_sessions"],
            "artifact_submissions": rollup["total_artifacts"],
            "milestones": rollup["total_milestones"],
            "eligible_students": eligible_students,
            "certificate_issued_students": len(issued_by_student),
            "total_students": len(students),
            "active_outcome_students": rollup["active_students"],
            "certificate_min_sessions": certificate_min_sessions,
            "certificate_min_artifacts": certificate_min_artifacts,
            "active_window_days": active_window_days,
        }
    )

    for student in students:
        sid = int(student.id)
        sessions = sessions_by_student.get(sid, 0)
        artifacts = artifacts_by_student.get(sid, 0)
        eligible = sessions >= certificate_min_sessions and artifacts >= certificate_min_artifacts
        first_outcome, last_outcome = outcome_windows.get(sid, ("", ""))
        certificate_issued_at = issued_by_student.get(sid, "")
        writer.writerow(
            {
                "row_type": "student_outcome_summary",
                "class_id": classroom.id,
                "class_name": classroom.name,
                "display_name": student.display_name,
                "session_completions": sessions,
                "artifact_submissions": artifacts,
                "milestones": milestones_by_student.get(sid, 0),
                "certificate_eligible": "yes" if eligible else "no",
                "certificate_issued": "yes" if certificate_issued_at else "no",
                "certificate_issued_at": certificate_issued_at,
                "first_outcome_at": first_outcome,
                "last_outcome_at": last_outcome,
                "certificate_min_sessions": certificate_min_sessions,
                "certificate_min_artifacts": certificate_min_artifacts,
                "active_window_days": active_window_days,
            }
        )

    return out.getvalue()


__all__ = ["export_class_outcomes_csv"]
