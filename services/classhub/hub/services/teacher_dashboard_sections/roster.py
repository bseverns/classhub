"""Roster/card section context builders for /teach/class."""

from __future__ import annotations

from django.db import models

from ...models import StudentIdentity, StudentSupportTag, Submission


def material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:
    submission_counts: dict[int, int] = {}
    if not upload_material_ids:
        return submission_counts
    rows = (
        Submission.objects.filter(material_id__in=upload_material_ids)
        .values("material_id")
        .annotate(total=models.Count("student_id", distinct=True))
    )
    for row in rows:
        material_id = int(row["material_id"])
        submission_counts[material_id] = int(row["total"])
    return submission_counts


def submission_counts_by_student(*, classroom, students: list) -> dict[int, int]:
    submission_counts: dict[int, int] = {}
    if not students:
        return submission_counts
    rows = (
        Submission.objects.filter(student__classroom=classroom)
        .values("student_id")
        .annotate(total=models.Count("id"))
    )
    for row in rows:
        submission_counts[int(row["student_id"])] = int(row["total"])
    return submission_counts


def support_tag_choices() -> list[dict[str, str]]:
    return [{"value": str(value), "label": str(label)} for value, label in StudentSupportTag.TAG_CHOICES]


def support_tags_by_student(*, classroom, students: list[StudentIdentity]) -> dict[int, list[dict[str, str]]]:
    by_student: dict[int, list[dict[str, str]]] = {}
    student_ids = [int(student.id) for student in students if getattr(student, "id", None) is not None]
    if not student_ids:
        return by_student
    rows = (
        StudentSupportTag.objects.filter(classroom=classroom, student_id__in=student_ids)
        .values("student_id", "tag")
        .order_by("student_id", "tag", "-id")
    )
    for row in rows:
        student_id = int(row["student_id"])
        tag = str(row["tag"] or "")
        if not tag:
            continue
        bucket = by_student.setdefault(student_id, [])
        bucket.append({"value": tag, "label": StudentSupportTag.label_for(tag)})
    return by_student


__all__ = [
    "material_submission_counts",
    "submission_counts_by_student",
    "support_tag_choices",
    "support_tags_by_student",
]
