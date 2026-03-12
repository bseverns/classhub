"""Google-specific teacher SSO flow orchestration helpers."""

from __future__ import annotations

from urllib.parse import urlencode


def google_authorize_redirect(
    request,
    *,
    next_path: str,
    provider,
    load_provider_discovery_fn,
    new_sso_state_fn,
    login_redirect_response_fn,
    http_response_cls,
    apply_no_store_fn,
    logger,
):
    if provider is None:
        return login_redirect_response_fn(
            request,
            next_path=next_path,
            error="Google Workspace SSO is configured incorrectly. Contact an administrator.",
        )
    try:
        discovery = load_provider_discovery_fn("google")
        state, nonce = new_sso_state_fn(provider_key="google", next_path=next_path)
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
        response = http_response_cls(status=302)
        response["Location"] = authorize_url
        apply_no_store_fn(response, private=True, pragma=True)
        return response
    except Exception:
        logger.exception("teacher_google_sso_start_error")
        return login_redirect_response_fn(
            request,
            next_path=next_path,
            error="Google Workspace SSO is unavailable right now. Please try again or use password login.",
        )


def google_sso_callback(
    request,
    *,
    provider,
    google_callback_inputs_fn,
    google_exchange_code_for_identity_fn,
    staff_user_for_email_fn,
    google_complete_teacher_login_fn,
    login_redirect_response_fn,
    logger,
):
    code, next_path, expected_nonce, error_response = google_callback_inputs_fn(request)
    if error_response is not None:
        return error_response
    if provider is None:
        return login_redirect_response_fn(
            request,
            next_path=next_path,
            error="Google Workspace SSO is configured incorrectly. Contact an administrator.",
        )
    try:
        callback_url = request.build_absolute_uri("/teach/sso/callback/google")
        identity = google_exchange_code_for_identity_fn(
            provider=provider,
            code=code,
            redirect_uri=callback_url,
            expected_nonce=expected_nonce,
        )
        staff_user = staff_user_for_email_fn(identity.email)
        if staff_user is None:
            return login_redirect_response_fn(
                request,
                next_path=next_path,
                error="No teacher account is linked to this organization email.",
            )
        return google_complete_teacher_login_fn(request, staff_user=staff_user, next_path=next_path)
    except Exception:
        logger.exception("teacher_google_sso_callback_error")
        return login_redirect_response_fn(
            request,
            next_path=next_path,
            error="Google Workspace login failed. Please try again or use password login.",
        )


__all__ = [
    "google_authorize_redirect",
    "google_sso_callback",
]
