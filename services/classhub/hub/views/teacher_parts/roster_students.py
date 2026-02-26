"""Teacher roster student-management endpoints."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .shared import (
    Class,
    HttpResponse,
    StudentEvent,
    StudentIdentity,
    Submission,
    _audit,
    _safe_internal_redirect,
    _teach_class_path,
    _with_notice,
    apply_no_store,
    require_POST,
    staff_member_required,
    transaction,
)

@staff_member_required
@require_GET
def teach_student_return_code(request, class_id: int, student_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if not student:
        return HttpResponse("Not found", status=404)

    response = JsonResponse({"return_code": student.return_code})
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_rename_student(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip())
    except Exception:
        student_id = 0
    new_name = (request.POST.get("display_name") or "").strip()[:80]
    if not student_id:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invalid student selection."),
            fallback=_teach_class_path(classroom.id),
        )
    if not new_name:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student name cannot be empty."),
            fallback=_teach_class_path(classroom.id),
        )

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student not found in this class."),
            fallback=_teach_class_path(classroom.id),
        )

    old_name = student.display_name
    if old_name == new_name:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), notice="No change applied to student name."),
            fallback=_teach_class_path(classroom.id),
        )

    student.display_name = new_name
    student.save(update_fields=["display_name"])
    _audit(
        request,
        action="student.rename",
        classroom=classroom,
        target_type="StudentIdentity",
        target_id=str(student.id),
        summary=f"Renamed student {old_name} -> {new_name}",
        metadata={"old_name": old_name, "new_name": new_name},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=f"Renamed student to {new_name}."),
        fallback=_teach_class_path(classroom.id),
    )


@staff_member_required
@require_POST
def teach_merge_students(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    try:
        source_student_id = int((request.POST.get("source_student_id") or "0").strip())
    except Exception:
        source_student_id = 0
    try:
        target_student_id = int((request.POST.get("target_student_id") or "0").strip())
    except Exception:
        target_student_id = 0
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
        source = StudentIdentity.objects.select_for_update().filter(
            id=source_student_id,
            classroom=classroom,
        ).first()
        target = StudentIdentity.objects.select_for_update().filter(
            id=target_student_id,
            classroom=classroom,
        ).first()

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
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    try:
        student_id = int((request.POST.get("student_id") or "0").strip())
    except Exception:
        student_id = 0
    confirmed = (request.POST.get("confirm_delete") or "").strip() == "1"

    if not student_id:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invalid student selection."),
            fallback=_teach_class_path(classroom.id),
        )
    if not confirmed:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Confirm deletion before continuing."),
            fallback=_teach_class_path(classroom.id),
        )

    student = StudentIdentity.objects.filter(id=student_id, classroom=classroom).first()
    if student is None:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Student not found in this class."),
            fallback=_teach_class_path(classroom.id),
        )

    submission_count = Submission.objects.filter(student=student).count()
    student_event_count = StudentEvent.objects.filter(student=student).count()
    student.delete()

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
            "student_events_detached": student_event_count,
            "session_epoch": classroom.session_epoch,
        },
    )
    notice = (
        f"Deleted student data for student #{student_id}: "
        f"{submission_count} submission(s), {student_event_count} event record(s) detached from student identity."
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )

__all__ = [
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
]
