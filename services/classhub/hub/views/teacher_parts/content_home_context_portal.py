"""Portal-mode context helpers for teacher home."""


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


def _portal_mode_rows(*, user, portal_mode: str, advanced_tools_enabled: bool) -> list[dict]:
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
    if advanced_tools_enabled and user.is_superuser:
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


def _portal_mode_context(*, user, portal_mode: str, advanced_tools_enabled: bool) -> dict:
    advanced_tools_available = bool(user.is_superuser)
    show_day_sections = portal_mode in {"all", "day"}
    show_setup_sections = portal_mode in {"all", "setup"}
    show_admin_sections = bool(user.is_superuser and advanced_tools_enabled and portal_mode in {"all", "admin"})
    show_policy_sections = bool(advanced_tools_enabled and user.is_superuser and portal_mode in {"all", "policy"})

    return {
        "portal_mode": portal_mode,
        "advanced_tools_available": advanced_tools_available,
        "advanced_tools_enabled": bool(advanced_tools_enabled),
        "advanced_tools_enable_url": "/teach?portal_mode=setup&advanced=1",
        "advanced_tools_disable_url": "/teach?portal_mode=setup",
        "setup_mode_url": "/teach?portal_mode=setup" + ("&advanced=1" if advanced_tools_enabled else ""),
        "admin_mode_url": "/teach?portal_mode=admin&advanced=1",
        "show_teacher_start_here": portal_mode in {"all", "day", "setup"},
        "portal_mode_rows": _portal_mode_rows(
            user=user,
            portal_mode=portal_mode,
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
    advanced_tools_enabled: bool,
) -> str:
    if portal_mode == "admin" and user.is_superuser and advanced_tools_enabled:
        return "org-admin"
    if portal_mode == "policy" and user.is_superuser and advanced_tools_enabled:
        return "rbac-tools"
    if portal_mode in {"setup", "day"} and initial_tab in {"org-admin", "invite-teacher", "rbac-tools"}:
        return "quick-actions"
    return initial_tab


__all__ = [
    "_portal_mode_context",
    "_tab_for_portal_mode",
]
