"""Teacher class roster control/export endpoints."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ...models import StudentIdentity, Submission
from ...services.filenames import safe_filename
from ...services.submission_quota import invalidate_classroom_submission_quota_cache
from ...services.teacher_roster_class import export_submissions_today_archive
from .shared_auth import (
    staff_can_manage_policy,
    staff_can_manage_roster,
    staff_can_view_submissions,
    staff_classroom_or_none,
    staff_member_required,
)
from .shared_ordering import _next_unique_class_join_code
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice
from .shared_tracker import _local_day_window

_RESET_EXPORT_ALLOWED_VALUES = {"0", "1", "true", "false", "yes", "no", "on", "off"}
_RESET_EXPORT_TRUE_VALUES = {"1", "true", "yes", "on"}


@staff_member_required
@require_POST
def teach_reset_roster(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    rotate_code = (request.POST.get("rotate_code") or "1").strip() == "1"

    students_qs = StudentIdentity.objects.filter(classroom=classroom)
    student_count = students_qs.count()
    submission_count = Submission.objects.filter(student__classroom=classroom).count()

    students_qs.delete()
    invalidate_classroom_submission_quota_cache(classroom_id=classroom.id)

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


def teach_reset_helper_conversations_impl(
    *,
    request,
    class_id: int,
    reset_helper_conversations_fn: Callable[..., object],
):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    export_before_reset = _coerce_export_before_reset(request)

    result = reset_helper_conversations_fn(
        class_id=classroom.id,
        endpoint_url=str(getattr(settings, "HELPER_INTERNAL_RESET_URL", "") or "").strip(),
        internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
        timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_RESET_TIMEOUT_SECONDS", 2.0) or 2.0),
        export_before_reset=export_before_reset,
    )
    if not result.ok:
        return _helper_reset_failed_redirect(request=request, classroom=classroom, result=result)

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
            "helper_request_id": result.request_id,
            "export_before_reset": export_before_reset,
            "status_code": result.status_code,
        },
    )
    notice = _helper_reset_success_notice(result=result)
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


def _coerce_export_before_reset(request) -> bool:
    export_before_reset = bool(getattr(settings, "HELPER_INTERNAL_RESET_EXPORT_BEFORE_DELETE", True))
    posted_export_before_reset = (request.POST.get("export_before_reset") or "").strip().lower()
    if posted_export_before_reset in _RESET_EXPORT_ALLOWED_VALUES:
        return posted_export_before_reset in _RESET_EXPORT_TRUE_VALUES
    return export_before_reset


def _helper_reset_failed_redirect(*, request, classroom, result):
    _audit(
        request,
        action="class.reset_helper_conversations_failed",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Failed helper conversation reset for {classroom.name}",
        metadata={
            "error_code": result.error_code,
            "helper_request_id": result.request_id,
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


def _helper_reset_success_notice(*, result) -> str:
    notice = f"Helper conversations reset. Cleared {result.deleted_conversations} conversation(s)."
    if result.archived_conversations <= 0:
        return notice
    notice += f" Archived {result.archived_conversations} conversation(s)"
    if result.archive_path:
        notice += f" to {result.archive_path}"
    return f"{notice}."


@staff_member_required
@require_POST
def teach_toggle_lock(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)
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
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

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
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_view_submissions(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

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
@require_POST
def teach_rotate_code(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

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
    "teach_export_class_submissions_today",
    "teach_lock_class",
    "teach_reset_helper_conversations_impl",
    "teach_reset_roster",
    "teach_rotate_code",
    "teach_toggle_lock",
]
