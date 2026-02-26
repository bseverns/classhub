"""Teacher self-service profile and password endpoints."""

from .shared import (
    _audit,
    _safe_internal_redirect,
    _with_notice,
    require_POST,
    staff_member_required,
    update_session_auth_hash,
    validate_email,
    validate_password,
)


def _profile_form_values(request):
    return {
        "profile_tab": "1",
        "profile_first_name": (request.POST.get("first_name") or "").strip()[:150],
        "profile_last_name": (request.POST.get("last_name") or "").strip()[:150],
        "profile_email": (request.POST.get("email") or "").strip(),
    }


@staff_member_required
@require_POST
def teach_update_profile(request):
    form_values = _profile_form_values(request)
    email = form_values["profile_email"]
    if email:
        try:
            validate_email(email)
        except Exception:
            return _safe_internal_redirect(
                request,
                _with_notice("/teach", error="Enter a valid email address.", extra=form_values),
                fallback="/teach",
            )

    user = request.user
    changed = []
    if user.first_name != form_values["profile_first_name"]:
        user.first_name = form_values["profile_first_name"]
        changed.append("first_name")
    if user.last_name != form_values["profile_last_name"]:
        user.last_name = form_values["profile_last_name"]
        changed.append("last_name")
    if user.email != email:
        user.email = email
        changed.append("email")

    if changed:
        user.save(update_fields=changed)
        _audit(
            request,
            action="teacher_profile.update_self",
            target_type="User",
            target_id=str(user.id),
            summary=f"Updated teacher profile for {user.username}",
            metadata={"fields_changed": changed, "has_email": bool(user.email)},
        )
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice="Profile updated.", extra={"profile_tab": "1"}),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_change_password(request):
    current_password = (request.POST.get("current_password") or "").strip()
    new_password = (request.POST.get("new_password") or "").strip()
    confirm_password = (request.POST.get("new_password_confirm") or "").strip()

    if not current_password or not new_password or not confirm_password:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Enter current password and both new password fields.", extra={"profile_tab": "1"}),
            fallback="/teach",
        )
    if new_password != confirm_password:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="New password fields must match.", extra={"profile_tab": "1"}),
            fallback="/teach",
        )
    if not request.user.check_password(current_password):
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error="Current password is incorrect.", extra={"profile_tab": "1"}),
            fallback="/teach",
        )
    try:
        validate_password(new_password, user=request.user)
    except Exception as exc:
        return _safe_internal_redirect(
            request,
            _with_notice("/teach", error=f"Password rejected: {exc}", extra={"profile_tab": "1"}),
            fallback="/teach",
        )

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    _audit(
        request,
        action="teacher_profile.change_password",
        target_type="User",
        target_id=str(request.user.id),
        summary=f"Changed password for {request.user.username}",
        metadata={"username": request.user.username},
    )
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice="Password updated.", extra={"profile_tab": "1"}),
        fallback="/teach",
    )


__all__ = [
    "teach_update_profile",
    "teach_change_password",
]
