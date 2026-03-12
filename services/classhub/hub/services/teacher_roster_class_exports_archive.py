"""Archive export helpers for teacher class roster surfaces."""

from __future__ import annotations

from django.utils import timezone

from ..models import Submission
from .filenames import safe_filename
from .zip_exports import (
    reserve_archive_path,
    temporary_zip_archive,
    write_submission_file_to_archive,
)


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


__all__ = ["export_submissions_today_archive"]
