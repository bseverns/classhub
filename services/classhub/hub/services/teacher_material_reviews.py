"""Teacher-facing material review row builders."""

from __future__ import annotations

from ..models import StudentMaterialResponse


def build_rubric_material_rows(*, material, students: list, show: str) -> tuple[list[dict], int]:
    response_rows = list(
        StudentMaterialResponse.objects.filter(material=material)
        .select_related("student")
        .order_by("-updated_at", "-id")
    )
    by_student = {row.student_id: row for row in response_rows}
    rows: list[dict] = []
    missing = 0
    for student in students:
        latest = by_student.get(student.id)
        if not latest:
            missing += 1
        rated_count = 0
        if latest and isinstance(latest.rubric_scores, list):
            rated_count = sum(1 for value in latest.rubric_scores if int(value or 0) > 0)
        rows.append(
            {
                "student": student,
                "latest": latest,
                "count": rated_count if latest else 0,
            }
        )
    if show == "submitted":
        rows = [row for row in rows if row["latest"]]
    elif show == "missing":
        rows = [row for row in rows if not row["latest"]]
    return rows, missing


__all__ = [
    "build_rubric_material_rows",
]
