"""Teacher account onboarding endpoints."""

from .shared import (
    _audit,
    _build_teacher_setup_token,
    _safe_internal_redirect,
    _send_teacher_onboarding_email,
    _with_notice,
    get_user_model,
    require_POST,
    staff_member_required,
    urlencode,
    urlparse,
    validate_email,
)


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


__all__ = [
    "teach_create_teacher",
]
