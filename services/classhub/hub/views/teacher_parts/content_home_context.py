"""Context builders for the teacher home view."""

from .content_home_org_admin import _build_org_admin_context, _read_org_admin_state
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


def _read_profile_state(request, user):
    profile_first_name = (request.GET.get("profile_first_name") or "").strip()
    profile_last_name = (request.GET.get("profile_last_name") or "").strip()
    profile_email = (request.GET.get("profile_email") or "").strip()
    return {
        "profile_first_name": profile_first_name or (user.first_name or ""),
        "profile_last_name": profile_last_name or (user.last_name or ""),
        "profile_email": profile_email or (user.email or ""),
        "profile_tab_active": (request.GET.get("profile_tab") or "").strip() == "1"
        or bool(profile_first_name or profile_last_name or profile_email),
    }


def _read_teacher_invite_state(request):
    teacher_username = (request.GET.get("teacher_username") or "").strip()
    teacher_email = (request.GET.get("teacher_email") or "").strip()
    teacher_first_name = (request.GET.get("teacher_first_name") or "").strip()
    teacher_last_name = (request.GET.get("teacher_last_name") or "").strip()
    teacher_invite_open = (request.GET.get("teacher_invite") or "").strip() == "1"
    return {
        "teacher_username": teacher_username,
        "teacher_email": teacher_email,
        "teacher_first_name": teacher_first_name,
        "teacher_last_name": teacher_last_name,
        "teacher_invite_open": teacher_invite_open,
        "teacher_invite_active": bool(
            teacher_invite_open or teacher_username or teacher_email or teacher_first_name or teacher_last_name
        ),
    }


def _resolve_initial_top_tab(*, user, profile_tab_active, org_admin_active, teacher_invite_active, rbac_tools_active):
    if profile_tab_active:
        return "profile"
    if rbac_tools_active:
        return "rbac-tools"
    if user.is_superuser and org_admin_active:
        return "org-admin"
    if user.is_superuser and teacher_invite_active:
        return "invite-teacher"
    return "quick-actions"


def _read_advanced_tools_state(request, *, user) -> bool:
    if not user.is_superuser:
        return False
    return (request.GET.get("advanced") or "").strip() == "1"


def _read_portal_mode(
    request,
    *,
    user,
    rbac_tools_enabled: bool,
    advanced_tools_enabled: bool,
) -> str:
    requested = (request.GET.get("portal_mode") or "").strip().lower()
    default_mode = "setup"
    allowed = {"day", "setup"}
    if user.is_superuser and advanced_tools_enabled:
        allowed.add("all")
        allowed.add("admin")
    if advanced_tools_enabled and (user.is_superuser or rbac_tools_enabled):
        allowed.add("policy")
    if requested not in allowed:
        return default_mode
    return requested


def _portal_mode_row(*, mode_id: str, label: str, description: str, portal_mode: str, advanced_tools_enabled: bool) -> dict:
    url = f"/teach?portal_mode={mode_id}"
    if advanced_tools_enabled:
        url = f"{url}&advanced=1"
    return {
        "id": mode_id,
        "label": label,
        "description": description,
        "url": url,
        "active": portal_mode == mode_id,
    }


def _portal_mode_rows(*, user, portal_mode: str, rbac_tools_enabled: bool, advanced_tools_enabled: bool) -> list[dict]:
    rows = [
        _portal_mode_row(
            mode_id="day",
            label="Day-of-class",
            description="Live class digest and closeout.",
            portal_mode=portal_mode,
            advanced_tools_enabled=advanced_tools_enabled,
        ),
        _portal_mode_row(
            mode_id="setup",
            label="Class setup",
            description="Class creation and content tools.",
            portal_mode=portal_mode,
            advanced_tools_enabled=advanced_tools_enabled,
        ),
    ]
    if user.is_superuser and advanced_tools_enabled:
        rows.insert(
            0,
            _portal_mode_row(
                mode_id="all",
                label="All panels",
                description="Full teacher cockpit.",
                portal_mode=portal_mode,
                advanced_tools_enabled=advanced_tools_enabled,
            ),
        )
        rows.append(
            _portal_mode_row(
                mode_id="admin",
                label="Org/admin",
                description="Teacher invites and organization controls.",
                portal_mode=portal_mode,
                advanced_tools_enabled=advanced_tools_enabled,
            )
        )
    if advanced_tools_enabled and (user.is_superuser or rbac_tools_enabled):
        rows.append(
            _portal_mode_row(
                mode_id="policy",
                label="Policy/RBAC",
                description="RBAC tools and operator policy posture.",
                portal_mode=portal_mode,
                advanced_tools_enabled=advanced_tools_enabled,
            )
        )
    return rows


def _portal_mode_context(*, user, portal_mode: str, rbac_tools_enabled: bool, advanced_tools_enabled: bool) -> dict:
    advanced_tools_available = bool(user.is_superuser)
    show_day_sections = portal_mode in {"all", "day"}
    show_setup_sections = portal_mode in {"all", "setup"}
    show_admin_sections = bool(user.is_superuser and advanced_tools_enabled and portal_mode in {"all", "admin"})
    show_policy_sections = bool(
        advanced_tools_enabled and (user.is_superuser or rbac_tools_enabled) and portal_mode in {"all", "policy"}
    )

    return {
        "portal_mode": portal_mode,
        "advanced_tools_available": advanced_tools_available,
        "advanced_tools_enabled": bool(advanced_tools_enabled),
        "advanced_tools_enable_url": "/teach?portal_mode=setup&advanced=1",
        "advanced_tools_disable_url": "/teach?portal_mode=setup",
        "portal_mode_rows": _portal_mode_rows(
            user=user,
            portal_mode=portal_mode,
            rbac_tools_enabled=rbac_tools_enabled,
            advanced_tools_enabled=advanced_tools_enabled,
        ),
        "show_day_sections": show_day_sections,
        "show_setup_sections": show_setup_sections,
        "show_admin_sections": show_admin_sections,
        "show_policy_sections": show_policy_sections,
        "show_setup_console": show_setup_sections or show_admin_sections or show_policy_sections,
    }


def _tab_for_portal_mode(
    initial_tab: str,
    *,
    portal_mode: str,
    user,
    rbac_tools_enabled: bool,
    advanced_tools_enabled: bool,
) -> str:
    if portal_mode == "admin" and user.is_superuser and advanced_tools_enabled:
        return "org-admin"
    if portal_mode == "policy" and rbac_tools_enabled and advanced_tools_enabled:
        return "rbac-tools"
    if portal_mode in {"setup", "day"} and initial_tab in {"org-admin", "invite-teacher", "rbac-tools"}:
        return "quick-actions"
    return initial_tab


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
    import_overwrite: bool,
    output_dir: Path,
    template_download_rows: list,
) -> dict:
    return {
        "classes": classes,
        "assigned_class_ids": assigned_class_ids,
        "assigned_classes": assigned_classes,
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
        "import_overwrite": import_overwrite,
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
    "_build_org_admin_context",
    "_build_teach_home_class_context",
    "_build_teach_home_staff_context",
    "_build_template_download_rows",
    "_portal_mode_context",
    "_read_org_admin_state",
    "_read_portal_mode",
    "_read_profile_state",
    "_read_teacher_invite_state",
    "_recent_submissions_for_class_ids",
    "_resolve_initial_top_tab",
    "_tab_for_portal_mode",
]
