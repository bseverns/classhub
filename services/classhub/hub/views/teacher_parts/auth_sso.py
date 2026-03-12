"""Teacher SSO start/callback endpoints.

T2 scope:
- Keep scaffold behavior for non-google providers.
- Implement Google teacher SSO callback exchange and account mapping.
"""

from __future__ import annotations

import logging

from django.core import signing
from django.core.cache import cache

from ...services.teacher_sso_google import (
    exchange_google_code_for_identity as service_exchange_google_code_for_identity,
    load_provider_discovery as service_load_provider_discovery,
    staff_user_for_email as service_staff_user_for_email,
)
from .auth_sso_core import (
    consume_sso_state as _consume_sso_state_impl,
    enabled_provider_keys as _enabled_provider_keys_impl,
    google_callback_inputs as _google_callback_inputs_impl,
    google_complete_teacher_login as _google_complete_teacher_login_impl,
    login_redirect_response as _login_redirect_response_impl,
    new_sso_state as _new_sso_state_impl,
    normalize_provider_key as _normalize_provider_key,
    not_found_response as _not_found_response_impl,
    provider_config as _provider_config_impl,
    provider_label as _provider_label,
    state_ttl_seconds as _state_ttl_seconds_impl,
    teacher_sso_options_for_login as _teacher_sso_options_for_login_impl,
)
from .auth_sso_google_flow import (
    google_authorize_redirect as _google_authorize_redirect_impl,
    google_sso_callback as _google_sso_callback_impl,
)
from .shared import (
    HttpResponse,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _with_notice,
    apply_no_store,
    auth_login,
    settings,
)

_STATE_SIGNING_SALT = "classhub.teacher-sso.state.v1"
_STATE_CACHE_PREFIX = "teacher_sso_state"
logger = logging.getLogger(__name__)


def _enabled_provider_keys() -> tuple[str, ...]:
    return _enabled_provider_keys_impl(settings=settings)


def _not_found_response() -> HttpResponse:
    return _not_found_response_impl(http_response_cls=HttpResponse, apply_no_store_fn=apply_no_store)


def teacher_sso_options_for_login(*, next_path: str) -> tuple[dict[str, str], ...]:
    """Return feature-flagged SSO provider options for /teach/login."""
    return _teacher_sso_options_for_login_impl(
        next_path=next_path,
        enabled_provider_keys_fn=_enabled_provider_keys,
        provider_label_fn=_provider_label,
    )


def _provider_config(provider_key: str):
    return _provider_config_impl(settings=settings, provider_key=provider_key)


def _state_ttl_seconds() -> int:
    return _state_ttl_seconds_impl(settings=settings)


def _load_provider_discovery(provider_key: str) -> dict:
    return service_load_provider_discovery(provider_key=provider_key, provider=_provider_config(provider_key))


def _new_sso_state(*, provider_key: str, next_path: str) -> tuple[str, str]:
    return _new_sso_state_impl(
        signing=signing,
        cache=cache,
        provider_key=provider_key,
        next_path=next_path,
        state_signing_salt=_STATE_SIGNING_SALT,
        state_cache_prefix=_STATE_CACHE_PREFIX,
        state_ttl_seconds=_state_ttl_seconds(),
    )


def _consume_sso_state(*, provider_key: str, state_token: str):
    return _consume_sso_state_impl(
        signing=signing,
        cache=cache,
        provider_key=provider_key,
        state_token=state_token,
        state_signing_salt=_STATE_SIGNING_SALT,
        state_cache_prefix=_STATE_CACHE_PREFIX,
        state_ttl_seconds=_state_ttl_seconds(),
    )


def _google_exchange_code_for_identity(
    *,
    provider,
    code: str,
    redirect_uri: str,
    expected_nonce: str,
):
    return service_exchange_google_code_for_identity(
        provider=provider,
        code=code,
        redirect_uri=redirect_uri,
        expected_nonce=expected_nonce,
    )


def _staff_user_for_email(email: str):
    return service_staff_user_for_email(email)


def _login_redirect_response(request, *, next_path: str, notice: str | None = None, error: str | None = None):
    return _login_redirect_response_impl(
        request,
        next_path=next_path,
        notice=notice,
        error=error,
        safe_internal_redirect_fn=_safe_internal_redirect,
        with_notice_fn=_with_notice,
        apply_no_store_fn=apply_no_store,
    )


def _google_authorize_redirect(request, *, next_path: str):
    return _google_authorize_redirect_impl(
        request,
        next_path=next_path,
        provider=_provider_config("google"),
        load_provider_discovery_fn=_load_provider_discovery,
        new_sso_state_fn=_new_sso_state,
        login_redirect_response_fn=_login_redirect_response,
        http_response_cls=HttpResponse,
        apply_no_store_fn=apply_no_store,
        logger=logger,
    )


def teach_sso_start(request, provider: str):
    provider_key = _normalize_provider_key(provider)
    next_raw = (request.GET.get("next") or "/teach").strip()
    next_path = _safe_teacher_return_path(next_raw, "/teach")
    if provider_key not in _enabled_provider_keys():
        return _not_found_response()
    if provider_key == "google":
        return _google_authorize_redirect(request, next_path=next_path)
    return _login_redirect_response(
        request,
        next_path=next_path,
        error=f"{_provider_label(provider_key)} SSO is not active yet in this build.",
    )


def _google_callback_inputs(request):
    return _google_callback_inputs_impl(
        request,
        consume_sso_state_fn=_consume_sso_state,
        login_redirect_response_fn=_login_redirect_response,
        safe_teacher_return_path_fn=_safe_teacher_return_path,
    )


def _google_complete_teacher_login(request, *, staff_user, next_path: str):
    return _google_complete_teacher_login_impl(
        request,
        staff_user=staff_user,
        next_path=next_path,
        settings=settings,
        auth_login_fn=auth_login,
        safe_internal_redirect_fn=_safe_internal_redirect,
        with_notice_fn=_with_notice,
        apply_no_store_fn=apply_no_store,
    )


def _google_sso_callback(request):
    return _google_sso_callback_impl(
        request,
        provider=_provider_config("google"),
        google_callback_inputs_fn=_google_callback_inputs,
        google_exchange_code_for_identity_fn=_google_exchange_code_for_identity,
        staff_user_for_email_fn=_staff_user_for_email,
        google_complete_teacher_login_fn=_google_complete_teacher_login,
        login_redirect_response_fn=_login_redirect_response,
        logger=logger,
    )


def teach_sso_callback(request, provider: str):
    provider_key = _normalize_provider_key(provider)
    if provider_key not in _enabled_provider_keys():
        return _not_found_response()
    if provider_key == "google":
        if str(request.GET.get("error", "")).strip():
            error_label = str(request.GET.get("error_description", "")).strip() or str(request.GET.get("error", "")).strip()
            return _login_redirect_response(
                request,
                next_path="/teach",
                error=f"Google Workspace login was cancelled or denied: {error_label}.",
            )
        return _google_sso_callback(request)
    return _login_redirect_response(
        request,
        next_path="/teach",
        error=f"{_provider_label(provider_key)} SSO callback is not active yet in this build.",
    )


__all__ = [
    "teacher_sso_options_for_login",
    "teach_sso_start",
    "teach_sso_callback",
]
