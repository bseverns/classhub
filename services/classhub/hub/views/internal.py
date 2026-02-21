"""Internal service-to-service endpoints (non-browser workflows)."""

from __future__ import annotations

import json
import logging
import re
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import StudentEvent

logger = logging.getLogger(__name__)

_ALLOWED_HELPER_EVENT_DETAIL_KEYS = {
    "request_id",
    "actor_type",
    "backend",
    "scope_verified",
    "attempts",
    "truncated",
}
_SAFE_TOKEN_RE = re.compile(r"^[a-z0-9_-]+$")


def _internal_events_token() -> str:
    return str(getattr(settings, "CLASSHUB_INTERNAL_EVENTS_TOKEN", "") or "").strip()


def _request_token(request) -> str:
    header = (request.headers.get("X-ClassHub-Internal-Token", "") or "").strip()
    if header:
        return header
    auth = (request.headers.get("Authorization", "") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _sanitize_helper_event_details(details: dict) -> dict:
    clean: dict = {}
    dropped = 0
    for key, value in details.items():
        if key not in _ALLOWED_HELPER_EVENT_DETAIL_KEYS:
            dropped += 1
            continue
        if key == "request_id":
            request_id = str(value or "").strip()[:80]
            if request_id:
                clean[key] = request_id
            continue
        if key in {"actor_type", "backend"}:
            token = str(value or "").strip().lower()[:32]
            if token and _SAFE_TOKEN_RE.fullmatch(token):
                clean[key] = token
            else:
                dropped += 1
            continue
        if key in {"scope_verified", "truncated"}:
            clean[key] = bool(value)
            continue
        if key == "attempts":
            try:
                attempts = int(value)
            except Exception:
                dropped += 1
                continue
            if attempts >= 0:
                clean[key] = attempts
            else:
                dropped += 1
            continue

    if dropped:
        logger.debug("internal_helper_event_details_dropped count=%s", dropped)
    return clean


@csrf_exempt
@require_POST
def internal_helper_chat_access_event(request):
    """Append helper chat metadata from homework_helper into StudentEvent."""
    expected = _internal_events_token()
    if not expected:
        return JsonResponse({"error": "internal_event_token_not_configured"}, status=503)

    provided = _request_token(request)
    if not provided or not secrets.compare_digest(provided, expected):
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad_json"}, status=400)

    try:
        classroom_id = int(payload.get("classroom_id") or 0)
    except Exception:
        classroom_id = 0
    try:
        student_id = int(payload.get("student_id") or 0)
    except Exception:
        student_id = 0

    ip_address = (payload.get("ip_address") or "").strip()
    details = payload.get("details") or {}
    if not isinstance(details, dict):
        return JsonResponse({"error": "invalid_details"}, status=400)
    details = _sanitize_helper_event_details(details)

    if classroom_id <= 0 and student_id <= 0:
        return JsonResponse({"ok": True, "skipped": "no_actor"})

    try:
        StudentEvent.objects.create(
            classroom_id=classroom_id if classroom_id > 0 else None,
            student_id=student_id if student_id > 0 else None,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="homework_helper.chat",
            details=details,
            ip_address=ip_address or None,
        )
    except Exception as exc:
        logger.warning("internal_helper_event_write_failed: %s", exc.__class__.__name__)
        return JsonResponse({"error": "event_write_failed"}, status=500)

    return JsonResponse({"ok": True})


__all__ = [
    "internal_helper_chat_access_event",
]
