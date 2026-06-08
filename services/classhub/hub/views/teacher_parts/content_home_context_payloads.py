"""Payload builder helpers for teacher home context assembly."""

from .shared import (
    OrganizationMembership,
    OrganizationRoleCapability,
    Path,
    Submission,
    _AUTHORING_TEMPLATE_SUFFIXES,
    _TEMPLATE_SLUG_RE,
    staff_can_export_syllabi,
    staff_has_explicit_memberships,
)


def _recent_submissions_for_class_ids(class_ids):
    if not class_ids:
        return []
    return list(
        Submission.objects.select_related("student", "material__module__classroom")
        .filter(material__module__classroom_id__in=class_ids)[:20]
    )


def _build_template_download_rows(template_slug: str, output_dir: Path):
    rows: list[dict] = []
    if not template_slug or not _TEMPLATE_SLUG_RE.match(template_slug):
        return rows

    existing_names: set[str] = set()
    try:
        existing_names = {item.name for item in output_dir.iterdir() if item.is_file()}
    except OSError:
        existing_names = set()
    for kind, suffix in _AUTHORING_TEMPLATE_SUFFIXES.items():
        expected_name = f"{template_slug}-{suffix}"
        rows.append(
            {
                "kind": kind,
                "label": expected_name,
                "exists": expected_name in existing_names,
                "url": f"/teach/authoring-template/download?slug={template_slug}&kind={kind}",
            }
        )
    return rows


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
        "template_slug": template_slug,
        "template_title": template_title,
        "template_sessions": template_sessions or "12",
        "template_duration": template_duration or "75",
        "import_course_slug": import_course_slug,
        "import_course_title": import_course_title,
        "import_default_ui_level": (
            import_default_ui_level if import_default_ui_level in {"elementary", "secondary", "advanced"} else "secondary"
        ),
        "import_session_parse_mode": (
            import_session_parse_mode if import_session_parse_mode in {"auto", "template", "verbose"} else "auto"
        ),
        "registry_index": registry_index,
        "registry_course_slug": registry_course_slug,
        "registry_version": registry_version,
        "registry_class_code": registry_class_code,
        "registry_class_name": registry_class_name,
        "registry_create_class": bool(registry_create_class),
        "registry_replace": bool(registry_replace),
        "registry_overwrite_content": bool(registry_overwrite_content),
        "template_output_dir": str(output_dir),
        "template_download_rows": template_download_rows,
    }


def _build_teach_home_staff_context(
    *,
    request,
    teacher_accounts,
    teacher_invite_state: dict,
    profile_state: dict,
    org_state: dict,
    initial_tab: str,
) -> dict:
    return {
        "teacher_accounts": teacher_accounts,
        "teacher_username": teacher_invite_state["teacher_username"],
        "teacher_email": teacher_invite_state["teacher_email"],
        "teacher_first_name": teacher_invite_state["teacher_first_name"],
        "teacher_last_name": teacher_invite_state["teacher_last_name"],
        "teacher_invite_active": teacher_invite_state["teacher_invite_active"],
        "data_lifespan_enabled": bool(request.user.is_superuser or staff_can_export_syllabi(request.user)),
        "initial_top_tab": initial_tab,
        "profile_first_name": profile_state["profile_first_name"],
        "profile_last_name": profile_state["profile_last_name"],
        "profile_email": profile_state["profile_email"],
        "org_name": org_state["org_name"],
        "org_membership_org_id": org_state["org_membership_org_id"],
        "org_membership_user_id": org_state["org_membership_user_id"],
        "org_membership_role": org_state["org_membership_role"] or OrganizationMembership.ROLE_TEACHER,
        "org_membership_active": org_state["org_membership_active"],
        "org_rolecap_org_id": org_state["org_rolecap_org_id"],
        "org_rolecap_role": org_state["org_rolecap_role"] or OrganizationMembership.ROLE_TEACHER,
        "org_rolecap_capability": (org_state["org_rolecap_capability"] or OrganizationRoleCapability.CAP_CLASS_VIEW),
        "org_rolecap_active": org_state["org_rolecap_active"],
        "org_membership_mode": staff_has_explicit_memberships(request.user),
    }


__all__ = [
    "_build_teach_home_class_context",
    "_build_teach_home_staff_context",
    "_build_template_download_rows",
    "_recent_submissions_for_class_ids",
]
