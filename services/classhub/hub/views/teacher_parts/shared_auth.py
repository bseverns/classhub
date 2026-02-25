"""Teacher auth and 2FA setup helper functions."""

import base64
import hashlib
import logging
import re
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required as django_staff_member_required
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django_otp.plugins.otp_totp.models import TOTPDevice
from qrcode.image.svg import SvgPathImage

_TEMPLATE_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")
_AUTHORING_TEMPLATE_SUFFIXES = {
    "teacher_plan_md": "teacher-plan-template.md",
    "teacher_plan_docx": "teacher-plan-template.docx",
    "public_overview_md": "public-overview-template.md",
    "public_overview_docx": "public-overview-template.docx",
}
_TEACHER_2FA_TOKEN_SALT = "classhub.teacher-2fa-setup"
_TEACHER_2FA_TOKEN_USED_CACHE_PREFIX = "classhub:teacher-2fa:used:"
logger = logging.getLogger(__name__)


def staff_member_required(view_func=None):
    """
    Wrap the Django admin staff_member_required decorator to redirect unauthenticated
    teachers to /teach/login instead of the Django admin login page.
    """
    if view_func is None:
        return lambda f: django_staff_member_required(f, login_url="/teach/login")
    return django_staff_member_required(view_func, login_url="/teach/login")


def _teacher_2fa_device_name() -> str:
    configured = (getattr(settings, "TEACHER_2FA_DEVICE_NAME", "teacher-primary") or "").strip()
    return configured or "teacher-primary"


def _product_name() -> str:
    configured = (getattr(settings, "CLASSHUB_PRODUCT_NAME", "Class Hub") or "").strip()
    return configured or "Class Hub"


def _teacher_invite_max_age_seconds() -> int:
    raw = int(getattr(settings, "TEACHER_2FA_INVITE_MAX_AGE_SECONDS", 24 * 3600) or 0)
    return raw if raw > 0 else 24 * 3600


def _teacher_setup_token_cache_key(token: str) -> str:
    digest = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    return f"{_TEACHER_2FA_TOKEN_USED_CACHE_PREFIX}{digest}"


def _build_teacher_setup_token(user) -> str:
    payload = {
        "uid": int(user.id),
        "email": (user.email or "").strip().lower(),
        "username": (user.get_username() or "").strip(),
    }
    return signing.dumps(payload, salt=_TEACHER_2FA_TOKEN_SALT)


def _resolve_teacher_setup_user(token: str, *, consume: bool = False):
    if not token:
        return None, "Missing setup token."
    cache_key = _teacher_setup_token_cache_key(token)
    if not consume:
        try:
            if cache.get(cache_key):
                return None, "This setup link was already used. Ask an admin for a new invite."
        except Exception:
            logger.warning("teacher_setup_token_cache_check_failed")
    try:
        payload = signing.loads(
            token,
            salt=_TEACHER_2FA_TOKEN_SALT,
            max_age=_teacher_invite_max_age_seconds(),
        )
    except signing.SignatureExpired:
        return None, "This setup link expired. Ask an admin to send a new invite."
    except signing.BadSignature:
        return None, "Invalid setup link."

    try:
        user_id = int(payload.get("uid") or 0)
    except Exception:
        user_id = 0
    email = (payload.get("email") or "").strip().lower()
    username = (payload.get("username") or "").strip()
    if not user_id or not email or not username:
        return None, "Invalid setup link payload."

    User = get_user_model()
    user = User.objects.filter(
        id=user_id,
        username=username,
        email__iexact=email,
        is_staff=True,
        is_active=True,
    ).first()
    if not user:
        return None, "Invite is no longer valid for an active teacher account."
    if consume:
        try:
            cache_claimed = bool(cache.add(cache_key, "1", timeout=_teacher_invite_max_age_seconds()))
        except Exception:
            logger.warning("teacher_setup_token_cache_mark_failed")
            cache_claimed = True
        if not cache_claimed:
            return None, "This setup link was already used. Ask an admin for a new invite."
    return user, ""


def _totp_secret_base32(device: TOTPDevice) -> str:
    return base64.b32encode(device.bin_key).decode("ascii").rstrip("=")


def _format_base32_for_display(secret: str) -> str:
    groups = [secret[idx : idx + 4] for idx in range(0, len(secret), 4)]
    return " ".join(groups)


def _totp_qr_svg(config_url: str) -> str:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(config_url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    stream = BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def _send_teacher_onboarding_email(request, *, user, setup_url: str, starting_password: str = ""):
    app_host = request.get_host()
    login_url = request.build_absolute_uri("/teach/login")
    product_name = _product_name()
    from_email = (getattr(settings, "TEACHER_INVITE_FROM_EMAIL", "") or "").strip() or getattr(
        settings, "DEFAULT_FROM_EMAIL", "classhub@localhost"
    )
    include_password = bool(starting_password)
    lines = [
        f"Hi {user.first_name or user.username},",
        "",
        f"Your {product_name} teacher account is ready.",
        "",
        f"Username: {user.username}",
    ]
    if include_password:
        lines.extend(
            [
                f"Temporary password: {starting_password}",
                "",
                "Change your password after first sign-in.",
            ]
        )
    lines.extend(
        [
            "",
            "Finalize two-factor setup here:",
            setup_url,
            "",
            "What to do:",
            "1) Open the setup link.",
            "2) Scan the QR code in your authenticator app.",
            "3) Enter the 6-digit code to confirm.",
            "",
            f"Teacher login: {login_url}",
            f"Host: {app_host}",
        ]
    )
    send_mail(
        subject=f"Complete your {product_name} teacher 2FA setup",
        message="\n".join(lines),
        from_email=from_email,
        recipient_list=[user.email],
        fail_silently=False,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
