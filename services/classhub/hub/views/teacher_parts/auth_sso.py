"""Teacher SSO start/callback endpoints.

T2 scope:
- Keep scaffold behavior for non-google providers.
- Implement Google teacher SSO callback exchange and account mapping.
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

from django.core import signing
from django.core.cache import cache

from ...services.teacher_sso_google import (
    exchange_google_code_for_identity as service_exchange_google_code_for_identity,
    load_provider_discovery as service_load_provider_discovery,
    staff_user_for_email as service_staff_user_for_email,
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

_PROVIDER_LABELS = {
    "google": "Google Workspace",
    "microsoft": "Microsoft",
    "oidc_custom": "Single Sign-On",
}
_STATE_SIGNING_SALT = "classhub.teacher-sso.state.v1"
_STATE_CACHE_PREFIX = "teacher_sso_state"
logger = logging.getLogger(__name__)


def _normalize_provider_key(raw: str) -> str:
    return (raw or "").strip().lower().replace("-", "_")


def _enabled_provider_keys() -> tuple[str, ...]:
    if not bool(getattr(settings, "CLASSHUB_TEACHER_SSO_ENABLED", False)):
        return ()
    values = getattr(settings, "CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS", ()) or ()
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        provider_key = _normalize_provider_key(str(value))
        if not provider_key or provider_key in seen:
            continue
        seen.add(provider_key)
        normalized.append(provider_key)
    return tuple(normalized)


def _provider_label(provider_key: str) -> str:
    if provider_key in _PROVIDER_LABELS:
        return _PROVIDER_LABELS[provider_key]
    return provider_key.replace("_", " ").title()


def _not_found_response() -> HttpResponse:
    response = HttpResponse(status=404)
    apply_no_store(response, private=True, pragma=True)
    return response


def teacher_sso_options_for_login(*, next_path: str) -> tuple[dict[str, str], ...]:
    """Return feature-flagged SSO provider options for /teach/login."""
    options: list[dict[str, str]] = []
    for provider_key in _enabled_provider_keys():
        start_path = f"/teach/sso/start/{provider_key}"
        if next_path and next_path != "/teach":
            start_path = f"{start_path}?{urlencode({'next': next_path})}"
        options.append(
            {
                "provider": provider_key,
                "label": _provider_label(provider_key),
                "start_path": start_path,
            }
        )
    return tuple(options)


def _provider_config(provider_key: str):
    providers = getattr(settings, "CLASSHUB_TEACHER_SSO_PROVIDERS", {}) or {}
    return providers.get(provider_key)


def _state_ttl_seconds() -> int:
    raw = getattr(settings, "CLASSHUB_TEACHER_SSO_STATE_MAX_AGE_SECONDS", 600)
    try:
        value = int(raw)
    except Exception:
        value = 600
    return max(value, 60)


def _state_cache_key(provider_key: str, state_id: str) -> str:
    return f"{_STATE_CACHE_PREFIX}:{provider_key}:{state_id}"


def _load_provider_discovery(provider_key: str) -> dict:
    return service_load_provider_discovery(provider_key=provider_key, provider=_provider_config(provider_key))


def _new_sso_state(*, provider_key: str, next_path: str) -> tuple[str, str]:
    state_id = secrets.token_urlsafe(18)
    nonce = secrets.token_urlsafe(18)
    payload = {
        "provider": provider_key,
        "next": next_path,
        "sid": state_id,
        "nonce": nonce,
    }
    state_token = signing.dumps(payload, salt=_STATE_SIGNING_SALT, compress=True)
    cache.set(_state_cache_key(provider_key, state_id), "1", timeout=_state_ttl_seconds())
    return state_token, nonce


def _consume_sso_state(*, provider_key: str, state_token: str) -> dict | None:
    try:
        payload = signing.loads(state_token, salt=_STATE_SIGNING_SALT, max_age=_state_ttl_seconds())
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None
    if _normalize_provider_key(str(payload.get("provider", ""))) != provider_key:
        return None
    state_id = str(payload.get("sid", "")).strip()
    if not state_id:
        return None
    cache_key = _state_cache_key(provider_key, state_id)
    if cache.get(cache_key) is None:
        return None
    cache.delete(cache_key)
    return payload


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
    login_path = "/teach/login"
    if next_path != "/teach":
        login_path = f"{login_path}?{urlencode({'next': next_path})}"
    target = _with_notice(login_path, notice=notice, error=error)
    response = _safe_internal_redirect(request, target, fallback="/teach/login")
    apply_no_store(response, private=True, pragma=True)
    return response


def _google_authorize_redirect(request, *, next_path: str):
    provider = _provider_config("google")
    if provider is None:
        return _login_redirect_response(
            request,
            next_path=next_path,
            error="Google Workspace SSO is configured incorrectly. Contact an administrator.",
        )
    try:
        discovery = _load_provider_discovery("google")
        state, nonce = _new_sso_state(provider_key="google", next_path=next_path)
        callback_url = request.build_absolute_uri("/teach/sso/callback/google")
        auth_params = {
            "client_id": str(provider.client_id),
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
        allowed_domains = tuple(getattr(provider, "allowed_domains", ()) or ())
        if len(allowed_domains) == 1:
            auth_params["hd"] = str(allowed_domains[0]).strip()
        authorize_url = f"{str(discovery['authorization_endpoint'])}?{urlencode(auth_params)}"
        response = HttpResponse(status=302)
        response["Location"] = authorize_url
        apply_no_store(response, private=True, pragma=True)
        return response
    except Exception:
        logger.exception("teacher_google_sso_start_error")
        return _login_redirect_response(
            request,
            next_path=next_path,
            error="Google Workspace SSO is unavailable right now. Please try again or use password login.",
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
    state_token = str(request.GET.get("state", "")).strip()
    code = str(request.GET.get("code", "")).strip()
    if not state_token or not code:
        return None, None, None, _login_redirect_response(
            request,
            next_path="/teach",
            error="Google Workspace login did not include required callback parameters.",
        )
    state_payload = _consume_sso_state(provider_key="google", state_token=state_token)
    if state_payload is None:
        return None, None, None, _login_redirect_response(
            request,
            next_path="/teach",
            error="Google Workspace login session expired. Please try again.",
        )
    next_path = _safe_teacher_return_path(str(state_payload.get("next", "/teach")), "/teach")
    expected_nonce = str(state_payload.get("nonce", "")).strip()
    if not expected_nonce:
        return None, None, None, _login_redirect_response(
            request,
            next_path=next_path,
            error="Google Workspace login session was invalid. Please try again.",
        )
    return code, next_path, expected_nonce, None


def _google_complete_teacher_login(request, *, staff_user, next_path: str):
    auth_login(request, staff_user)
    if bool(getattr(settings, "TEACHER_2FA_REQUIRED", True)):
        is_verified_attr = getattr(staff_user, "is_verified", None)
        is_verified = bool(is_verified_attr() if callable(is_verified_attr) else is_verified_attr)
        if not is_verified:
            response = _safe_internal_redirect(
                request,
                _with_notice("/teach/2fa/setup", notice="Finish 2FA setup to continue."),
                fallback="/teach/2fa/setup",
            )
            apply_no_store(response, private=True, pragma=True)
            return response
    response = _safe_internal_redirect(request, next_path, fallback="/teach")
    apply_no_store(response, private=True, pragma=True)
    return response


def _google_sso_callback(request):
    code, next_path, expected_nonce, error_response = _google_callback_inputs(request)
    if error_response is not None:
        return error_response
    provider = _provider_config("google")
    if provider is None:
        return _login_redirect_response(
            request,
            next_path=next_path,
            error="Google Workspace SSO is configured incorrectly. Contact an administrator.",
        )
    try:
        callback_url = request.build_absolute_uri("/teach/sso/callback/google")
        identity = _google_exchange_code_for_identity(
            provider=provider,
            code=code,
            redirect_uri=callback_url,
            expected_nonce=expected_nonce,
        )
        staff_user = _staff_user_for_email(identity.email)
        if staff_user is None:
            return _login_redirect_response(
                request,
                next_path=next_path,
                error="No teacher account is linked to this organization email.",
            )
        return _google_complete_teacher_login(request, staff_user=staff_user, next_path=next_path)
    except Exception:
        logger.exception("teacher_google_sso_callback_error")
        return _login_redirect_response(
            request,
            next_path=next_path,
            error="Google Workspace login failed. Please try again or use password login.",
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
