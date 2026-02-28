"""Join-flow service facade for student session entry."""

from common.pseudonyms import generate_pseudonym

from .student_join import (
    JoinResolution,
    JoinValidationError,
    apply_device_hint_cookie,
    clear_device_hint_cookie,
    normalize_display_name,
    resolve_join_student,
    validate_display_name_safety,
)

__all__ = [
    "JoinResolution",
    "JoinValidationError",
    "apply_device_hint_cookie",
    "clear_device_hint_cookie",
    "generate_pseudonym",
    "normalize_display_name",
    "resolve_join_student",
    "validate_display_name_safety",
]

