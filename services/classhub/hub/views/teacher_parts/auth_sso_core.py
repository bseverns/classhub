"""Shared helper primitives for teacher SSO start/callback flows."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode


_PROVIDER_LABELS = {
    "google": "Google Workspace",
    "microsoft": "Microsoft",
    "oidc_custom": "Single Sign-On",
}


def normalize_provider_key(raw: str) -> str:
    return (raw or "").strip().lower().replace("-", "_")


def enabled_provider_keys(*, settings) -> tuple[str, ...]:
    if not bool(getattr(settings, "CLASSHUB_TEACHER_SSO_ENABLED", False)):
        return ()
    values = getattr(settings, "CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS", ()) or ()
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        provider_key = normalize_provider_key(str(value))
        if not provider_key or provider_key in seen:
            continue
        seen.add(provider_key)
        normalized.append(provider_key)
    return tuple(normalized)


def provider_label(provider_key: str) -> str:
    if provider_key in _PROVIDER_LABELS:
        return _PROVIDER_LABELS[provider_key]
    return provider_key.replace("_", " ").title()


def teacher_sso_options_for_login(*, next_path: str, enabled_provider_keys_fn, provider_label_fn) -> tuple[dict[str, str], ...]:
    options: list[dict[str, str]] = []
    for provider_key in enabled_provider_keys_fn():
        start_path = f"/teach/sso/start/{provider_key}"
        if next_path and next_path != "/teach":
            start_path = f"{start_path}?{urlencode({'next': next_path})}"
        options.append(
            {
                "provider": provider_key,
                "label": provider_label_fn(provider_key),
                "start_path": start_path,
            }
        )
    return tuple(options)


def not_found_response(*, http_response_cls, apply_no_store_fn):
    response = http_response_cls(status=404)
    apply_no_store_fn(response, private=True, pragma=True)
    return response


def provider_config(*, settings, provider_key: str):
    providers = getattr(settings, "CLASSHUB_TEACHER_SSO_PROVIDERS", {}) or {}
    return providers.get(provider_key)


def state_ttl_seconds(*, settings) -> int:
    raw = getattr(settings, "CLASSHUB_TEACHER_SSO_STATE_MAX_AGE_SECONDS", 600)
    try:
        value = int(raw)
    except Exception:
        value = 600
    return max(value, 60)


def state_cache_key(*, state_cache_prefix: str, provider_key: str, state_id: str) -> str:
    return f"{state_cache_prefix}:{provider_key}:{state_id}"


def new_sso_state(
    *,
    signing,
    cache,
    provider_key: str,
    next_path: str,
    state_signing_salt: str,
    state_cache_prefix: str,
    state_ttl_seconds: int,
) -> tuple[str, str]:
    state_id = secrets.token_urlsafe(18)
    nonce = secrets.token_urlsafe(18)
    payload = {
        "provider": provider_key,
        "next": next_path,
        "sid": state_id,
        "nonce": nonce,
    }
    state_token = signing.dumps(payload, salt=state_signing_salt, compress=True)
    cache.set(
        state_cache_key(state_cache_prefix=state_cache_prefix, provider_key=provider_key, state_id=state_id),
        "1",
        timeout=state_ttl_seconds,
    )
    return state_token, nonce


def consume_sso_state(
    *,
    signing,
    cache,
    provider_key: str,
    state_token: str,
    state_signing_salt: str,
    state_cache_prefix: str,
    state_ttl_seconds: int,
):
    try:
        payload = signing.loads(state_token, salt=state_signing_salt, max_age=state_ttl_seconds)
    except signing.BadSignature:
        return None
    if not isinstance(payload, dict):
        return None
    if normalize_provider_key(str(payload.get("provider", ""))) != provider_key:
        return None
    state_id = str(payload.get("sid", "")).strip()
    if not state_id:
        return None
    cache_key = state_cache_key(state_cache_prefix=state_cache_prefix, provider_key=provider_key, state_id=state_id)
    if cache.get(cache_key) is None:
        return None
    cache.delete(cache_key)
    return payload


def login_redirect_response(
    request,
    *,
    next_path: str,
    notice: str | None,
    error: str | None,
    safe_internal_redirect_fn,
    with_notice_fn,
    apply_no_store_fn,
):
    login_path = "/teach/login"
    if next_path != "/teach":
        login_path = f"{login_path}?{urlencode({'next': next_path})}"
    target = with_notice_fn(login_path, notice=notice, error=error)
    response = safe_internal_redirect_fn(request, target, fallback="/teach/login")
    apply_no_store_fn(response, private=True, pragma=True)
    return response


def google_callback_inputs(
    request,
    *,
    consume_sso_state_fn,
    login_redirect_response_fn,
    safe_teacher_return_path_fn,
):
    state_token = str(request.GET.get("state", "")).strip()
    code = str(request.GET.get("code", "")).strip()
    if not state_token or not code:
        return None, None, None, login_redirect_response_fn(
            request,
            next_path="/teach",
            error="Google Workspace login did not include required callback parameters.",
        )
    state_payload = consume_sso_state_fn(provider_key="google", state_token=state_token)
    if state_payload is None:
        return None, None, None, login_redirect_response_fn(
            request,
            next_path="/teach",
            error="Google Workspace login session expired. Please try again.",
        )
    next_path = safe_teacher_return_path_fn(str(state_payload.get("next", "/teach")), "/teach")
    expected_nonce = str(state_payload.get("nonce", "")).strip()
    if not expected_nonce:
        return None, None, None, login_redirect_response_fn(
            request,
            next_path=next_path,
            error="Google Workspace login session was invalid. Please try again.",
        )
    return code, next_path, expected_nonce, None


def google_complete_teacher_login(
    request,
    *,
    staff_user,
    next_path: str,
    settings,
    auth_login_fn,
    safe_internal_redirect_fn,
    with_notice_fn,
    apply_no_store_fn,
):
    auth_login_fn(request, staff_user)
    if bool(getattr(settings, "TEACHER_2FA_REQUIRED", True)):
        is_verified_attr = getattr(staff_user, "is_verified", None)
        is_verified = bool(is_verified_attr() if callable(is_verified_attr) else is_verified_attr)
        if not is_verified:
            response = safe_internal_redirect_fn(
                request,
                with_notice_fn("/teach/2fa/setup", notice="Finish 2FA setup to continue."),
                fallback="/teach/2fa/setup",
            )
            apply_no_store_fn(response, private=True, pragma=True)
            return response
    response = safe_internal_redirect_fn(request, next_path, fallback="/teach")
    apply_no_store_fn(response, private=True, pragma=True)
    return response


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
