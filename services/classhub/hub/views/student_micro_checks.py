"""Student micro-check endpoint and state helpers."""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from common.request_safety import client_ip_from_request

from ..models import Class, StudentEvent, StudentIdentity
from ..services.ip_privacy import minimize_student_event_ip

logger = logging.getLogger(__name__)


def _micro_check_signal_config() -> dict[str, dict]:
    return {
        "can_do_this": {
            "event_type": StudentEvent.EVENT_MICRO_CHECK_CAN_DO_THIS,
            "label": _("I can do this"),
            "notice": _("Saved. Keep going, and ask for help any time."),
        },
        "stuck": {
            "event_type": StudentEvent.EVENT_MICRO_CHECK_STUCK,
            "label": _("I'm stuck"),
            "notice": _("Saved. Your facilitator can see you asked for help."),
        },
        "taught_someone": {
            "event_type": StudentEvent.EVENT_MICRO_CHECK_TAUGHT_SOMEONE,
            "label": _("I taught someone"),
            "notice": _("Saved. Thanks for helping a classmate."),
        },
    }


def latest_micro_check_state(*, classroom: Class, student: StudentIdentity, modules: list) -> dict:
    config = _micro_check_signal_config()
    event_types = [row["event_type"] for row in config.values()]
    latest = (
        StudentEvent.objects.filter(
            classroom=classroom,
            student=student,
            event_type__in=event_types,
        )
        .only("event_type", "details", "created_at")
        .order_by("-created_at", "-id")
        .first()
    )
    if latest is None:
        return {}

    module_by_id = {int(module.id): str(module.title) for module in modules}
    module_id = 0
    try:
        module_id = int((latest.details or {}).get("module_id") or 0)
    except Exception:
        module_id = 0

    label = ""
    for row in config.values():
        if row["event_type"] == latest.event_type:
            label = str(row["label"] or "")
            break
    return {
        "label": label or latest.event_type,
        "created_at": latest.created_at,
        "module_title": module_by_id.get(module_id, ""),
    }


def _emit_micro_check_event(
    *,
    request,
    event_type: str,
    details: dict,
) -> None:
    try:
        StudentEvent.objects.create(
            classroom=request.classroom,
            student=request.student,
            event_type=event_type,
            source="classhub.student_micro_check",
            details=details or {},
            ip_address=(
                minimize_student_event_ip(
                    client_ip_from_request(
                        request,
                        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
                        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
                    )
                )
                or None
            ),
        )
    except Exception:
        logger.exception("student_micro_check_write_failed event_type=%s", event_type)


@require_POST
def student_micro_check(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    signal = (request.POST.get("signal") or "").strip().lower()
    config = _micro_check_signal_config().get(signal)
    if not config:
        return redirect("/student")

    module_id = 0
    try:
        module_id = int((request.POST.get("module_id") or "0").strip() or 0)
    except Exception:
        module_id = 0
    if module_id > 0 and not request.classroom.modules.filter(id=module_id).exists():
        module_id = 0

    details = {
        "signal": signal,
        "session_epoch": int(request.session.get("class_epoch") or 0),
    }
    if module_id > 0:
        details["module_id"] = module_id
    _emit_micro_check_event(
        request=request,
        event_type=str(config["event_type"] or ""),
        details=details,
    )
    return redirect("/student?" + urlencode({"checkin_notice": str(config["notice"] or "")}))


__all__ = [
    "latest_micro_check_state",
    "student_micro_check",
]
