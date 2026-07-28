"""Student join/session helper logic used by view adapters."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.db import IntegrityError

from ..models import Class, StudentIdentity, gen_student_return_code

DEVICE_HINT_SIGNING_SALT = "classhub.student-device-hint"

# ── Name-safety checks (bounded, linear-time) ───────────────────────
_MAX_NAME_SAFETY_SCAN_CHARS = 256
_EMAIL_LOCAL_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!#$%&'*+/=?^_`{|}~-")
_PHONE_ALLOWED_CHARS = set("0123456789 -().+\t")


class JoinValidationError(ValueError):
    """Raised when join payload values fail domain validation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class JoinResolution:
    student: StudentIdentity
    rejoined: bool
    join_mode: str


def normalize_display_name(raw: str, *, max_length: int = 80) -> str:
    # Collapse repeated whitespace/newlines into single spaces for stable matching.
    value = " ".join(str(raw or "").split())
    return value[:max_length]


def _bounded_name_for_safety(name: str) -> str:
    return str(name or "").strip()[:_MAX_NAME_SAFETY_SCAN_CHARS]


def _looks_like_email(value: str) -> bool:
    token = (value or "").strip()
    if not token or " " in token or token.count("@") != 1:
        return False

    local, domain = token.split("@", 1)
    if not local or not domain:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if any(ch not in _EMAIL_LOCAL_ALLOWED for ch in local):
        return False

    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        return False
    labels = domain.split(".")
    if not labels or len(labels[-1]) < 2:
        return False
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if any(not (ch.isalnum() or ch == "-") for ch in label):
            return False
    return True


def _looks_like_phone_number(value: str) -> bool:
    token = (value or "").strip()
    if not token:
        return False

    digits = 0
    separators = 0
    for ch in token:
        if ch.isdigit():
            digits += 1
            continue
        if ch in _PHONE_ALLOWED_CHARS:
            if not ch.isspace():
                separators += 1
            continue
        return False

    if digits < 7 or digits > 15:
        return False
    return separators > 0 or digits >= 10


def validate_display_name_safety(name: str) -> tuple[bool, str]:
    """Check whether *name* looks like PII (email or phone number).

    Returns ``(is_flagged, reason)`` where *reason* is one of
    ``"email_pattern"``, ``"phone_pattern"``, or ``""`` (not flagged).

    The caller should consult ``settings.NAME_SAFETY_MODE`` to decide
    whether to warn or reject.
    """
    trimmed = _bounded_name_for_safety(name)
    if _looks_like_email(trimmed):
        return True, "email_pattern"
    if _looks_like_phone_number(trimmed):
        return True, "phone_pattern"
    return False, ""


def _device_hint_signing_key() -> str:
    return getattr(settings, "DEVICE_HINT_SIGNING_KEY", settings.SECRET_KEY)


def device_hint_cookie_max_age_seconds() -> int:
    days = int(getattr(settings, "DEVICE_REJOIN_MAX_AGE_DAYS", 30))
    return max(days, 1) * 24 * 60 * 60


def create_student_identity(classroom: Class, display_name: str) -> StudentIdentity:
    for _ in range(20):
        code = gen_student_return_code().upper()
        try:
            return StudentIdentity.objects.create(
                classroom=classroom,
                display_name=display_name,
                return_code=code,
            )
        except IntegrityError:
            continue
    raise RuntimeError("could_not_allocate_unique_student_return_code")


def load_device_hint_student(request, classroom: Class, display_name: str) -> StudentIdentity | None:
    cookie_name = getattr(settings, "DEVICE_REJOIN_COOKIE_NAME", "classhub_student_hint")
    raw = request.COOKIES.get(cookie_name)
    if not raw:
        return None
    try:
        payload = signing.loads(
            raw,
            key=_device_hint_signing_key(),
            salt=DEVICE_HINT_SIGNING_SALT,
            max_age=device_hint_cookie_max_age_seconds(),
        )
    except (BadSignature, SignatureExpired):
        return None

    try:
        class_id = int(payload.get("class_id") or 0)
        student_id = int(payload.get("student_id") or 0)
    except Exception:
        return None
    if class_id != classroom.id or student_id <= 0:
        return None

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).order_by("id").first()
    if student is None:
        return None
    if student.display_name.strip().casefold() != display_name.strip().casefold():
        return None
    return student


def load_name_match_student(classroom: Class, display_name: str) -> StudentIdentity | None:
    """Fallback rejoin by class + display-name match."""
    normalized = (display_name or "").strip()
    if not normalized:
        return None
    return (
        StudentIdentity.objects.filter(classroom=classroom, display_name__iexact=normalized)
        .order_by("id")
        .first()
    )


def apply_device_hint_cookie(response, *, classroom: Class, student: StudentIdentity) -> None:
    payload = {"class_id": classroom.id, "student_id": student.id}
    signed = signing.dumps(
        payload,
        key=_device_hint_signing_key(),
        salt=DEVICE_HINT_SIGNING_SALT,
    )
    response.set_cookie(
        getattr(settings, "DEVICE_REJOIN_COOKIE_NAME", "classhub_student_hint"),
        signed,
        max_age=device_hint_cookie_max_age_seconds(),
        httponly=True,
        samesite="Lax",
        secure=settings.SESSION_COOKIE_SECURE,
    )


def clear_device_hint_cookie(response) -> None:
    response.set_cookie(
        getattr(settings, "DEVICE_REJOIN_COOKIE_NAME", "classhub_student_hint"),
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=settings.SESSION_COOKIE_SECURE,
    )


def require_return_code_for_rejoin() -> bool:
    return bool(getattr(settings, "CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN", False))


def resolve_join_student(
    *,
    request,
    classroom: Class,
    display_name: str,
    return_code: str,
) -> JoinResolution:
    student = None
    rejoined = False
    join_mode = "new"
    if return_code:
        student = StudentIdentity.objects.filter(classroom=classroom, return_code=return_code).order_by("id").first()
        if student is None:
            raise JoinValidationError("invalid_return_code")
        if student.display_name.strip().casefold() != display_name.strip().casefold():
            raise JoinValidationError("invalid_return_code")
        rejoined = True
        join_mode = "return_code"
    else:
        if require_return_code_for_rejoin():
            student = load_device_hint_student(request, classroom, display_name)
            if student is not None:
                rejoined = True
                join_mode = "device_hint"
            elif load_name_match_student(classroom, display_name) is not None:
                raise JoinValidationError("return_code_required")
        else:
            student = load_device_hint_student(request, classroom, display_name)
            if student is not None:
                rejoined = True
                join_mode = "device_hint"
            else:
                student = load_name_match_student(classroom, display_name)
                if student is not None:
                    rejoined = True
                    join_mode = "name_match"

    if student is None:
        student = create_student_identity(classroom, display_name)
    return JoinResolution(student=student, rejoined=rejoined, join_mode=join_mode)
