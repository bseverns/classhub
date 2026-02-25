"""Teacher auth and onboarding endpoints."""

import re

from .shared import *  # noqa: F401,F403,F405


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


@staff_member_required
@require_POST
def teach_create_teacher(request):
    if not request.user.is_superuser:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Only superusers can create teacher accounts."),
            fallback="/teach",
        )

    username = (request.POST.get("username") or "").strip()
    email = (request.POST.get("email") or "").strip()
    password = (request.POST.get("password") or "").strip()
    first_name = (request.POST.get("first_name") or "").strip()[:150]
    last_name = (request.POST.get("last_name") or "").strip()[:150]
    include_password_in_email = (request.POST.get("email_include_password") or "").strip() == "1"

    form_values = {
        "teacher_username": username,
        "teacher_email": email,
        "teacher_first_name": first_name,
        "teacher_last_name": last_name,
    }

    if not username:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Teacher username is required.", extra=form_values),
            fallback="/teach",
        )
    if not email:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Teacher email is required.", extra=form_values),
            fallback="/teach",
        )
    if not password:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Starting password is required.", extra=form_values),
            fallback="/teach",
        )
    try:
        validate_email(email)
    except Exception:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Enter a valid teacher email address.", extra=form_values),
            fallback="/teach",
        )

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="That username already exists.", extra=form_values),
            fallback="/teach",
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    user.is_staff = True
    user.is_superuser = False
    user.is_active = True
    user.save(update_fields=["is_staff", "is_superuser", "is_active"])

    token = _build_teacher_setup_token(user)
    setup_url = request.build_absolute_uri(f"/teach/2fa/setup?{urlencode({'token': token})}")
    email_error = ""
    try:
        _send_teacher_onboarding_email(
            request,
            user=user,
            setup_url=setup_url,
            starting_password=password if include_password_in_email else "",
        )
    except Exception as exc:
        email_error = str(exc)

    _audit(
        request,
        action="teacher_account.create",
        target_type="User",
        target_id=str(user.id),
        summary=f"Created teacher account {user.username}",
        metadata={
            "username": user.username,
            "email": user.email,
            "email_sent": not bool(email_error),
            "invite_includes_password": include_password_in_email,
            "setup_url_host": urlparse(setup_url).netloc,
        },
    )

    if email_error:
        notice = f"Teacher account '{user.username}' created."
        error = f"Invite email failed: {email_error}"
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", notice=notice, error=error),
            fallback="/teach",
        )

    notice = f"Teacher account '{user.username}' created and invite email sent."
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice),
        fallback="/teach",
    )


def _resolve_teacher_setup_context(request):
    requested_next = (request.GET.get("next") or request.POST.get("next") or "").strip()
    safe_next = requested_next if requested_next.startswith("/teach") and not requested_next.startswith("//") else ""
    token = (request.GET.get("token") or request.POST.get("token") or "").strip()
    if token:
        user, err = _resolve_teacher_setup_user(token)
        if err:
            return None, token, err, safe_next
        if not request.user.is_authenticated or request.user.pk != user.pk:
            user.backend = "django.contrib.auth.backends.ModelBackend"
            auth_login(request, user)
        return user, token, "", safe_next

    current = getattr(request, "user", None)
    if current and current.is_authenticated and current.is_staff and current.is_active:
        return current, "", "", safe_next

    return None, "", "Sign in first, or open a valid setup link from your invite email.", safe_next


