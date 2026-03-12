"""Compatibility facade for teacher facilitator-support endpoints."""

from .roster_support_signals import (
    teach_resolve_delete_request,
    teach_resolve_stuck_flag,
)
from .roster_support_tags import (
    teach_add_support_tag,
    teach_remove_support_tag,
)

__all__ = [
    "teach_add_support_tag",
    "teach_remove_support_tag",
    "teach_resolve_delete_request",
    "teach_resolve_stuck_flag",
]
