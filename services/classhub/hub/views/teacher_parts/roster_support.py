"""Compatibility facade for teacher facilitator-support endpoints."""

from .roster_support_signals import (
    teach_resolve_delete_request as _teach_resolve_delete_request_impl,
    teach_resolve_stuck_flag as _teach_resolve_stuck_flag_impl,
)
from .roster_support_tags import (
    teach_add_support_tag as _teach_add_support_tag_impl,
    teach_remove_support_tag as _teach_remove_support_tag_impl,
)


def teach_resolve_stuck_flag(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_resolve_stuck_flag_impl(request, class_id=class_id)


def teach_resolve_delete_request(request, class_id: int):
    return _teach_resolve_delete_request_impl(request, class_id=class_id)


def teach_add_support_tag(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_add_support_tag_impl(request, class_id=class_id)


def teach_remove_support_tag(request, class_id: int):
    return _teach_remove_support_tag_impl(request, class_id=class_id)

__all__ = [
    "teach_add_support_tag",
    "teach_remove_support_tag",
    "teach_resolve_delete_request",
    "teach_resolve_stuck_flag",
]
