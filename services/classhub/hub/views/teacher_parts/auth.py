"""Compatibility re-exports for teacher auth views."""

from .auth_login import teach_login, teacher_logout
from .auth_teacher_accounts import teach_create_teacher
from .auth_teacher_2fa import teach_teacher_2fa_setup

__all__ = [
    "teach_login",
    "teacher_logout",
    "teach_create_teacher",
    "teach_teacher_2fa_setup",
]
