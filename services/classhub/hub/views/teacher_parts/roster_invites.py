"""Teacher class invite-link and summary-export endpoints."""

from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store, safe_attachment_filename
from ...models import Class, ClassInviteLink
from ...services.filenames import safe_filename
from ...services.teacher_roster_class import export_class_summary_csv
from .shared_auth import staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


@staff_member_required
@require_POST
def teach_create_invite_link(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    label = (request.POST.get("label") or "").strip()[:120]
    expires_hours_raw = (request.POST.get("expires_in_hours") or "").strip()
    seat_cap_raw = (request.POST.get("seat_cap") or "").strip()

    expires_in_hours = None
    if expires_hours_raw:
        try:
            expires_in_hours = int(expires_hours_raw)
        except Exception:
            expires_in_hours = None
        if expires_in_hours is None or expires_in_hours <= 0 or expires_in_hours > 24 * 90:
            return _safe_internal_redirect(
                request,
                _with_notice(
                    _teach_class_path(classroom.id),
                    error="Expiry must be between 1 and 2160 hours.",
                ),
                fallback=_teach_class_path(classroom.id),
            )

    seat_cap = None
    if seat_cap_raw:
        try:
            seat_cap = int(seat_cap_raw)
        except Exception:
            seat_cap = None
        if seat_cap is None or seat_cap <= 0 or seat_cap > 5000:
            return _safe_internal_redirect(
                request,
                _with_notice(
                    _teach_class_path(classroom.id),
                    error="Seat cap must be between 1 and 5000.",
                ),
                fallback=_teach_class_path(classroom.id),
            )

    expires_at = timezone.now() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    invite = ClassInviteLink.objects.create(
        classroom=classroom,
        label=label,
        expires_at=expires_at,
        max_uses=seat_cap,
        created_by=request.user if request.user.is_authenticated else None,
    )
    invite_url = request.build_absolute_uri(f"/invite/{invite.token}")
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
    return _safe_internal_redirect(
        request,
        _with_notice(
            _teach_class_path(classroom.id),
            notice=f"Invite created. Share link: {invite_url}",
        ),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_disable_invite_link(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

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
    classroom = Class.objects.filter(id=class_id).first()
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


__all__ = [
    "teach_create_invite_link",
    "teach_disable_invite_link",
    "teach_export_class_summary_csv",
]
