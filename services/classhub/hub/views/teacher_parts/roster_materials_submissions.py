"""Teacher material submissions endpoints."""

from .shared import (
    FileResponse,
    HttpResponse,
    Material,
    Path,
    Submission,
    _temporary_zip_archive,
    _write_submission_file_to_archive,
    apply_download_safety,
    apply_no_store,
    render,
    safe_attachment_filename,
    safe_filename,
    staff_can_view_submissions,
    staff_member_required,
)
from ...services.teacher_material_reviews import build_rubric_material_rows


def _build_latest_submission_maps(*, all_subs: list) -> tuple[dict, dict]:
    latest_by_student = {}
    count_by_student = {}
    for submission in all_subs:
        sid = submission.student_id
        count_by_student[sid] = count_by_student.get(sid, 0) + 1
        if sid not in latest_by_student:
            latest_by_student[sid] = submission
    return latest_by_student, count_by_student


def _base_student_rows(*, students: list, latest_by_student: dict, count_by_student: dict) -> tuple[list[dict], int]:
    rows = []
    missing = 0
    for student in students:
        latest = latest_by_student.get(student.id)
        count = count_by_student.get(student.id, 0)
        if not latest:
            missing += 1
        rows.append({"student": student, "latest": latest, "count": count})
    return rows, missing


def _filtered_rows(*, rows: list[dict], show: str) -> list[dict]:
    if show == "missing":
        return [row for row in rows if row["latest"] is None]
    if show == "submitted":
        return [row for row in rows if row["latest"] is not None]
    return rows


def _zip_latest_submissions_response(*, classroom, material, students: list, latest_by_student: dict):
    with _temporary_zip_archive() as (tmp, archive):
        for student in students:
            submission = latest_by_student.get(student.id)
            if not submission:
                continue
            base_name = safe_filename(student.display_name)
            original = safe_filename(submission.original_filename or Path(submission.file.name).name)
            arcname = f"{base_name}/{original}"
            if not _write_submission_file_to_archive(
                archive,
                submission=submission,
                arcname=arcname,
                allow_file_fallback=False,
            ):
                continue

    download_name = safe_attachment_filename(
        f"{safe_filename(classroom.name)}_material_{material.id}_latest.zip"
    )
    tmp.seek(0)
    response = FileResponse(
        tmp,
        as_attachment=True,
        filename=download_name,
        content_type="application/zip",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_material_submissions(request, material_id: int):
    material = Material.objects.select_related("module__classroom").filter(id=material_id).first()
    if not material or material.type not in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY, Material.TYPE_RUBRIC}:
        return HttpResponse("Not found", status=404)

    classroom = material.module.classroom
    if not staff_can_view_submissions(request.user, classroom, module_id=material.module_id):
        return HttpResponse("Not found", status=404)

    students = list(classroom.students.all().order_by("created_at", "id"))
    all_subs = []
    if material.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
        all_subs = list(
            Submission.objects.filter(material=material)
            .select_related("student")
            .order_by("-uploaded_at", "-id")
        )
    latest_by_student, count_by_student = _build_latest_submission_maps(all_subs=all_subs)

    show = (request.GET.get("show") or "all").strip()
    if material.type == Material.TYPE_RUBRIC:
        rows, missing = build_rubric_material_rows(material=material, students=students, show=show)
        return render(
            request,
            "teach_material_submissions.html",
            {
                "classroom": classroom,
                "module": material.module,
                "material": material,
                "rows": rows,
                "student_count": len(students),
                "missing": missing,
                "show": show,
                "is_rubric": True,
            },
        )

    if request.GET.get("download") == "zip_latest":
        return _zip_latest_submissions_response(
            classroom=classroom,
            material=material,
            students=students,
            latest_by_student=latest_by_student,
        )

    rows, missing = _base_student_rows(
        students=students,
        latest_by_student=latest_by_student,
        count_by_student=count_by_student,
    )
    rows = _filtered_rows(rows=rows, show=show)

    return render(
        request,
        "teach_material_submissions.html",
        {
            "classroom": classroom,
            "module": material.module,
            "material": material,
            "rows": rows,
            "missing": missing,
            "student_count": len(students),
            "show": show,
            "is_gallery": material.type == Material.TYPE_GALLERY,
        },
    )


__all__ = ["teach_material_submissions"]
