"""Teacher syllabus import endpoint and helpers."""

import io
import tempfile
import zipfile
from pathlib import Path

from django.http import FileResponse

from ...services.syllabus_ingest import (
    SyllabusIngestError,
    ingest_uploaded_syllabus_files,
)
from .shared import (
    _TEMPLATE_SLUG_RE,
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_can_create_classes,
    staff_member_required,
)


def _syllabus_import_form_state(request):
    source_upload = request.FILES.get("syllabus_source")
    overview_upload = request.FILES.get("syllabus_overview")
    slug = (request.POST.get("import_course_slug") or "").strip().lower()
    title = (request.POST.get("import_course_title") or "").strip()
    default_ui_level = (request.POST.get("import_default_ui_level") or "secondary").strip().lower()
    session_parse_mode = (request.POST.get("import_session_parse_mode") or "auto").strip().lower()
    overwrite = (request.POST.get("import_overwrite") or "").strip() == "1"
    return {
        "source_upload": source_upload,
        "overview_upload": overview_upload,
        "slug": slug,
        "title": title,
        "default_ui_level": default_ui_level,
        "session_parse_mode": session_parse_mode,
        "overwrite": overwrite,
        "form_values": {
            "import_course_slug": slug,
            "import_course_title": title,
            "import_default_ui_level": default_ui_level,
            "import_session_parse_mode": session_parse_mode,
            "import_overwrite": "1" if overwrite else "0",
        },
    }


def _syllabus_import_error(request, *, form_values, message: str):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def _validate_syllabus_import_state(state: dict) -> str:
    source_upload = state.get("source_upload")
    slug = state.get("slug") or ""
    default_ui_level = state.get("default_ui_level") or ""
    session_parse_mode = state.get("session_parse_mode") or ""
    if source_upload is None:
        return "Select a syllabus source file (.md, .docx, or .zip)."
    if slug and not _TEMPLATE_SLUG_RE.match(slug):
        return "Course slug can use lowercase letters, numbers, underscores, and dashes."
    if default_ui_level not in {"elementary", "secondary", "advanced"}:
        return "Default UI level must be elementary, secondary, or advanced."
    if session_parse_mode not in {"auto", "template", "verbose"}:
        return "Session parse mode must be auto, template, or verbose."
    return ""


def _audit_syllabus_import(request, *, result, overwrite: bool):
    _audit(
        request,
        action="teacher_syllabus_import.compile",
        target_type="CourseSyllabus",
        target_id=result.course_slug,
        summary=f"Compiled syllabus source into {result.course_slug}",
        metadata={
            "course_slug": result.course_slug,
            "course_title": result.course_title,
            "lesson_count": result.lesson_count,
            "source_kind": result.source_kind,
            "source_files": result.source_files,
            "ui_level": result.ui_level,
            "overwrite": overwrite,
        },
    )


@staff_member_required
@require_POST
def teach_import_syllabus_source(request):
    state = _syllabus_import_form_state(request)
    form_values = state["form_values"]
    if not staff_can_create_classes(request.user):
        return _syllabus_import_error(
            request,
            form_values=form_values,
            message="Your account cannot compile classes in the current organization scope.",
        )
    error = _validate_syllabus_import_state(state)
    if error:
        return _syllabus_import_error(request, form_values=form_values, message=error)

    try:
        with tempfile.TemporaryDirectory() as scratch_dir:
            scratch_path = Path(scratch_dir).resolve()
            result = ingest_uploaded_syllabus_files(
                source_upload=state["source_upload"],
                course_slug=state["slug"],
                course_title=state["title"],
                overview_upload=state["overview_upload"],
                default_ui_level=state["default_ui_level"],
                session_parse_mode=state["session_parse_mode"],
                overwrite=True,
                courses_root=scratch_path,
            )

            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                course_dir = Path(result.course_dir)
                for file_path in course_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(scratch_path)
                        zf.write(file_path, arcname)

            buffer.seek(0)
            _audit_syllabus_import(request, result=result, overwrite=False)

            return FileResponse(
                buffer,
                as_attachment=True,
                filename=f"coursepack_{result.course_slug}.zip",
            )
    except (SyllabusIngestError, OSError, ValueError) as exc:
        return _syllabus_import_error(
            request,
            form_values=form_values,
            message=f"Syllabus compilation failed: {exc}",
        )


__all__ = [
    "teach_import_syllabus_source",
]
