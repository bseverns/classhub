"""Student identity update endpoints."""

from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..models import StudentEvent
from ..services.join_flow_service import normalize_display_name, validate_display_name_safety

_EVENT_STUDENT_RENAME = "student_rename_display_name"


@require_POST
def student_rename_display_name(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    student = request.student
    new_name = normalize_display_name(request.POST.get("display_name") or "")
    if not new_name:
        notice = _("Display name cannot be empty.")
        return redirect("/student/my-data?" + urlencode({"notice": notice}))

    if new_name == student.display_name:
        notice = _("Display name unchanged.")
        return redirect("/student/my-data?" + urlencode({"notice": notice}))

    safety_mode = str(getattr(settings, "NAME_SAFETY_MODE", "warn") or "warn").strip().lower()
    warning_reason = ""
    if safety_mode != "off":
        is_flagged, warning_reason = validate_display_name_safety(new_name)
        if is_flagged and safety_mode == "strict":
            message = {
                "email_pattern": _("That looks like an email address. Please use a nickname or display name instead."),
                "phone_pattern": _("That looks like a phone number. Please use a nickname or display name instead."),
            }.get(warning_reason, _("Please use a nickname or display name instead of personal information."))
            return redirect("/student/my-data?" + urlencode({"notice": message}))

    old_name = student.display_name
    student.display_name = new_name
    student.save(update_fields=["display_name"])
    try:
        StudentEvent.objects.create(
            classroom=request.classroom,
            student=student,
            event_type=_EVENT_STUDENT_RENAME,
            source="classhub.student_my_data",
            details={
                "safety_mode": safety_mode,
                "safety_warning": warning_reason,
                "changed": old_name != new_name,
            },
        )
    except Exception:
        pass

    notice = _("Display name updated.")
    if warning_reason:
        notice += " " + {
            "email_pattern": _("Heads-up: this looks like an email address. A nickname is safer."),
            "phone_pattern": _("Heads-up: this looks like a phone number. A nickname is safer."),
        }.get(warning_reason, _("Consider using a nickname instead of personal information."))
    return redirect("/student/my-data?" + urlencode({"notice": notice}))


__all__ = [
    "student_rename_display_name",
]