def teach_teacher_2fa_setup(request):
    requested_next = (request.GET.get("next") or request.POST.get("next") or "").strip()
    safe_next = requested_next if requested_next.startswith("/teach") and not requested_next.startswith("//") else ""
    invite_token = (request.GET.get("token") or "").strip()
    if invite_token:
        invite_user, invite_error = _resolve_teacher_setup_user(invite_token, consume=True)
        if invite_error:
            response = render(
                request,
                "teach_setup_otp.html",
                {
                    "error": invite_error,
                    "token": invite_token,
                    "otp_ready": False,
                    "already_configured": False,
                    "setup_user": None,
                    "next_path": safe_next,
                },
                status=400,
            )
            apply_no_store(response, private=True, pragma=True)
            return response
        if not request.user.is_authenticated or request.user.pk != invite_user.pk:
            invite_user.backend = "django.contrib.auth.backends.ModelBackend"
            auth_login(request, invite_user)
        redirect_to = "/teach/2fa/setup"
        if safe_next:
            redirect_to = f"{redirect_to}?{urlencode({'next': safe_next})}"
        response = _safe_internal_redirect(request, redirect_to, fallback="/teach/2fa/setup")
        apply_no_store(response, private=True, pragma=True)
        return response

    user, token, setup_error, safe_next = _resolve_teacher_setup_context(request)
    if user is None:
        login_next = "/teach/2fa/setup"
        if safe_next:
            login_next = f"{login_next}?{urlencode({'next': safe_next})}"
        login_url = f"/teach/login?{urlencode({'next': login_next})}"
        if token:
            response = render(
                request,
                "teach_setup_otp.html",
                {
                    "error": setup_error,
                    "token": token,
                    "otp_ready": False,
                    "already_configured": False,
                    "setup_user": None,
                    "next_path": safe_next,
                },
                status=400,
            )
            apply_no_store(response, private=True, pragma=True)
            return response
        response = _safe_internal_redirect(request, login_url, fallback="/teach/login")
        apply_no_store(response, private=True, pragma=True)
        return response

    device_name = _teacher_2fa_device_name()
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        device = TOTPDevice.objects.filter(user=user, name=device_name).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name=device_name, confirmed=False)

    notice = ""
    error = setup_error
    if request.method == "POST":
        otp_token = re.sub(r"\s+", "", (request.POST.get("otp_token") or "").strip())
        if not otp_token.isdigit() or len(otp_token) != int(device.digits or 6):
            error = f"Enter the {int(device.digits or 6)}-digit code from your authenticator app."
        elif not device.verify_token(otp_token):
            error = "Invalid code. Check your authenticator app and try again."
        else:
            from django_otp import login as otp_login
            otp_login(request, device)
            
            was_confirmed = device.confirmed
            if not was_confirmed:
                device.confirmed = True
                device.save(update_fields=["confirmed"])
                _audit(
                    request,
                    action="teacher_2fa.enroll",
                    target_type="User",
                    target_id=str(user.id),
                    summary=f"Completed teacher 2FA enrollment for {user.username}",
                    metadata={"device_name": device.name},
                )
            else:
                _audit(
                    request,
                    action="teacher_2fa.verify",
                    target_type="User",
                    target_id=str(user.id),
                    summary=f"Verified 2FA for {user.username}",
                    metadata={"device_name": device.name},
                )
            redirect_to = safe_next if safe_next.startswith("/teach") else "/teach"
            notice_text = "2FA verified." if was_confirmed else "2FA setup complete."
            return _safe_internal_redirect(
                request,
                _with_notice(redirect_to, notice=notice_text),
                fallback="/teach",
            )

    already_configured = bool(device.confirmed)
    qr_svg = ""
    manual_secret = ""
    config_url = ""
    if not already_configured:
        config_url = getattr(device, "config_url", "")
        if config_url:
            qr_svg = _totp_qr_svg(config_url)
        manual_secret = _format_base32_for_display(_totp_secret_base32(device))

    response = render(
        request,
        "teach_setup_otp.html",
        {
            "setup_user": user,
            "token": token,
            "notice": notice,
            "error": error,
            "otp_ready": bool(config_url),
            "already_configured": already_configured,
            "config_url": config_url,
            "manual_secret": manual_secret,
            "qr_svg": mark_safe(qr_svg) if qr_svg else "",
            "digits": int(device.digits or 6),
            "next_path": safe_next,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response

__all__ = [
    "teach_login",
    "teacher_logout",
    "teach_create_teacher",
    "teach_teacher_2fa_setup",
]
