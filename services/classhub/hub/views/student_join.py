"""Student join/index endpoints split from student.py for maintainability."""

import json
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from common.request_safety import client_ip_from_request, fixed_window_allow

from ..http.headers import apply_no_store
from ..models import Class, ClassInviteLink, StudentEvent, StudentIdentity
from ..services.ip_privacy import minimize_student_event_ip
from ..services.join_flow_service import (
    JoinValidationError,
    apply_device_hint_cookie,
    resolve_join_student,
)
from ..services.student_home import privacy_meta_context

logger = logging.getLogger(__name__)


def _invite_error_message(code: str) -> str:
    messages = {
        "invite_invalid": "That invite link is not valid.",
        "invite_inactive": "That invite link has been disabled.",
        "invite_expired": "That invite link has expired.",
        "invite_seat_cap_reached": "That invite link has reached its seat limit.",
    }
    return messages.get(code, "That invite link is not usable right now.")


def _resolve_invite_link(token: str, *, enforce_seat_cap: bool = True) -> tuple[ClassInviteLink | None, str]:
    invite_token = (token or "").strip()
    if not invite_token:
        return None, "invite_missing"
    invite = ClassInviteLink.objects.select_related("classroom").filter(token=invite_token).first()
    if invite is None:
        return None, "invite_invalid"
    if not invite.is_active:
        return None, "invite_inactive"
    if invite.is_expired():
        return None, "invite_expired"
    if enforce_seat_cap and not invite.has_seat_available():
        return None, "invite_seat_cap_reached"
    return invite, ""


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _emit_student_event(
    *,
    event_type: str,
    classroom: Class | None,
    student: StudentIdentity | None,
    source: str,
    details: dict,
    ip_address: str = "",
) -> None:
    try:
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=event_type,
            source=source,
            details=details or {},
            ip_address=(minimize_student_event_ip(ip_address) or None),
        )
    except Exception:
        logger.exception("student_event_write_failed type=%s", event_type)


def _render_join_page(request, *, invite_token: str = ""):
    invite, invite_error = _resolve_invite_link(invite_token, enforce_seat_cap=False) if invite_token else (None, "")
    if invite is not None and not invite.has_seat_available():
        invite_error = "invite_seat_cap_reached"
    get_token(request)
    response = render(
        request,
        "student_join.html",
        {
            "invite_join_classroom": invite.classroom if invite else None,
            "invite_join_token": invite.token if invite else "",
            "invite_join_error": invite_error,
            "invite_join_error_message": _invite_error_message(invite_error) if invite_error else "",
            **privacy_meta_context(),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def invite_join(request, invite_token: str):
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    return _render_join_page(request, invite_token=invite_token.strip())


def index(request):
    """Landing page for class-code + no-login student access."""
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    return _render_join_page(request, invite_token=(request.GET.get("invite") or "").strip())


@require_POST
def join_class(request):
    """Join via class code + display name, optionally using invite token."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_no_store_response({"error": "bad_json"}, status=400)

    client_ip = client_ip_from_request(
        request,
        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
    )
    request_id = (request.META.get("HTTP_X_REQUEST_ID", "") or "").strip()
    join_limit = int(getattr(settings, "JOIN_RATE_LIMIT_PER_MINUTE", 20))
    if not fixed_window_allow(
        f"join:ip:{client_ip}:m",
        limit=join_limit,
        window_seconds=60,
        request_id=request_id,
    ):
        return _json_no_store_response({"error": "rate_limited"}, status=429)

    code = (payload.get("class_code") or "").strip().upper()
    name = (payload.get("display_name") or "").strip()[:80]
    return_code = (payload.get("return_code") or "").strip().upper()
    invite_token = (payload.get("invite_token") or "").strip()

    if not name or (not code and not invite_token):
        return _json_no_store_response({"error": "missing_fields"}, status=400)

    invite = None
    if invite_token:
        invite, invite_error = _resolve_invite_link(invite_token, enforce_seat_cap=False)
        if invite is None:
            return _json_no_store_response({"error": invite_error}, status=403)
        classroom = invite.classroom
    else:
        classroom = Class.objects.filter(join_code=code).first()
        if not classroom:
            return _json_no_store_response({"error": "invalid_code"}, status=404)
    if classroom is None:
        return _json_no_store_response({"error": "invalid_code"}, status=404)

    with transaction.atomic():
        if invite is not None:
            invite = (
                ClassInviteLink.objects.select_for_update()
                .select_related("classroom")
                .filter(id=invite.id)
                .first()
            )
            if invite is None:
                return _json_no_store_response({"error": "invite_invalid"}, status=403)
            if not invite.is_active:
                return _json_no_store_response({"error": "invite_inactive"}, status=403)
            if invite.is_expired():
                return _json_no_store_response({"error": "invite_expired"}, status=403)
            classroom = invite.classroom

        classroom = Class.objects.select_for_update().filter(id=classroom.id).first()
        if classroom is None:
            return _json_no_store_response({"error": "invalid_code"}, status=404)
        if classroom.is_locked:
            return _json_no_store_response({"error": "class_locked"}, status=403)

        try:
            join_result = resolve_join_student(
                request=request,
                classroom=classroom,
                display_name=name,
                return_code=return_code,
            )
            if invite is not None and join_result.join_mode == "new":
                if not invite.has_seat_available():
                    raise JoinValidationError("invite_seat_cap_reached")
                invite.use_count = int(invite.use_count or 0) + 1
                invite.last_used_at = timezone.now()
                invite.save(update_fields=["use_count", "last_used_at"])
            elif invite is not None:
                invite.last_used_at = timezone.now()
                invite.save(update_fields=["last_used_at"])
        except JoinValidationError as exc:
            return _json_no_store_response({"error": exc.code}, status=400)
        student = join_result.student
        rejoined = join_result.rejoined
        join_mode = join_result.join_mode

        student.last_seen_at = timezone.now()
        student.save(update_fields=["last_seen_at"])

    request.session.cycle_key()
    request.session["student_id"] = student.id
    request.session["class_id"] = classroom.id
    request.session["class_epoch"] = int(getattr(classroom, "session_epoch", 1) or 1)
    rotate_token(request)

    response = _json_no_store_response({"ok": True, "return_code": student.return_code, "rejoined": rejoined})
    apply_device_hint_cookie(response, classroom=classroom, student=student)
    if join_mode == "return_code":
        event_type = StudentEvent.EVENT_REJOIN_RETURN_CODE
    elif join_mode in {"device_hint", "name_match"}:
        event_type = StudentEvent.EVENT_REJOIN_DEVICE_HINT
    else:
        event_type = StudentEvent.EVENT_CLASS_JOIN
    _emit_student_event(
        event_type=event_type,
        classroom=classroom,
        student=student,
        source="classhub.join_class",
        details={
            "join_mode": join_mode,
            **({"invite_id": int(invite.id)} if invite is not None else {}),
        },
        ip_address=client_ip,
    )
    return response


__all__ = [
    "index",
    "invite_join",
    "join_class",
]
