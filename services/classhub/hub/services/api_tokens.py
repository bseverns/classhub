"""Stateless API token utilities for mobile/headless clients.

Student tokens contain {sid, cid, epoch} signed with a dedicated key.
They are validated in StudentSessionMiddleware for /api/ paths.
"""

from django.conf import settings
from django.core import signing

_SALT = "classhub.api-token.v1"


def _signing_key() -> str:
    return getattr(settings, "CLASSHUB_API_TOKEN_SIGNING_KEY", None) or settings.SECRET_KEY


def issue_student_token(*, student_id: int, class_id: int, epoch: int) -> str:
    """Create a signed bearer token for a student session."""
    return signing.dumps(
        {"sid": student_id, "cid": class_id, "epoch": epoch},
        key=_signing_key(),
        salt=_SALT,
    )


def verify_student_token(token: str) -> dict | None:
    """Verify and decode a student bearer token.

    Returns the payload dict on success, or None on failure.
    """
    try:
        return signing.loads(token, key=_signing_key(), salt=_SALT)
    except signing.BadSignature:
        return None
