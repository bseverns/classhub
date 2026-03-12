"""Shared helpers for teacher account onboarding/admin endpoints."""

from .shared import (
    _build_teacher_setup_token,
    _parse_positive_int,
    _safe_internal_redirect,
    _with_notice,
    get_user_model,
    urlencode,
)

_SUPERUSER_ONLY_ERROR = "Only superusers can manage teacher accounts."


def teacher_account_redirect(request, *, notice: str = "", error: str = "", extra: dict | None = None):
    payload = {"teacher_invite": "1"}
    if extra:
        payload.update(extra)
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, error=error, extra=payload),
        fallback="/teach",
    )


def require_superuser(request):
    if request.user.is_superuser:
        return None
    return teacher_account_redirect(request, error=_SUPERUSER_ONLY_ERROR)


def resolve_staff_target_user(request):
    user_id = _parse_positive_int(
        (request.POST.get("teacher_account_user_id") or "").strip(),
        min_value=1,
        max_value=2_147_483_647,
    )
    if user_id is None:
        return None, teacher_account_redirect(request, error="Select a teacher account.")
    User = get_user_model()
    target_user = User.objects.filter(id=user_id, is_staff=True).first()
    if target_user is None:
        return None, teacher_account_redirect(request, error="Teacher account not found.")
    return target_user, None


def would_remove_last_active_superuser(*, target_user, next_is_active: bool, next_is_superuser: bool) -> bool:
    currently_active_superuser = bool(target_user.is_active and target_user.is_superuser)
    if not currently_active_superuser or (next_is_active and next_is_superuser):
        return False
    User = get_user_model()
    return not User.objects.filter(is_staff=True, is_superuser=True, is_active=True).exclude(id=target_user.id).exists()


def build_setup_url(request, *, user):
    token = _build_teacher_setup_token(user)
    return request.build_absolute_uri(f"/teach/2fa/setup?{urlencode({'token': token})}")


__all__ = [
    "build_setup_url",
    "require_superuser",
    "resolve_staff_target_user",
    "teacher_account_redirect",
    "would_remove_last_active_superuser",
]
