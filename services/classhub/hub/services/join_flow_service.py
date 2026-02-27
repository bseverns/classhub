"""Join-flow service facade for student session entry."""

from .student_join import (
    JoinResolution,
    JoinValidationError,
    apply_device_hint_cookie,
    clear_device_hint_cookie,
    normalize_display_name,
    resolve_join_student,
)

__all__ = [
    "JoinResolution",
    "JoinValidationError",
    "apply_device_hint_cookie",
    "clear_device_hint_cookie",
    "normalize_display_name",
    "resolve_join_student",
]
