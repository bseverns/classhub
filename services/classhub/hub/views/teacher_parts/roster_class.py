"""Compatibility facade for teacher class-level roster endpoints."""

from django.views.decorators.http import require_POST

from ...services.helper_control import reset_class_conversations as _reset_helper_class_conversations
from .roster_class_controls import (
    teach_export_class_submissions_today,
    teach_lock_class,
    teach_reset_helper_conversations_impl,
    teach_reset_roster,
    teach_rotate_code,
    teach_toggle_lock,
)
from .roster_class_dashboard import (
    teach_class_dashboard,
    teach_class_join_card,
    teach_create_class,
)
from .shared_auth import staff_member_required


@staff_member_required
@require_POST
def teach_reset_helper_conversations(request, class_id: int):
    # Keep wrapper in this module so existing patch target
    # hub.views.teacher_parts.roster_class._reset_helper_class_conversations stays valid.
    return teach_reset_helper_conversations_impl(
        request=request,
        class_id=class_id,
        reset_helper_conversations_fn=_reset_helper_class_conversations,
    )


__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
]
