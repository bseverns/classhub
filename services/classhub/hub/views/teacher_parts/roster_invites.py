"""Teacher class invite-link and summary-export endpoints."""

from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store, safe_attachment_filename
from ...models import Class, ClassInviteLink
from ...services.filenames import safe_filename
from ...services.teacher_roster_class import export_class_summary_csv
from .shared_auth import (
    staff_can_manage_classroom,
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


def _parse_enrollment_mode(raw: str) -> str:
    mode = (raw or "").strip().lower()
    allowed = {
        Class.ENROLLMENT_OPEN,
        Class.ENROLLMENT_INVITE_ONLY,
        Class.ENROLLMENT_CLOSED,
    }
    return mode if mode in allowed else ""


def _class_notice_redirect(request, classroom, *, notice: str = "", error: str = ""):
    class_path = _teach_class_path(classroom.id)
    return _safe_internal_redirect(
        request,
        _with_notice(class_path, notice=notice, error=error),
        fallback=class_path,
    )


def _parse_invite_link_fields(request) -> tuple[str, int | None, int | None, str]:
    label = (request.POST.get("label") or "").strip()[:120]
    expires_hours_raw = (request.POST.get("expires_in_hours") or "").strip()
    seat_cap_raw = (request.POST.get("seat_cap") or "").strip()

    expires_in_hours = _parse_positive_int(expires_hours_raw, min_value=1, max_value=24 * 90)
    if expires_hours_raw and expires_in_hours is None:
        return label, None, None, "Expiry must be between 1 and 2160 hours."

    seat_cap = _parse_positive_int(seat_cap_raw, min_value=1, max_value=5000)
    if seat_cap_raw and seat_cap is None:
        return label, None, None, "Seat cap must be between 1 and 5000."

    return label, expires_in_hours, seat_cap, ""


def _create_invite_link(request, *, classroom: Class, label: str, expires_in_hours: int | None, seat_cap: int | None):
    expires_at = timezone.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    invite = ClassInviteLink.objects.create(
        classroom=classroom,
        label=label,
        expires_at=expires_at,
        max_uses=seat_cap,
        created_by=request.user if request.user.is_authenticated else None,
    )
    invite_url = request.build_absolute_uri(f"/invite/{invite.token}")
    return invite, invite_url, expires_at


@staff_member_required
@require_POST
def teach_create_invite_link(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    label, expires_in_hours, seat_cap, validation_error = _parse_invite_link_fields(request)
    if validation_error:
        return _class_notice_redirect(request, classroom, error=validation_error)

    invite, invite_url, expires_at = _create_invite_link(
        request,
        classroom=classroom,
        label=label,
        expires_in_hours=expires_in_hours,
        seat_cap=seat_cap,
    )
    _audit(
        request,
        action="class.invite_link_create",
        classroom=classroom,
        target_type="ClassInviteLink",
        target_id=str(invite.id),
        summary=f"Created class invite link for {classroom.name}",
        metadata={
            "invite_id": invite.id,
            "has_expiry": bool(expires_at),
            "max_uses": seat_cap,
        },
    )
    return _class_notice_redirect(request, classroom, notice=f"Invite created. Share link: {invite_url}")


@staff_member_required
@require_POST
def teach_disable_invite_link(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    try:
        invite_id = int((request.POST.get("invite_id") or "0").strip())
    except Exception:
        invite_id = 0
    if invite_id <= 0:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invalid invite link selection."),
            fallback=_teach_class_path(classroom.id),
        )

    invite = ClassInviteLink.objects.filter(id=invite_id, classroom=classroom).first()
    if invite is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invite link not found."),
            fallback=_teach_class_path(classroom.id),
        )

    if invite.is_active:
        invite.is_active = False
        invite.save(update_fields=["is_active"])

    _audit(
        request,
        action="class.invite_link_disable",
        classroom=classroom,
        target_type="ClassInviteLink",
        target_id=str(invite.id),
        summary=f"Disabled class invite link for {classroom.name}",
        metadata={"invite_id": invite.id},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice="Invite link disabled."),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
def teach_export_class_summary_csv(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)

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
    response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_set_enrollment_mode(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
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
    "teach_create_invite_link",
    "teach_disable_invite_link",
    "teach_export_class_summary_csv",
    "teach_set_enrollment_mode",
]
