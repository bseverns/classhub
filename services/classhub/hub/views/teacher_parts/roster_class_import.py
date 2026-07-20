"""Teacher class creation and content import logic."""

from django.http import HttpResponse
from django.shortcuts import redirect

from ...models import Class, ClassStaffAssignment
from ...services.coursepack_import import CoursepackImportError, import_content_upload_to_class
from .shared_auth import (
    staff_can_create_classes,
    staff_default_organization,
    staff_member_required,
)
from .shared_ordering import _next_unique_class_join_code
from .shared_routing import _audit, _teach_class_path, _with_notice


def _clean_class_seed_value(raw: str | None, *, limit: int) -> str:
    return (raw or "").strip()[:limit]


def _should_open_class_workspace(request) -> bool:
    raw = (request.POST.get("open_after_create") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _class_content_import_upload(request):
    return request.FILES.get("class_content_import")


def _class_content_import_requested(request) -> bool:
    raw = (request.POST.get("class_content_import_intent") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    return _class_content_import_upload(request) is not None


def _class_content_import_options(request) -> dict:
    return {
        "course_slug": _clean_class_seed_value(request.POST.get("import_course_slug"), limit=120).lower(),
        "course_title": _clean_class_seed_value(request.POST.get("import_course_title"), limit=200),
        "default_ui_level": _clean_class_seed_value(request.POST.get("import_default_ui_level"), limit=20) or "secondary",
        "session_parse_mode": _clean_class_seed_value(request.POST.get("import_session_parse_mode"), limit=20) or "auto",
        "overwrite_content": (request.POST.get("import_overwrite_content") or "").strip().lower()
        in {"1", "true", "yes", "on"},
    }


def _get_create_form_data(request):
    return {
        "name": _clean_class_seed_value(request.POST.get("name"), limit=200),
        "landing_title": _clean_class_seed_value(request.POST.get("student_landing_title"), limit=200),
        "landing_message": _clean_class_seed_value(request.POST.get("student_landing_message"), limit=4000),
        "first_module_title": _clean_class_seed_value(request.POST.get("first_module_title"), limit=200),
        "open_after": _should_open_class_workspace(request),
    }


def _handle_class_import(request, classroom):
    source_upload = _class_content_import_upload(request)
    if source_upload is None:
        return None
    try:
        return import_content_upload_to_class(
            source_upload=source_upload,
            classroom=classroom,
            replace=True,
            **_class_content_import_options(request),
        )
    except CoursepackImportError as exc:
        classroom.delete()
        raise exc


def _audit_class_create(request, classroom, data, import_result, created_module):
    _audit(
        request,
        action="class.create",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Created class {classroom.name}",
        metadata={
            "join_code": classroom.join_code,
            "organization_id": classroom.organization_id,
            "has_student_landing_title": bool(data["landing_title"]),
            "has_student_landing_message": bool(data["landing_message"]),
            "created_first_module": bool(created_module),
            "first_module_id": created_module.id if created_module else None,
            "imported_course_slug": import_result.course_slug if import_result else "",
            "imported_course_title": import_result.course_title if import_result else "",
            "import_source_kind": import_result.source_kind if import_result else "",
        },
    )
    if import_result:
        _audit(
            request,
            action="class.content_import",
            classroom=classroom,
            target_type="Coursepack",
            target_id=import_result.course_slug,
            summary=f"Imported course content into {classroom.name}",
            metadata={
                "course_slug": import_result.course_slug,
                "course_title": import_result.course_title,
                "source_kind": import_result.source_kind,
                "source_files": list(import_result.source_files),
                "created_modules": import_result.created_modules,
                "created_materials": import_result.created_materials,
                "created_assets": import_result.created_assets,
                "course_dir": str(import_result.course_dir),
                "writes_live_content": True,
            },
        )


@staff_member_required
def teach_create_class(request):
    from django.views.decorators.http import require_POST

    @require_POST
    def _inner(request):
        if not staff_can_create_classes(request.user):
            return HttpResponse("Forbidden", status=403)
        import_requested = _class_content_import_requested(request)
        if import_requested and not request.user.is_superuser:
            return HttpResponse("Forbidden", status=403)
        data = _get_create_form_data(request)
        if not data["name"]:
            return redirect("/teach")
        if import_requested and not _class_content_import_upload(request):
            return redirect(_with_notice("/teach", error="Import requested but no file found."))
        if (
            import_requested
            and _class_content_import_options(request)["overwrite_content"]
            and (request.POST.get("confirm_overwrite_content") or "").strip() != "OVERWRITE"
        ):
            return redirect(_with_notice("/teach", error="Type OVERWRITE to confirm live course replacement."))

        classroom = Class.objects.create(
            organization=staff_default_organization(request.user),
            name=data["name"],
            join_code=_next_unique_class_join_code(),
            student_landing_title=data["landing_title"],
            student_landing_message=data["landing_message"],
        )
        try:
            import_res = _handle_class_import(request, classroom)
        except CoursepackImportError as exc:
            return redirect(_with_notice("/teach", error=f"Import failed: {exc}"))

        mod = None
        if data["first_module_title"] and not import_res:
            mod = classroom.modules.create(title=data["first_module_title"], order_index=0)

        if not request.user.is_superuser:
            ClassStaffAssignment.objects.update_or_create(classroom=classroom, user=request.user, defaults={"is_active": True})

        _audit_class_create(request, classroom, data, import_res, mod)
        if data["open_after"]:
            return redirect(_with_notice(_teach_class_path(classroom.id), "Class workspace created."))
        return redirect("/teach")

    return _inner(request)

