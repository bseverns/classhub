"""Teacher syllabus import endpoint and helpers."""

from django.core.management import call_command
from django.core.management.base import CommandError

from ...services.syllabus_ingest import (
    SyllabusIngestError,
    ingest_uploaded_syllabus_files,
)
from .shared import (
    Class,
    ClassStaffAssignment,
    _TEMPLATE_SLUG_RE,
    _audit,
    _next_unique_class_join_code,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_can_create_classes,
    staff_default_organization,
    staff_member_required,
    transaction,
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


def _create_class_from_import_result(request, *, result):
    class_name = (result.course_title or result.course_slug).strip()[:200] or result.course_slug
    join_code = _next_unique_class_join_code()
    organization = staff_default_organization(request.user)
    with transaction.atomic():
        classroom = Class.objects.create(
            organization=organization,
            name=class_name,
            join_code=join_code,
        )
        if not request.user.is_superuser:
            ClassStaffAssignment.objects.update_or_create(
                classroom=classroom,
                user=request.user,
                defaults={"is_active": True},
            )
        call_command(
            "import_coursepack",
            course_slug=result.course_slug,
            class_code=join_code,
            verbosity=0,
        )
    return classroom


def _audit_syllabus_import(request, *, result, overwrite: bool, classroom):
    _audit(
        request,
        action="teacher_syllabus_import.upload",
        target_type="CourseSyllabus",
        target_id=result.course_slug,
        summary=f"Imported syllabus source into {result.course_slug}",
        metadata={
            "course_slug": result.course_slug,
            "course_title": result.course_title,
            "course_dir": str(result.course_dir),
            "lesson_count": result.lesson_count,
            "source_kind": result.source_kind,
            "source_files": result.source_files,
            "ui_level": result.ui_level,
            "overwrite": overwrite,
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "classroom_join_code": classroom.join_code,
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
            message="Your account cannot create classes in the current organization scope.",
        )
    error = _validate_syllabus_import_state(state)
    if error:
        return _syllabus_import_error(request, form_values=form_values, message=error)

    try:
        result = ingest_uploaded_syllabus_files(
            source_upload=state["source_upload"],
            course_slug=state["slug"],
            course_title=state["title"],
            overview_upload=state["overview_upload"],
            default_ui_level=state["default_ui_level"],
            session_parse_mode=state["session_parse_mode"],
            overwrite=state["overwrite"],
        )
        classroom = _create_class_from_import_result(request, result=result)
    except (SyllabusIngestError, OSError, ValueError, CommandError) as exc:
        return _syllabus_import_error(
            request,
            form_values=form_values,
            message=f"Syllabus import failed: {exc}",
        )

    _audit_syllabus_import(request, result=result, overwrite=state["overwrite"], classroom=classroom)
    notice = (
        f"Imported course '{result.course_slug}' with {result.lesson_count} lessons. "
        f"Created class '{classroom.name}' ({classroom.join_code})."
    )
    success_values = {
        "import_course_slug": result.course_slug,
        "import_course_title": result.course_title,
        "import_default_ui_level": state["default_ui_level"],
        "import_session_parse_mode": state["session_parse_mode"],
        "import_overwrite": "1" if state["overwrite"] else "0",
    }
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, extra=success_values),
        fallback="/teach",
    )


__all__ = [
    "teach_import_syllabus_source",
]
