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


def _join_rate_limit_exceeded(request, *, client_ip: str) -> bool:
    request_id = (request.META.get("HTTP_X_REQUEST_ID", "") or "").strip()
    join_limit = int(getattr(settings, "JOIN_RATE_LIMIT_PER_MINUTE", 20))
    return not fixed_window_allow(
        f"join:ip:{client_ip}:m",
        limit=join_limit,
        window_seconds=60,
        request_id=request_id,
    )


def _parse_join_request(request) -> tuple[dict, str, JsonResponse | None]:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}, "", _json_no_store_response({"error": "bad_json"}, status=400)

    client_ip = client_ip_from_request(
        request,
        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
    )
    if _join_rate_limit_exceeded(request, client_ip=client_ip):
        return {}, client_ip, _json_no_store_response({"error": "rate_limited"}, status=429)

    fields = {
        "code": (payload.get("class_code") or "").strip().upper(),
        "name": (payload.get("display_name") or "").strip()[:80],
        "return_code": (payload.get("return_code") or "").strip().upper(),
        "invite_token": (payload.get("invite_token") or "").strip(),
    }
    if not fields["name"] or (not fields["code"] and not fields["invite_token"]):
        return {}, client_ip, _json_no_store_response({"error": "missing_fields"}, status=400)
    return fields, client_ip, None


def _resolve_join_target(*, code: str, invite_token: str) -> tuple[Class | None, ClassInviteLink | None, str, int]:
    if invite_token:
        invite, invite_error = _resolve_invite_link(invite_token, enforce_seat_cap=False)
        if invite is None:
            return None, None, invite_error, 403
        return invite.classroom, invite, "", 200

    classroom = Class.objects.filter(join_code=code).first()
    if classroom is None:
        return None, None, "invalid_code", 404
    return classroom, None, "", 200


def _lock_invite_for_join(invite: ClassInviteLink | None) -> tuple[ClassInviteLink | None, str]:
    if invite is None:
        return None, ""
    invite = (
        ClassInviteLink.objects.select_for_update()
        .select_related("classroom")
        .filter(id=invite.id)
        .first()
    )
    if invite is None:
        return None, "invite_invalid"
    if not invite.is_active:
        return None, "invite_inactive"
    if invite.is_expired():
        return None, "invite_expired"
    return invite, ""


def _complete_join_transaction(
    request,
    *,
    classroom: Class,
    invite: ClassInviteLink | None,
    display_name: str,
    return_code: str,
) -> tuple[StudentIdentity | None, Class | None, ClassInviteLink | None, bool, str, str, int]:
    with transaction.atomic():
        invite, invite_error = _lock_invite_for_join(invite)
        if invite_error:
            return None, None, None, False, "", invite_error, 403
        if invite is not None:
            classroom = invite.classroom

        classroom = Class.objects.select_for_update().filter(id=classroom.id).first()
        if classroom is None:
            return None, None, invite, False, "", "invalid_code", 404
        if classroom.is_locked:
            return None, classroom, invite, False, "", "class_locked", 403

        try:
            join_result = resolve_join_student(
                request=request,
                classroom=classroom,
                display_name=display_name,
                return_code=return_code,
            )
        except JoinValidationError as exc:
            return None, classroom, invite, False, "", exc.code, 400

        if invite is not None:
            now = timezone.now()
            if join_result.join_mode == "new":
                if not invite.has_seat_available():
                    return None, classroom, invite, False, "", "invite_seat_cap_reached", 400
                invite.use_count = int(invite.use_count or 0) + 1
                invite.last_used_at = now
                invite.save(update_fields=["use_count", "last_used_at"])
            else:
                invite.last_used_at = now
                invite.save(update_fields=["last_used_at"])

        student = join_result.student
        student.last_seen_at = timezone.now()
        student.save(update_fields=["last_seen_at"])

    return student, classroom, invite, join_result.rejoined, join_result.join_mode, "", 200


def _establish_student_session(request, *, student: StudentIdentity, classroom: Class) -> None:
    request.session.cycle_key()
    request.session["student_id"] = student.id
    request.session["class_id"] = classroom.id
    request.session["class_epoch"] = int(getattr(classroom, "session_epoch", 1) or 1)
    rotate_token(request)


def _join_event_type(join_mode: str) -> str:
    if join_mode == "return_code":
        return StudentEvent.EVENT_REJOIN_RETURN_CODE
    if join_mode in {"device_hint", "name_match"}:
        return StudentEvent.EVENT_REJOIN_DEVICE_HINT
    return StudentEvent.EVENT_CLASS_JOIN


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
    fields, client_ip, parse_error = _parse_join_request(request)
    if parse_error is not None:
        return parse_error

    classroom, invite, resolve_error, resolve_status = _resolve_join_target(
        code=fields["code"],
        invite_token=fields["invite_token"],
    )
    if resolve_error:
        return _json_no_store_response({"error": resolve_error}, status=resolve_status)

    student, classroom, invite, rejoined, join_mode, txn_error, txn_status = _complete_join_transaction(
        request,
        classroom=classroom,
        invite=invite,
        display_name=fields["name"],
        return_code=fields["return_code"],
    )
    if txn_error:
        return _json_no_store_response({"error": txn_error}, status=txn_status)

    _establish_student_session(request, student=student, classroom=classroom)
    response = _json_no_store_response({"ok": True, "return_code": student.return_code, "rejoined": rejoined})
    apply_device_hint_cookie(response, classroom=classroom, student=student)
    _emit_student_event(
        event_type=_join_event_type(join_mode),
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
