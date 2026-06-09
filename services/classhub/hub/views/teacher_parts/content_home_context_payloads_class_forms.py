"""Teacher home class/import payload builders."""

from .shared import Path


def _build_teach_home_class_context(
    *,
    classes: list,
    assigned_class_ids: set[int],
    assigned_classes: list,
    teacher_start_class,
    teacher_start_submission_material_id: int,
    class_digest_rows: list,
    digest_since,
    recent_submissions: list,
    notice: str,
    error: str,
    template_slug: str,
    template_title: str,
    template_sessions: str,
    template_duration: str,
    import_course_slug: str,
    import_course_title: str,
    import_default_ui_level: str,
    import_session_parse_mode: str,
    registry_index: str,
    registry_course_slug: str,
    registry_version: str,
    registry_class_code: str,
    registry_class_name: str,
    registry_create_class: bool,
    registry_replace: bool,
    registry_overwrite_content: bool,
    output_dir: Path,
    template_download_rows: list,
) -> dict:
    return {
        **_base_teach_home_class_context(
            classes=classes,
            assigned_class_ids=assigned_class_ids,
            assigned_classes=assigned_classes,
            teacher_start_class=teacher_start_class,
            teacher_start_submission_material_id=teacher_start_submission_material_id,
            class_digest_rows=class_digest_rows,
            digest_since=digest_since,
            recent_submissions=recent_submissions,
            notice=notice,
            error=error,
        ),
        **_template_form_context(
            template_slug=template_slug,
            template_title=template_title,
            template_sessions=template_sessions,
            template_duration=template_duration,
            output_dir=output_dir,
            template_download_rows=template_download_rows,
        ),
        **_syllabus_import_form_context(
            import_course_slug=import_course_slug,
            import_course_title=import_course_title,
            import_default_ui_level=import_default_ui_level,
            import_session_parse_mode=import_session_parse_mode,
        ),
        **_registry_import_form_context(
            registry_index=registry_index,
            registry_course_slug=registry_course_slug,
            registry_version=registry_version,
            registry_class_code=registry_class_code,
            registry_class_name=registry_class_name,
            registry_create_class=registry_create_class,
            registry_replace=registry_replace,
            registry_overwrite_content=registry_overwrite_content,
        ),
    }


def _base_teach_home_class_context(
    *,
    classes: list,
    assigned_class_ids: set[int],
    assigned_classes: list,
    teacher_start_class,
    teacher_start_submission_material_id: int,
    class_digest_rows: list,
    digest_since,
    recent_submissions: list,
    notice: str,
    error: str,
) -> dict:
    return {
        "classes": classes,
        "assigned_class_ids": assigned_class_ids,
        "assigned_classes": assigned_classes,
        "teacher_start_class": teacher_start_class,
        "teacher_start_submission_material_id": int(teacher_start_submission_material_id),
        "class_digest_rows": class_digest_rows,
        "digest_since": digest_since,
        "recent_submissions": recent_submissions,
        "notice": notice,
        "error": error,
    }


def _template_form_context(
    *,
    template_slug: str,
    template_title: str,
    template_sessions: str,
    template_duration: str,
    output_dir: Path,
    template_download_rows: list,
) -> dict:
    return {
        "template_slug": template_slug,
        "template_title": template_title,
        "template_sessions": template_sessions or "12",
        "template_duration": template_duration or "75",
        "template_output_dir": str(output_dir),
        "template_download_rows": template_download_rows,
    }


def _syllabus_import_form_context(
    *,
    import_course_slug: str,
    import_course_title: str,
    import_default_ui_level: str,
    import_session_parse_mode: str,
) -> dict:
    return {
        "import_course_slug": import_course_slug,
        "import_course_title": import_course_title,
        "import_default_ui_level": (
            import_default_ui_level if import_default_ui_level in {"elementary", "secondary", "advanced"} else "secondary"
        ),
        "import_session_parse_mode": (
            import_session_parse_mode if import_session_parse_mode in {"auto", "template", "verbose"} else "auto"
        ),
    }


def _registry_import_form_context(
    *,
    registry_index: str,
    registry_course_slug: str,
    registry_version: str,
    registry_class_code: str,
    registry_class_name: str,
    registry_create_class: bool,
    registry_replace: bool,
    registry_overwrite_content: bool,
) -> dict:
    return {
        "registry_index": registry_index,
        "registry_course_slug": registry_course_slug,
        "registry_version": registry_version,
        "registry_class_code": registry_class_code,
        "registry_class_name": registry_class_name,
        "registry_create_class": bool(registry_create_class),
        "registry_replace": bool(registry_replace),
        "registry_overwrite_content": bool(registry_overwrite_content),
    }


__all__ = ["_build_teach_home_class_context"]
