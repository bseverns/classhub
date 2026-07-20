"""Teacher portal registry import endpoint and helpers."""

from ...services.coursepack_import import CoursepackImportError, import_coursepack_registry
from .shared import (
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_can_create_classes,
    staff_default_organization,
    staff_member_required,
)


def _registry_import_form_state(request):
    index = (request.POST.get("registry_index") or "").strip()
    course_slug = (request.POST.get("registry_course_slug") or "").strip().lower()
    registry_version = (request.POST.get("registry_version") or "").strip()
    class_code = (request.POST.get("registry_class_code") or "").strip().upper()
    class_name = (request.POST.get("registry_class_name") or "").strip()
    create_class = (request.POST.get("registry_create_class") or "").strip().lower() in {"1", "true", "yes", "on"}
    replace = (request.POST.get("registry_replace") or "").strip().lower() in {"1", "true", "yes", "on"}
    overwrite_content = (request.POST.get("registry_overwrite_content") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "index": index,
        "course_slug": course_slug,
        "registry_version": registry_version,
        "class_code": class_code,
        "class_name": class_name,
        "create_class": create_class,
        "replace": replace,
        "overwrite_content": overwrite_content,
        "overwrite_confirmed": (request.POST.get("confirm_overwrite_content") or "").strip() == "OVERWRITE",
        "form_values": {
            "registry_index": index,
            "registry_course_slug": course_slug,
            "registry_version": registry_version,
            "registry_class_code": class_code,
            "registry_class_name": class_name,
            "registry_create_class": "1" if create_class else "",
            "registry_replace": "1" if replace else "",
            "registry_overwrite_content": "1" if overwrite_content else "",
        },
    }


def _registry_import_error(request, *, form_values: dict, message: str):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def _validate_registry_import_state(state: dict) -> str:
    index = state.get("index") or ""
    course_slug = state.get("course_slug") or ""
    class_code = state.get("class_code") or ""
    class_name = state.get("class_name") or ""

    if not index:
        return "Registry index path or URL is required."
    if not course_slug:
        return "Registry course slug is required."
    if class_code and class_name:
        return "Use a class code or class name, not both."
    if (state.get("replace") or state.get("overwrite_content")) and not state.get("overwrite_confirmed"):
        return "Type OVERWRITE to confirm live course replacement."
    return ""


def _audit_registry_import(request, *, result, create_class: bool, replace: bool, overwrite_content: bool):
    _audit(
        request,
        action="coursepack.registry.import",
        classroom=result.classroom,
        target_type="Coursepack",
        target_id=result.course_slug,
        summary=f"Imported registry coursepack for {result.course_slug}",
        metadata={
            "import_channel": "teacher_portal",
            "course_slug": result.course_slug,
            "course_title": result.course_title,
            "classroom_id": result.classroom.id,
            "join_code": result.classroom.join_code,
            "course_dir": str(result.course_dir),
            "created_modules": result.created_modules,
            "created_materials": result.created_materials,
            "created_assets": result.created_assets,
            "extracted_files": result.extracted_files,
            "source_kind": result.source_kind,
            "source_files": list(result.source_files),
            "source_metadata": result.source_metadata,
            "create_class": create_class,
            "replace": replace,
            "overwrite_content": overwrite_content,
        },
    )


@staff_member_required
@require_POST
def teach_import_coursepack_registry(request):
    if not staff_can_create_classes(request.user) or not request.user.is_superuser:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Only superusers can import live course content from a registry."),
            fallback="/teach",
        )

    state = _registry_import_form_state(request)
    form_values = state["form_values"]
    error = _validate_registry_import_state(state)
    if error:
        return _registry_import_error(request, form_values=form_values, message=error)

    try:
        result = import_coursepack_registry(
            index_location=state["index"],
            course_slug=state["course_slug"],
            version=state["registry_version"],
            class_code=state["class_code"],
            class_name=state["class_name"],
            create_class=state["create_class"],
            replace=state["replace"],
            overwrite_content=state["overwrite_content"],
            organization=staff_default_organization(request.user),
        )
    except CoursepackImportError as exc:
        return _registry_import_error(request, form_values=form_values, message=f"Registry import failed: {exc}")

    _audit_registry_import(
        request,
        result=result,
        create_class=state["create_class"],
        replace=state["replace"],
        overwrite_content=state["overwrite_content"],
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            "/teach",
            notice=(
                f"Imported {result.course_slug} into {result.classroom.name} "
                f"({result.classroom.join_code})."
            ),
        ),
        fallback="/teach",
    )


__all__ = ["teach_import_coursepack_registry"]
