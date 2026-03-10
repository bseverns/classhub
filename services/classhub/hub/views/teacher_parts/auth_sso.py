"""Teacher SSO start/callback endpoints (T1 scaffold)."""

from urllib.parse import urlencode

from .shared import (
    HttpResponse,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _with_notice,
    apply_no_store,
    settings,
)

_PROVIDER_LABELS = {
    "google": "Google Workspace",
    "microsoft": "Microsoft",
    "oidc_custom": "Single Sign-On",
}


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


def teach_sso_start(request, provider: str):
    provider_key = _normalize_provider_key(provider)
    next_raw = (request.GET.get("next") or "/teach").strip()
    next_path = _safe_teacher_return_path(next_raw, "/teach")
    if provider_key not in _enabled_provider_keys():
        return _not_found_response()

    login_path = "/teach/login"
    if next_path != "/teach":
        login_path = f"{login_path}?{urlencode({'next': next_path})}"
    response = _safe_internal_redirect(
        request,
        _with_notice(
            login_path,
            error=f"{_provider_label(provider_key)} SSO is not active yet in this build.",
        ),
        fallback="/teach/login",
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def teach_sso_callback(request, provider: str):
    provider_key = _normalize_provider_key(provider)
    next_raw = (request.GET.get("next") or "/teach").strip()
    next_path = _safe_teacher_return_path(next_raw, "/teach")
    if provider_key not in _enabled_provider_keys():
        return _not_found_response()

    login_path = "/teach/login"
    if next_path != "/teach":
        login_path = f"{login_path}?{urlencode({'next': next_path})}"
    response = _safe_internal_redirect(
        request,
        _with_notice(
            login_path,
            error=f"{_provider_label(provider_key)} SSO callback is not active yet in this build.",
        ),
        fallback="/teach/login",
    )
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "teacher_sso_options_for_login",
    "teach_sso_start",
    "teach_sso_callback",
]

