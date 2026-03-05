"""Teacher account onboarding endpoints."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .shared import (
    _audit,
    _build_teacher_setup_token,
    _parse_positive_int,
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

_SUPERUSER_ONLY_ERROR = "Only superusers can manage teacher accounts."


def _teacher_account_redirect(request, *, notice: str = "", error: str = "", extra: dict | None = None):
    payload = {"teacher_invite": "1"}
    if extra:
        payload.update(extra)
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra=payload),
        fallback="/teach",
    )


def _require_superuser(request):
    if request.user.is_superuser:
        return None
    return _teacher_account_redirect(request, error=_SUPERUSER_ONLY_ERROR)


def _resolve_staff_target_user(request):
    user_id = _parse_positive_int(
        (request.POST.get("teacher_account_user_id") or "").strip(),
        min_value=1,
        max_value=2_147_483_647,
    )
    if user_id is None:
        return None, _teacher_account_redirect(request, error="Select a teacher account.")
    User = get_user_model()
    target_user = User.objects.filter(id=user_id, is_staff=True).first()
    if target_user is None:
        return None, _teacher_account_redirect(request, error="Teacher account not found.")
    return target_user, None


def _would_remove_last_active_superuser(*, target_user, next_is_active: bool, next_is_superuser: bool) -> bool:
    currently_active_superuser = bool(target_user.is_active and target_user.is_superuser)
    if not currently_active_superuser or (next_is_active and next_is_superuser):
        return False
    User = get_user_model()
    return not User.objects.filter(is_staff=True, is_superuser=True, is_active=True).exclude(id=target_user.id).exists()


def _build_setup_url(request, *, user):
    token = _build_teacher_setup_token(user)
    return request.build_absolute_uri(f"/teach/2fa/setup?{urlencode({'token': token})}")


@staff_member_required
@require_POST
def teach_create_teacher(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied

    username = (request.POST.get("username") or "").strip()
    email = (request.POST.get("email") or "").strip()
    password = (request.POST.get("password") or "").strip()
    first_name = (request.POST.get("first_name") or "").strip()[:150]
    last_name = (request.POST.get("last_name") or "").strip()[:150]
    include_password_in_email = (request.POST.get("email_include_password") or "").strip() == "1"

    form_values = {
        "teacher_invite": "1",
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

    setup_url = _build_setup_url(request, user=user)
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
        return _teacher_account_redirect(request, notice=notice, error=error)

    notice = f"Teacher account '{user.username}' created and invite email sent."
    return _teacher_account_redirect(request, notice=notice)


@staff_member_required
@require_POST
def teach_set_teacher_account_active(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = _resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    is_active = (request.POST.get("teacher_account_active") or "").strip() == "1"
    if target_user.id == request.user.id and not is_active:
        return _teacher_account_redirect(request, error="You cannot disable your current superuser account.")
    if _would_remove_last_active_superuser(
        target_user=target_user,
        next_is_active=is_active,
        next_is_superuser=bool(target_user.is_superuser),
    ):
        return _teacher_account_redirect(request, error="At least one active superuser account is required.")

    if target_user.is_active != is_active:
        target_user.is_active = is_active
        target_user.save(update_fields=["is_active"])
    status_label = "active" if target_user.is_active else "inactive"
    _audit(
        request,
        action="teacher_account.set_active",
        target_type="User",
        target_id=str(target_user.id),
        summary=f"Set teacher account active={target_user.is_active} for {target_user.username}",
        metadata={"user_id": target_user.id, "username": target_user.username, "is_active": target_user.is_active},
    )
    return _teacher_account_redirect(request, notice=f"Set teacher account '{target_user.username}' {status_label}.")


@staff_member_required
@require_POST
def teach_set_teacher_account_superuser(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = _resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    is_superuser = (request.POST.get("teacher_account_superuser") or "").strip() == "1"
    if target_user.id == request.user.id and not is_superuser:
        return _teacher_account_redirect(request, error="You cannot remove superuser from your current account.")
    if _would_remove_last_active_superuser(
        target_user=target_user,
        next_is_active=bool(target_user.is_active),
        next_is_superuser=is_superuser,
    ):
        return _teacher_account_redirect(request, error="At least one active superuser account is required.")

    changed_fields: list[str] = []
    if target_user.is_superuser != is_superuser:
        target_user.is_superuser = is_superuser
        changed_fields.append("is_superuser")
    if is_superuser and not target_user.is_staff:
        target_user.is_staff = True
        changed_fields.append("is_staff")
    if changed_fields:
        target_user.save(update_fields=changed_fields)
    role_label = "superuser" if target_user.is_superuser else "staff"
    _audit(
        request,
        action="teacher_account.set_superuser",
        target_type="User",
        target_id=str(target_user.id),
        summary=f"Set teacher account superuser={target_user.is_superuser} for {target_user.username}",
        metadata={
            "user_id": target_user.id,
            "username": target_user.username,
            "is_superuser": target_user.is_superuser,
            "is_staff": target_user.is_staff,
        },
    )
    return _teacher_account_redirect(request, notice=f"Set teacher account '{target_user.username}' as {role_label}.")


@staff_member_required
@require_POST
def teach_reset_teacher_account_password(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = _resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    new_password = (request.POST.get("teacher_account_password") or "").strip()
    if not new_password:
        return _teacher_account_redirect(request, error="Temporary password is required.")
    try:
        validate_password(new_password, user=target_user)
    except ValidationError as exc:
        return _teacher_account_redirect(request, error=" ".join(exc.messages))

    target_user.set_password(new_password)
    target_user.save(update_fields=["password"])
    _audit(
        request,
        action="teacher_account.reset_password",
        target_type="User",
        target_id=str(target_user.id),
        summary=f"Reset teacher account password for {target_user.username}",
        metadata={"user_id": target_user.id, "username": target_user.username},
    )
    return _teacher_account_redirect(request, notice=f"Reset password for '{target_user.username}'.")


@staff_member_required
@require_POST
def teach_resend_teacher_invite(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = _resolve_staff_target_user(request)
    if error_response is not None:
        return error_response
    if not target_user.is_active:
        return _teacher_account_redirect(request, error="Activate the teacher account before sending an invite.")
    if not (target_user.email or "").strip():
        return _teacher_account_redirect(request, error="Teacher account must have an email before sending an invite.")
    try:
        validate_email(target_user.email)
    except Exception:
        return _teacher_account_redirect(request, error="Teacher account email is invalid.")

    setup_url = _build_setup_url(request, user=target_user)
    email_error = ""
    try:
        _send_teacher_onboarding_email(
            request,
            user=target_user,
            setup_url=setup_url,
            starting_password="",
        )
    except Exception as exc:
        email_error = str(exc)
    _audit(
        request,
        action="teacher_account.resend_invite",
        target_type="User",
        target_id=str(target_user.id),
        summary=f"Resent teacher invite for {target_user.username}",
        metadata={
            "user_id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "email_sent": not bool(email_error),
            "setup_url_host": urlparse(setup_url).netloc,
        },
    )
    if email_error:
        return _teacher_account_redirect(request, error=f"Invite email failed: {email_error}")
    return _teacher_account_redirect(request, notice=f"Sent a new 2FA invite to '{target_user.username}'.")


__all__ = [
    "teach_create_teacher",
    "teach_reset_teacher_account_password",
    "teach_resend_teacher_invite",
    "teach_set_teacher_account_active",
    "teach_set_teacher_account_superuser",
]
