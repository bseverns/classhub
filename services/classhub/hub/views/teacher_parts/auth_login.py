"""Teacher login/logout endpoints."""

from .shared import (
    AuthenticationForm,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _with_notice,
    apply_no_store,
    auth_login,
    auth_logout,
    redirect,
    render,
    settings,
)


def teach_login(request):
    next_raw = (request.GET.get("next") or request.POST.get("next") or "/teach").strip()
    next_path = _safe_teacher_return_path(next_raw, "/teach")

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if user.is_staff and user.is_active:
            if getattr(settings, "TEACHER_2FA_REQUIRED", True):
                is_verified_attr = getattr(user, "is_verified", None)
                is_verified = bool(is_verified_attr() if callable(is_verified_attr) else is_verified_attr)
                if not is_verified:
                    return _safe_internal_redirect(request, "/teach/2fa/setup", fallback="/teach/2fa/setup")
            return _safe_internal_redirect(request, next_path, fallback="/teach")
        auth_logout(request)
        request.session.flush()

    error = ""
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            authenticated_user = form.get_user()
            if not authenticated_user.is_active or not authenticated_user.is_staff:
                auth_logout(request)
                request.session.flush()
                error = "This account does not have teacher access."
            else:
                auth_login(request, authenticated_user)
                if getattr(settings, "TEACHER_2FA_REQUIRED", True):
                    is_verified_attr = getattr(authenticated_user, "is_verified", None)
                    is_verified = bool(is_verified_attr() if callable(is_verified_attr) else is_verified_attr)
                    if not is_verified:
                        return _safe_internal_redirect(
                            request,
                            _with_notice("/teach/2fa/setup", notice="Finish 2FA setup to continue."),
                            fallback="/teach/2fa/setup",
                        )
                return _safe_internal_redirect(request, next_path, fallback="/teach")

    response = render(
        request,
        "teach_login.html",
        {
            "form": form,
            "next_path": next_path,
            "error": error,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def teacher_logout(request):
    # Teacher/admin auth uses Django auth session, so call auth_logout first.
    auth_logout(request)
    # Also flush generic session keys to keep student and staff states cleanly separate.
    request.session.flush()
    return redirect("/teach/login")


__all__ = [
    "teach_login",
    "teacher_logout",
]
