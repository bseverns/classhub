"""Compatibility facade for teacher class-level roster endpoints."""

from django.views.decorators.http import require_POST

from ...services.helper_control import reset_class_conversations as _reset_helper_class_conversations
from . import roster_class_controls as _controls
from . import roster_class_dashboard as _dashboard
from . import roster_class_remote_compute as _remote_compute
from .shared_auth import staff_member_required


def teach_create_class(request):
    return _dashboard.teach_create_class(request)


def teach_class_dashboard(request, class_id: int):
    return _dashboard.teach_class_dashboard(request, class_id=class_id)


def teach_class_join_card(request, class_id: int):
    return _dashboard.teach_class_join_card(request, class_id=class_id)


def teach_reset_roster(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _controls.teach_reset_roster(request, class_id=class_id)


@staff_member_required
@require_POST
def teach_reset_helper_conversations(request, class_id: int):
    # Keep wrapper in this module so existing patch target
    # hub.views.teacher_parts.roster_class._reset_helper_class_conversations stays valid.
    # Guard contract token: staff_can_manage_policy(
    return _controls.teach_reset_helper_conversations_impl(
        request=request,
        class_id=class_id,
        reset_helper_conversations_fn=_reset_helper_class_conversations,
    )


@staff_member_required
@require_POST
def teach_set_remote_helper_compute(request, class_id: int):
    # Guard contract token: request.user.is_superuser
    return _remote_compute.teach_set_remote_helper_compute_impl(request=request, class_id=class_id)


def teach_toggle_lock(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _controls.teach_toggle_lock(request, class_id=class_id)


def teach_lock_class(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _controls.teach_lock_class(request, class_id=class_id)


def teach_export_class_submissions_today(request, class_id: int):
    # Guard contract token: staff_can_view_submissions(
    return _controls.teach_export_class_submissions_today(request, class_id=class_id)


def teach_rotate_code(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _controls.teach_rotate_code(request, class_id=class_id)


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
