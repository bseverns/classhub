"""Teacher account state/password control endpoints."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .shared import _audit, require_POST, staff_member_required
from .auth_teacher_accounts_shared import (
    require_superuser as _require_superuser,
    resolve_staff_target_user,
    teacher_account_redirect,
    would_remove_last_active_superuser,
)


@staff_member_required
@require_POST
def teach_set_teacher_account_active(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    is_active = (request.POST.get("teacher_account_active") or "").strip() == "1"
    if target_user.id == request.user.id and not is_active:
        return teacher_account_redirect(request, error="You cannot disable your current superuser account.")
    if would_remove_last_active_superuser(
        target_user=target_user,
        next_is_active=is_active,
        next_is_superuser=bool(target_user.is_superuser),
    ):
        return teacher_account_redirect(request, error="At least one active superuser account is required.")

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
    return teacher_account_redirect(request, notice=f"Set teacher account '{target_user.username}' {status_label}.")


@staff_member_required
@require_POST
def teach_set_teacher_account_superuser(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    is_superuser = (request.POST.get("teacher_account_superuser") or "").strip() == "1"
    if target_user.id == request.user.id and not is_superuser:
        return teacher_account_redirect(request, error="You cannot remove superuser from your current account.")
    if would_remove_last_active_superuser(
        target_user=target_user,
        next_is_active=bool(target_user.is_active),
        next_is_superuser=is_superuser,
    ):
        return teacher_account_redirect(request, error="At least one active superuser account is required.")

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
    return teacher_account_redirect(request, notice=f"Set teacher account '{target_user.username}' as {role_label}.")


@staff_member_required
@require_POST
def teach_reset_teacher_account_password(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    target_user, error_response = resolve_staff_target_user(request)
    if error_response is not None:
        return error_response

    new_password = (request.POST.get("teacher_account_password") or "").strip()
    if not new_password:
        return teacher_account_redirect(request, error="Temporary password is required.")
    try:
        validate_password(new_password, user=target_user)
    except ValidationError as exc:
        return teacher_account_redirect(request, error=" ".join(exc.messages))

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
    return teacher_account_redirect(request, notice=f"Reset password for '{target_user.username}'.")


__all__ = [
    "teach_reset_teacher_account_password",
    "teach_set_teacher_account_active",
    "teach_set_teacher_account_superuser",
]
