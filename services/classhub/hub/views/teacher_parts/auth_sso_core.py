"""Compatibility facade for teacher SSO core helpers."""

from __future__ import annotations

from .auth_sso_core_callback import (
    google_callback_inputs,
    google_complete_teacher_login,
)
from .auth_sso_core_providers import (
    enabled_provider_keys,
    login_redirect_response,
    normalize_provider_key,
    not_found_response,
    provider_config,
    provider_label,
    state_ttl_seconds,
    teacher_sso_options_for_login,
)
from .auth_sso_core_state import (
    consume_sso_state,
    new_sso_state,
)

__all__ = [
    "consume_sso_state",
    "enabled_provider_keys",
    "google_callback_inputs",
    "google_complete_teacher_login",
    "login_redirect_response",
    "new_sso_state",
    "normalize_provider_key",
    "not_found_response",
    "provider_config",
    "provider_label",
    "state_ttl_seconds",
    "teacher_sso_options_for_login",
]
