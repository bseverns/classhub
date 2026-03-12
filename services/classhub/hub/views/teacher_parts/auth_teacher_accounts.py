"""Compatibility facade for teacher account onboarding/admin endpoints."""

from .auth_teacher_accounts_controls import (
    teach_reset_teacher_account_password,
    teach_set_teacher_account_active,
    teach_set_teacher_account_superuser,
)
from .auth_teacher_accounts_onboarding import (
    teach_create_teacher,
    teach_resend_teacher_invite,
)

__all__ = [
    "teach_create_teacher",
    "teach_reset_teacher_account_password",
    "teach_resend_teacher_invite",
    "teach_set_teacher_account_active",
    "teach_set_teacher_account_superuser",
]
