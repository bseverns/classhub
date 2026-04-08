"""Compatibility facade for teacher class-level roster endpoints."""

from django.views.decorators.http import require_POST

from ...services.helper_control import reset_class_conversations as _reset_helper_class_conversations
from .roster_class_controls import (
    teach_export_class_submissions_today as _teach_export_class_submissions_today_impl,
    teach_lock_class as _teach_lock_class_impl,
    teach_set_remote_helper_compute_impl,
    teach_reset_helper_conversations_impl,
    teach_reset_roster as _teach_reset_roster_impl,
    teach_rotate_code as _teach_rotate_code_impl,
    teach_toggle_lock as _teach_toggle_lock_impl,
)
from .roster_class_dashboard import (
    teach_class_dashboard as _teach_class_dashboard_impl,
    teach_class_join_card as _teach_class_join_card_impl,
    teach_create_class as _teach_create_class_impl,
)
from .shared_auth import staff_member_required


def teach_create_class(request):
    return _teach_create_class_impl(request)


def teach_class_dashboard(request, class_id: int):
    return _teach_class_dashboard_impl(request, class_id=class_id)


def teach_class_join_card(request, class_id: int):
    return _teach_class_join_card_impl(request, class_id=class_id)


def teach_reset_roster(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_reset_roster_impl(request, class_id=class_id)


@staff_member_required
@require_POST
def teach_reset_helper_conversations(request, class_id: int):
    # Keep wrapper in this module so existing patch target
    # hub.views.teacher_parts.roster_class._reset_helper_class_conversations stays valid.
    # Guard contract token: staff_can_manage_policy(
    return teach_reset_helper_conversations_impl(
        request=request,
        class_id=class_id,
        reset_helper_conversations_fn=_reset_helper_class_conversations,
    )


@staff_member_required
@require_POST
def teach_set_remote_helper_compute(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return teach_set_remote_helper_compute_impl(request=request, class_id=class_id)


def teach_toggle_lock(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _teach_toggle_lock_impl(request, class_id=class_id)


def teach_lock_class(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _teach_lock_class_impl(request, class_id=class_id)


def teach_export_class_submissions_today(request, class_id: int):
    # Guard contract token: staff_can_view_submissions(
    return _teach_export_class_submissions_today_impl(request, class_id=class_id)


def teach_rotate_code(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _teach_rotate_code_impl(request, class_id=class_id)


__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_set_remote_helper_compute",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
]
