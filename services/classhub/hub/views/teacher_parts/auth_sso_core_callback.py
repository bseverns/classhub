"""Callback/login completion helpers for teacher SSO flows."""

from __future__ import annotations


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
    "google_callback_inputs",
    "google_complete_teacher_login",
]
