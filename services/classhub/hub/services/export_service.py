"""Portfolio/export service helpers."""

from pathlib import Path

from django.http import FileResponse
from django.template.loader import render_to_string
from django.utils import timezone

from ..http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ..models import Class, StudentIdentity, Submission
from .filenames import safe_filename
from .zip_exports import reserve_archive_path, temporary_zip_archive, write_submission_file_to_archive


def build_student_portfolio_export_response(
    *,
    student: StudentIdentity,
    classroom: Class,
    filename_mode: str = "generic",
) -> FileResponse:
    submissions = list(
        Submission.objects.filter(student=student, material__module__classroom=classroom)
        .select_related("material__module")
        .order_by("uploaded_at", "id")
    )

    generated_at = timezone.localtime(timezone.now())
    rows: list[dict] = []
    used_archive_paths: set[str] = set()

    with temporary_zip_archive() as (tmp, archive):
        for sub in submissions:
            local_uploaded_at = timezone.localtime(sub.uploaded_at)
            module_label = safe_filename(sub.material.module.title or "module")
            material_label = safe_filename(sub.material.title or "material")
            original = safe_filename(sub.original_filename or Path(sub.file.name).name or "submission")
            timestamp = local_uploaded_at.strftime("%Y%m%d_%H%M%S")
            archive_path = reserve_archive_path(
                f"files/{module_label}/{material_label}/{timestamp}_{sub.id}_{original}",
                used_archive_paths,
                fallback=f"files/{module_label}/{material_label}/{timestamp}_{sub.id}_dup_{original}",
            )
            included = write_submission_file_to_archive(
                archive,
                submission=sub,
                arcname=archive_path,
                allow_file_fallback=True,
            )
            status = "ok" if included else "missing"
            rows.append(
                {
                    "submission_id": sub.id,
                    "module_title": sub.material.module.title,
                    "material_title": sub.material.title,
                    "uploaded_at": local_uploaded_at,
                    "original_filename": sub.original_filename or Path(sub.file.name).name,
                    "note": sub.note or "",
                    "archive_path": archive_path,
                    "included": included,
                    "status": status,
                }
            )

        index_html = render_to_string(
            "student_portfolio_index.html",
            {
                "student": student,
                "classroom": classroom,
                "generated_at": generated_at,
                "rows": rows,
                "submission_count": len(rows),
                "included_count": sum(1 for row in rows if row["included"]),
            },
        )
        archive.writestr("index.html", index_html.encode("utf-8"))

    stamp = generated_at.strftime("%Y%m%d")
    mode = (filename_mode or "generic").strip().lower()
    if mode == "descriptive":
        student_name = safe_filename(student.display_name or "student")
        class_name = safe_filename(classroom.name or "classroom")
        filename = safe_attachment_filename(f"{class_name}_{student_name}_portfolio_{stamp}.zip")
    else:
        filename = safe_attachment_filename(f"portfolio_{stamp}.zip")

    tmp.seek(0)
    response = FileResponse(
        tmp,
        as_attachment=True,
        filename=filename,
        content_type="application/zip",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "build_student_portfolio_export_response",
]
