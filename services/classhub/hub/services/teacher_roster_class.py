"""Service helpers for teacher class dashboard/export view logic."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from ..models import Material, Submission
from .filenames import safe_filename
from .teacher_tracker import _build_helper_signal_snapshot, _build_lesson_tracker_rows
from .zip_exports import (
    reserve_archive_path,
    temporary_zip_archive,
    write_submission_file_to_archive,
)


def _material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:
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


def _submission_counts_by_student(*, classroom, students: list) -> dict[int, int]:
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


def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))
    normalize_order_fn(modules)
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))

    upload_material_ids: list[int] = []
    for module in modules:
        for material in module.materials.all():
            if material.type == Material.TYPE_UPLOAD:
                upload_material_ids.append(material.id)

    student_count = classroom.students.count()
    students = list(classroom.students.all().order_by("created_at", "id"))
    lesson_rows = _build_lesson_tracker_rows(
        request,
        classroom.id,
        modules,
        student_count,
        class_session_epoch=classroom.session_epoch,
    )
    helper_signals = _build_helper_signal_snapshot(
        classroom=classroom,
        students=students,
        window_hours=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_WINDOW_HOURS", 24) or 24), 1),
        top_students=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_TOP_STUDENTS", 5) or 5), 1),
    )
    return {
        "modules": modules,
        "student_count": student_count,
        "students": students,
        "submission_counts": _material_submission_counts(upload_material_ids),
        "submission_counts_by_student": _submission_counts_by_student(
            classroom=classroom,
            students=students,
        ),
        "lesson_rows": lesson_rows,
        "helper_signals": helper_signals,
    }


def export_submissions_today_archive(*, classroom, day_start, day_end):
    rows = list(
        Submission.objects.filter(
            student__classroom=classroom,
            uploaded_at__gte=day_start,
            uploaded_at__lt=day_end,
        )
        .select_related("student", "material")
        .order_by("student__display_name", "material__title", "uploaded_at", "id")
    )

    file_count = 0
    used_paths: set[str] = set()
    with temporary_zip_archive() as (tmp, archive):
        for submission in rows:
            student_name = safe_filename(submission.student.display_name)
            material_name = safe_filename(submission.material.title)
            original = safe_filename(submission.original_filename or submission.file.name.rsplit("/", 1)[-1])
            stamp = timezone.localtime(submission.uploaded_at).strftime("%H%M%S")
            candidate = reserve_archive_path(
                f"{student_name}/{material_name}/{stamp}_{original}",
                used_paths,
                fallback=f"{student_name}/{material_name}/{stamp}_{submission.id}_{original}",
            )
            if not write_submission_file_to_archive(
                archive,
                submission=submission,
                arcname=candidate,
                allow_file_fallback=False,
            ):
                continue
            file_count += 1
        if file_count == 0:
            archive.writestr(
                "README.txt",
                (
                    "No submission files were available for this class today.\n"
                    "This can happen when there were no uploads or file sources were unavailable.\n"
                ),
            )
    return tmp, file_count


__all__ = ["build_dashboard_context", "export_submissions_today_archive"]
