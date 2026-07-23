"""State-reading helpers for teacher home context assembly."""

from ...services.org_access import staff_accessible_classes_queryset


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
    advanced_tools_enabled: bool,
) -> str:
    requested = (request.GET.get("portal_mode") or "").strip().lower()
    default_mode = "day" if staff_accessible_classes_queryset(user).exists() else "setup"
    allowed = {"day", "setup"}
    if user.is_superuser and advanced_tools_enabled:
        allowed.add("all")
        allowed.add("admin")
    if advanced_tools_enabled and user.is_superuser:
        allowed.add("policy")
    if requested not in allowed:
        return default_mode
    return requested


__all__ = [
    "_read_advanced_tools_state",
    "_read_portal_mode",
    "_read_profile_state",
    "_read_teacher_invite_state",
    "_resolve_initial_top_tab",
]
