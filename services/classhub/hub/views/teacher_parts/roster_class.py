"""Teacher class-level roster and dashboard endpoints."""

from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ...models import Class, ClassInviteLink, StudentIdentity, Submission
from ...services.filenames import safe_filename
from ...services.helper_control import reset_class_conversations as _reset_helper_class_conversations
from ...services.teacher_roster_class import (
    build_dashboard_context,
    export_class_summary_csv,
    export_submissions_today_archive,
)
from .shared_auth import staff_member_required
from .shared_ordering import _next_unique_class_join_code, _normalize_order
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice
from .shared_tracker import _local_day_window

@staff_member_required
@require_POST
def teach_create_class(request):
    name = (request.POST.get("name") or "").strip()[:200]
    if not name:
        return redirect("/teach")

    join_code = _next_unique_class_join_code()

    classroom = Class.objects.create(name=name, join_code=join_code)
    _audit(
        request,
        action="class.create",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Created class {classroom.name}",
        metadata={"join_code": classroom.join_code},
    )
    return redirect("/teach")


@staff_member_required
def teach_class_dashboard(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    context = build_dashboard_context(
        request=request,
        classroom=classroom,
        normalize_order_fn=_normalize_order,
    )
    invite_links = list(
        ClassInviteLink.objects.filter(classroom=classroom)
        .select_related("created_by")
        .order_by("-created_at", "-id")
    )
    now = timezone.now()
    for invite in invite_links:
        invite.invite_url = request.build_absolute_uri(f"/invite/{invite.token}")
        invite.is_expired_now = invite.is_expired(at=now)
        invite.seats_remaining_value = invite.seats_remaining()

    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()

    response = render(
        request,
        "teach_class.html",
        {
            "classroom": classroom,
            **context,
            "invite_links": invite_links,
            "notice": notice,
            "error": error,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_class_join_card(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    query = urlencode({"class_code": classroom.join_code})
    response = render(
        request,
        "teach_join_card.html",
        {
            "classroom": classroom,
            "join_url": request.build_absolute_uri("/"),
            "prefilled_join_url": request.build_absolute_uri(f"/?{query}"),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response

@staff_member_required
@require_POST
def teach_reset_roster(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    rotate_code = (request.POST.get("rotate_code") or "1").strip() == "1"

    students_qs = StudentIdentity.objects.filter(classroom=classroom)
    student_count = students_qs.count()
    submission_count = Submission.objects.filter(student__classroom=classroom).count()

    students_qs.delete()

    updated_fields = []
    classroom.session_epoch = int(getattr(classroom, "session_epoch", 1) or 1) + 1
    updated_fields.append("session_epoch")
    if rotate_code:
        classroom.join_code = _next_unique_class_join_code(exclude_class_id=classroom.id)
        updated_fields.append("join_code")
    classroom.save(update_fields=updated_fields)

    _audit(
        request,
        action="class.reset_roster",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Reset roster for {classroom.name}",
        metadata={
            "students_deleted": student_count,
            "submissions_deleted": submission_count,
            "session_epoch": classroom.session_epoch,
            "rotated_join_code": rotate_code,
        },
    )

    notice = f"Roster reset complete. Removed {student_count} students and {submission_count} submissions."
    if rotate_code:
        notice += " Join code rotated."
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


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
@require_POST
def teach_reset_helper_conversations(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    export_before_reset = bool(getattr(settings, "HELPER_INTERNAL_RESET_EXPORT_BEFORE_DELETE", True))
    posted_export_before_reset = (request.POST.get("export_before_reset") or "").strip().lower()
    if posted_export_before_reset in {"0", "1", "true", "false", "yes", "no", "on", "off"}:
        export_before_reset = posted_export_before_reset in {"1", "true", "yes", "on"}

    result = _reset_helper_class_conversations(
        class_id=classroom.id,
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_RESET_URL", "") or "").strip(),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_RESET_TIMEOUT_SECONDS", 2.0) or 2.0),
        export_before_reset=export_before_reset,
    )
    if not result.ok:
        _audit(
            request,
            action="class.reset_helper_conversations_failed",
            classroom=classroom,
            target_type="Class",
            target_id=str(classroom.id),
            summary=f"Failed helper conversation reset for {classroom.name}",
            metadata={
                "error_code": result.error_code,
                "status_code": result.status_code,
            },
        )
        return _safe_internal_redirect(
            request,
            _with_notice(
                _teach_class_path(classroom.id),
                error=f"Could not reset helper conversations ({result.error_code}).",
            ),
            fallback=_teach_class_path(classroom.id),
        )

    _audit(
        request,
        action="class.reset_helper_conversations",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Reset helper conversations for {classroom.name}",
        metadata={
            "deleted_conversations": result.deleted_conversations,
            "archived_conversations": result.archived_conversations,
            "archive_path": result.archive_path,
            "export_before_reset": export_before_reset,
            "status_code": result.status_code,
        },
    )
    notice = f"Helper conversations reset. Cleared {result.deleted_conversations} conversation(s)."
    if result.archived_conversations > 0:
        notice += f" Archived {result.archived_conversations} conversation(s)"
        if result.archive_path:
            notice += f" to {result.archive_path}"
        notice += "."
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_toggle_lock(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)
    classroom.is_locked = not classroom.is_locked
    classroom.save(update_fields=["is_locked"])
    _audit(
        request,
        action="class.toggle_lock",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Toggled class lock to {classroom.is_locked}",
        metadata={"is_locked": classroom.is_locked},
    )
    return _safe_internal_redirect(request, _teach_class_path(classroom.id), fallback="/teach")


@staff_member_required
@require_POST
def teach_lock_class(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    if not classroom.is_locked:
        classroom.is_locked = True
        classroom.save(update_fields=["is_locked"])

    _audit(
        request,
        action="class.lock",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Locked class {classroom.name}",
        metadata={"is_locked": classroom.is_locked},
    )
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=f"Locked class {classroom.name}."),
        fallback="/teach",
    )


@staff_member_required
def teach_export_class_submissions_today(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    day_start, day_end = _local_day_window()
    tmp, file_count = export_submissions_today_archive(
        classroom=classroom,
        day_start=day_start,
        day_end=day_end,
    )

    _audit(
        request,
        action="class.export_submissions_today",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Exported today's submissions for {classroom.name}",
        metadata={
            "day_start": day_start.isoformat(),
            "day_end": day_end.isoformat(),
            "file_count": file_count,
        },
    )

    day_label = timezone.localdate().strftime("%Y%m%d")
    filename = safe_attachment_filename(f"{safe_filename(classroom.name)}_submissions_{day_label}.zip")
    tmp.seek(0)
    response = FileResponse(
        tmp,
        as_attachment=True,
        filename=filename,
        content_type="application/zip",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


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
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_rotate_code(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    classroom.join_code = _next_unique_class_join_code()
    classroom.save(update_fields=["join_code"])
    _audit(
        request,
        action="class.rotate_code",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary="Rotated class join code",
        metadata={"join_code": classroom.join_code},
    )
    return _safe_internal_redirect(request, _teach_class_path(classroom.id), fallback="/teach")

__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_create_invite_link",
    "teach_disable_invite_link",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_summary_csv",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
]
