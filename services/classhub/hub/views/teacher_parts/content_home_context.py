"""Compatibility facade for teacher home context builders."""

from .content_home_context_payloads import (
    _build_teach_home_class_context,
    _build_teach_home_staff_context,
    _build_template_download_rows,
    _recent_submissions_for_class_ids,
)
from .content_home_context_portal import (
    _portal_mode_context as _portal_mode_context_impl,
    _tab_for_portal_mode as _tab_for_portal_mode_impl,
)
from .content_home_context_state import (
    _read_advanced_tools_state as _read_advanced_tools_state_impl,
    _read_portal_mode as _read_portal_mode_impl,
    _read_profile_state as _read_profile_state_impl,
    _read_teacher_invite_state as _read_teacher_invite_state_impl,
    _resolve_initial_top_tab as _resolve_initial_top_tab_impl,
)
from .content_home_org_admin import _build_org_admin_context, _read_org_admin_state


def _read_profile_state(request, user):
    return _read_profile_state_impl(request, user)


def _read_teacher_invite_state(request):
    return _read_teacher_invite_state_impl(request)


def _resolve_initial_top_tab(*, user, profile_tab_active, org_admin_active, teacher_invite_active, rbac_tools_active):
    return _resolve_initial_top_tab_impl(
        user=user,
        profile_tab_active=profile_tab_active,
        org_admin_active=org_admin_active,
        teacher_invite_active=teacher_invite_active,
        rbac_tools_active=rbac_tools_active,
    )


def _read_advanced_tools_state(request, *, user) -> bool:
    if not user.is_superuser:
        return False
    return _read_advanced_tools_state_impl(request, user=user)


def _read_portal_mode(request, *, user, advanced_tools_enabled: bool) -> str:
    return _read_portal_mode_impl(
        request,
        user=user,
        advanced_tools_enabled=advanced_tools_enabled,
    )


def _portal_mode_context(*, user, portal_mode: str, advanced_tools_enabled: bool) -> dict:
    show_policy_sections = bool(advanced_tools_enabled and user.is_superuser and portal_mode in {"all", "policy"})
    if advanced_tools_enabled and user.is_superuser:
        pass
    context = _portal_mode_context_impl(
        user=user,
        portal_mode=portal_mode,
        advanced_tools_enabled=advanced_tools_enabled,
    )
    context["show_policy_sections"] = show_policy_sections
    return context


def _tab_for_portal_mode(initial_tab: str, *, portal_mode: str, user, advanced_tools_enabled: bool) -> str:
    return _tab_for_portal_mode_impl(
        initial_tab,
        portal_mode=portal_mode,
        user=user,
        advanced_tools_enabled=advanced_tools_enabled,
    )

__all__ = [
    "_build_org_admin_context",
    "_build_teach_home_class_context",
    "_build_teach_home_staff_context",
    "_build_template_download_rows",
    "_portal_mode_context",
    "_read_advanced_tools_state",
    "_read_org_admin_state",
    "_read_portal_mode",
    "_read_profile_state",
    "_read_teacher_invite_state",
    "_recent_submissions_for_class_ids",
    "_resolve_initial_top_tab",
    "_tab_for_portal_mode",
]
