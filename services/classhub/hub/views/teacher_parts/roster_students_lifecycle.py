"""Teacher student merge/delete lifecycle endpoints."""

from django.conf import settings

from ...services.helper_control import clear_actor_conversations as clear_helper_actor_conversations
from ...services.submission_quota import invalidate_classroom_submission_quota_cache
from ...services.telemetry_events import delete_student_event_history
from .shared import (
    HttpResponse,
    StudentEvent,
    StudentIdentity,
    Submission,
    _audit,
    _safe_internal_redirect,
    _teach_class_path,
    _with_notice,
    require_POST,
    staff_can_manage_roster,
    staff_classroom_or_none,
    staff_member_required,
    transaction,
)


def _parse_student_id(raw: str | None) -> int:
    try:
        return int((raw or "0").strip())
    except Exception:
        return 0


@staff_member_required
@require_POST
def teach_merge_students(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    source_student_id = _parse_student_id(request.POST.get("source_student_id"))
    target_student_id = _parse_student_id(request.POST.get("target_student_id"))
    confirmed = (request.POST.get("confirm_merge") or "").strip() == "1"

    if not source_student_id or not target_student_id:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Select both source and destination students."),
            fallback=_teach_class_path(classroom.id),
        )
    if source_student_id == target_student_id:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Source and destination must be different students."),
            fallback=_teach_class_path(classroom.id),
        )
    if not confirmed:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Confirm merge before continuing."),
            fallback=_teach_class_path(classroom.id),
        )

    with transaction.atomic():
        source = StudentIdentity.objects.select_for_update().filter(id=source_student_id, classroom=classroom).first()
        target = StudentIdentity.objects.select_for_update().filter(id=target_student_id, classroom=classroom).first()

        if source is None:
            return _safe_internal_redirect(
                request,
                _with_notice(_teach_class_path(classroom.id), error="Source student not found in this class."),
                fallback=_teach_class_path(classroom.id),
            )
        if target is None:
            return _safe_internal_redirect(
                request,
                _with_notice(_teach_class_path(classroom.id), error="Destination student not found in this class."),
                fallback=_teach_class_path(classroom.id),
            )

        moved_submissions = Submission.objects.filter(student=source).update(student=target)
        moved_events = StudentEvent.objects.filter(student=source).update(student=target)

        update_target_fields: list[str] = []
        source_last_seen = source.last_seen_at
        target_last_seen = target.last_seen_at
        if source_last_seen and (target_last_seen is None or source_last_seen > target_last_seen):
            target.last_seen_at = source_last_seen
            update_target_fields.append("last_seen_at")
        if update_target_fields:
            target.save(update_fields=update_target_fields)

        source_name = source.display_name
        source_code = source.return_code
        target_name = target.display_name
        target_code = target.return_code
        source.delete()

    _audit(
        request,
        action="student.merge",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(target_student_id),
        summary=f"Merged student {source_name} into {target_name}",
        metadata={
            "source_student_id": source_student_id,
            "target_student_id": target_student_id,
            "source_display_name": source_name,
            "target_display_name": target_name,
            "source_return_code": source_code,
            "target_return_code": target_code,
            "submissions_moved": moved_submissions,
            "events_moved": moved_events,
        },
    )
    notice = (
        f"Merged {source_name} into {target_name}. "
        f"Moved {moved_submissions} submission(s) and {moved_events} event record(s)."
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_delete_student_data(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_roster(request.user, classroom):
        return HttpResponse("Forbidden", status=403)
    class_path = _teach_class_path(classroom.id)

    student_id = _parse_student_id(request.POST.get("student_id"))
    confirmed = (request.POST.get("confirm_delete") or "").strip() == "1"

    if not student_id:
        return _safe_internal_redirect(
            request, _with_notice(class_path, error="Invalid student selection."), fallback=class_path
        )
    if not confirmed:
        return _safe_internal_redirect(
            request, _with_notice(class_path, error="Confirm deletion before continuing."), fallback=class_path
        )

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if student is None:
        return _safe_internal_redirect(
            request, _with_notice(class_path, error="Student not found in this class."), fallback=class_path
        )

    submission_count = Submission.objects.filter(student=student).count()
    helper_clear = clear_helper_actor_conversations(
        class_id=classroom.id,
        student_id=student.id,
        endpoint_url=getattr(settings, "HELPER_INTERNAL_ACTOR_CLEAR_URL", ""),
        internal_token=getattr(settings, "HELPER_INTERNAL_API_TOKEN", ""),
        timeout_seconds=getattr(settings, "HELPER_INTERNAL_RESET_TIMEOUT_SECONDS", 2.0),
    )
    if not helper_clear.ok:
        return _safe_internal_redirect(
            request,
            _with_notice(
                class_path,
                error="Nothing was deleted because the helper service could not confirm its context clear. Retry deletion when the helper is available.",
            ),
            fallback=class_path,
        )
    deleted_history = delete_student_event_history(classroom_id=classroom.id, student_id=student.id)
    if not deleted_history.ok:
        return _safe_internal_redirect(
            request,
            _with_notice(
                class_path,
                error="Student records were not deleted because the activity-history store could not confirm deletion. Retry when it is available.",
            ),
            fallback=class_path,
        )
    student.delete()
    invalidate_classroom_submission_quota_cache(classroom_id=classroom.id)

    classroom.session_epoch = int(getattr(classroom, "session_epoch", 1) or 1) + 1
    classroom.save(update_fields=["session_epoch"])
    _audit(
        request,
        action="student.delete_data",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student_id),
        summary=f"Deleted student data for student_id={student_id}",
        metadata={
            "student_id": student_id,
            "submissions_deleted": submission_count,
            "core_student_events_deleted": deleted_history.core_events_deleted,
            "core_student_outcomes_deleted": deleted_history.core_outcomes_deleted,
            "telemetry_student_events_deleted": deleted_history.telemetry_events_deleted,
            "telemetry_student_outcomes_deleted": deleted_history.telemetry_outcomes_deleted,
            "session_epoch": classroom.session_epoch,
            "helper_context_clear_ok": helper_clear.ok,
            "helper_conversations_deleted": helper_clear.deleted_conversations,
        },
    )
    notice = (
        f"Deleted student data for student #{student_id}: "
        f"{submission_count} submission(s), {deleted_history.total_deleted} event record(s), "
        "and transient helper context cleared."
    )
    return _safe_internal_redirect(
        request, _with_notice(class_path, notice=notice), fallback=class_path
    )


__all__ = [
    "teach_merge_students",
    "teach_delete_student_data",
]
