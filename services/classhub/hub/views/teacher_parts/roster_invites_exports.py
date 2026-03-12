"""Teacher class summary/outcomes export and enrollment-mode endpoints."""

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store, safe_attachment_filename
from ...models import Class
from ...services.filenames import safe_filename
from ...services.teacher_roster_class import export_class_outcomes_csv, export_class_summary_csv
from .shared_auth import (
    staff_can_manage_policy,
    staff_can_view_submissions,
    staff_classroom_or_none,
    staff_member_required,
)
from .shared_routing import (
    _audit,
    _parse_positive_int,
    _safe_internal_redirect,
    _teach_class_path,
    _with_notice,
)


def _class_notice_redirect(request, classroom, *, notice: str = "", error: str = ""):
    class_path = _teach_class_path(classroom.id)
    return _safe_internal_redirect(
        request,
        _with_notice(class_path, notice=notice, error=error),
        fallback=class_path,
    )


def _parse_enrollment_mode(raw: str) -> str:
    mode = (raw or "").strip().lower()
    allowed = {
        Class.ENROLLMENT_OPEN,
        Class.ENROLLMENT_INVITE_ONLY,
        Class.ENROLLMENT_CLOSED,
    }
    return mode if mode in allowed else ""


@staff_member_required
def teach_export_class_summary_csv(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_view_submissions(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    csv_text = export_class_summary_csv(classroom=classroom, active_window_days=7)
    _audit(
        request,
        action="class.export_summary_csv",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Exported class summary CSV for {classroom.name}",
        metadata={"active_window_days": 7},
    )
    day_label = timezone.localdate().strftime("%Y%m%d")
    filename = safe_attachment_filename(f"{safe_filename(classroom.name)}_summary_{day_label}.csv")
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_export_class_outcomes_csv(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_view_submissions(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    active_window_days = _parse_positive_int((request.GET.get("active_window_days") or "").strip(), min_value=1, max_value=365)
    if active_window_days is None:
        active_window_days = 30
    csv_text = export_class_outcomes_csv(classroom=classroom, active_window_days=active_window_days)
    _audit(
        request,
        action="class.export_outcomes_csv",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Exported class outcomes CSV for {classroom.name}",
        metadata={"active_window_days": active_window_days},
    )
    day_label = timezone.localdate().strftime("%Y%m%d")
    filename = safe_attachment_filename(f"{safe_filename(classroom.name)}_outcomes_{day_label}.csv")
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_set_enrollment_mode(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    enrollment_mode = _parse_enrollment_mode(request.POST.get("enrollment_mode") or "")
    if not enrollment_mode:
        return _class_notice_redirect(request, classroom, error="Invalid enrollment mode.")

    old_mode = classroom.enrollment_mode
    if old_mode == enrollment_mode:
        return _class_notice_redirect(request, classroom, notice="Enrollment mode unchanged.")

    classroom.enrollment_mode = enrollment_mode
    classroom.save(update_fields=["enrollment_mode"])
    _audit(
        request,
        action="class.set_enrollment_mode",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Set class enrollment mode to {enrollment_mode}",
        metadata={"old_mode": old_mode, "enrollment_mode": enrollment_mode},
    )
    return _class_notice_redirect(request, classroom, notice="Enrollment mode updated.")


__all__ = [
    "teach_export_class_outcomes_csv",
    "teach_export_class_summary_csv",
    "teach_set_enrollment_mode",
]
