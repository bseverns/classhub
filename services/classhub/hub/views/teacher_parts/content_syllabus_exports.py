"""Teacher syllabus export endpoints and helper state."""

import re

from ...services.syllabus_exports import (
    build_syllabus_backup_zip,
    build_syllabus_catalog_csv,
    list_syllabus_courses,
)
from .shared import (
    FileResponse,
    HttpResponse,
    _audit,
    apply_download_safety,
    apply_no_store,
    safe_attachment_filename,
    staff_can_export_syllabi,
    staff_member_required,
    timezone,
)

_COURSE_EXPORT_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def build_syllabus_export_state(request):
    enabled = bool(staff_can_export_syllabi(request.user))
    if not enabled:
        return {
            "syllabus_export_enabled": False,
            "syllabus_export_courses": [],
            "syllabus_export_selected_course_slug": "",
        }

    courses = list_syllabus_courses()
    available_slugs = {str(item.get("slug") or "").strip() for item in courses}
    requested_slug = (request.GET.get("syllabus_course_slug") or "").strip()
    if requested_slug in available_slugs:
        selected_slug = requested_slug
    elif courses:
        selected_slug = str(courses[0].get("slug") or "").strip()
    else:
        selected_slug = ""

    return {
        "syllabus_export_enabled": True,
        "syllabus_export_courses": courses,
        "syllabus_export_selected_course_slug": selected_slug,
    }


def _catalog_csv_response(request, *, kind: str, stamp: str):
    body = build_syllabus_catalog_csv()
    filename = safe_attachment_filename(f"classhub_syllabus_catalog_{stamp}.csv")
    response = HttpResponse(body, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    _audit(
        request,
        action="syllabus_export.catalog_csv",
        target_type="SyllabusExport",
        target_id="catalog_csv",
        summary="Exported syllabus catalog CSV",
        metadata={"kind": kind, "filename": filename},
    )
    return response


def _backup_zip_response(request, *, kind: str, stamp: str):
    course_slug = ""
    if kind == "course_zip":
        course_slug = (request.GET.get("course_slug") or "").strip()
        if not course_slug or not _COURSE_EXPORT_SLUG_RE.fullmatch(course_slug):
            return HttpResponse("Invalid course slug.", status=400)
    try:
        tmp, file_count, course_count = build_syllabus_backup_zip(course_slug=course_slug)
    except ValueError:
        return HttpResponse("Invalid course slug.", status=400)
    except FileNotFoundError:
        return HttpResponse("Course not found.", status=404)

    zip_name = (
        f"classhub_syllabus_{course_slug}_{stamp}.zip"
        if course_slug
        else f"classhub_syllabus_backup_{stamp}.zip"
    )
    filename = safe_attachment_filename(zip_name)
    tmp.seek(0)
    response = FileResponse(
        tmp,
        as_attachment=True,
        filename=filename,
        content_type="application/zip",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    _audit(
        request,
        action="syllabus_export.backup_zip",
        target_type="SyllabusExport",
        target_id=course_slug or "all_courses",
        summary="Exported syllabus backup zip",
        metadata={
            "kind": kind,
            "course_slug": course_slug,
            "filename": filename,
            "file_count": file_count,
            "course_count": course_count,
        },
    )
    return response


@staff_member_required
def teach_export_syllabus(request):
    if not staff_can_export_syllabi(request.user):
        return HttpResponse("Forbidden", status=403)

    kind = (request.GET.get("kind") or "").strip().lower()
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    if kind == "catalog_csv":
        return _catalog_csv_response(request, kind=kind, stamp=stamp)
    if kind in {"backup_zip", "course_zip"}:
        return _backup_zip_response(request, kind=kind, stamp=stamp)
    return HttpResponse("Invalid export kind.", status=400)


__all__ = [
    "build_syllabus_export_state",
    "teach_export_syllabus",
]
