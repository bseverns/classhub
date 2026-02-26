"""Teacher 2FA enrollment and verification endpoints."""

import re

from .shared import (
    TOTPDevice,
    _audit,
    _format_base32_for_display,
    _resolve_teacher_setup_user,
    _safe_internal_redirect,
    _teacher_2fa_device_name,
    _totp_qr_svg,
    _totp_secret_base32,
    _with_notice,
    apply_no_store,
    auth_login,
    mark_safe,
    render,
    urlencode,
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
    "teach_teacher_2fa_setup",
]
