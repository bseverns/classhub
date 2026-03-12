"""Provider/config/redirect helpers for teacher SSO core flows."""

from __future__ import annotations

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


__all__ = [
    "enabled_provider_keys",
    "login_redirect_response",
    "normalize_provider_key",
    "not_found_response",
    "provider_config",
    "provider_label",
    "state_ttl_seconds",
    "teacher_sso_options_for_login",
]
