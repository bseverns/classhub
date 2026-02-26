"""Teacher class-level roster and dashboard endpoints."""

from .shared import *  # noqa: F401,F403,F405

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

    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda m: (m.order_index, m.id))
    _normalize_order(modules)
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda m: (m.order_index, m.id))

    upload_material_ids = []
    for m in modules:
        for mat in m.materials.all():
            if mat.type == Material.TYPE_UPLOAD:
                upload_material_ids.append(mat.id)

    submission_counts = {}
    if upload_material_ids:
        qs = (
            Submission.objects.filter(material_id__in=upload_material_ids)
            .values("material_id", "student_id")
            .distinct()
        )
        for row in qs:
            submission_counts[row["material_id"]] = submission_counts.get(row["material_id"], 0) + 1

    student_count = classroom.students.count()
    students = list(classroom.students.all().order_by("created_at", "id"))
    lesson_rows = _build_lesson_tracker_rows(
        request,
        classroom.id,
        modules,
        student_count,
        class_session_epoch=classroom.session_epoch,
    )
    helper_signals = _build_helper_signal_snapshot(
        classroom=classroom,
        students=students,
        window_hours=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_WINDOW_HOURS", 24) or 24), 1),
        top_students=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_TOP_STUDENTS", 5) or 5), 1),
    )
    submission_counts_by_student: dict[int, int] = {}
    if students:
        rows = (
            Submission.objects.filter(student__classroom=classroom)
            .values("student_id")
            .annotate(total=models.Count("id"))
        )
        for row in rows:
            submission_counts_by_student[int(row["student_id"])] = int(row["total"])
    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()

    response = render(
        request,
        "teach_class.html",
        {
            "classroom": classroom,
            "modules": modules,
            "student_count": student_count,
            "students": students,
            "submission_counts": submission_counts,
            "submission_counts_by_student": submission_counts_by_student,
            "lesson_rows": lesson_rows,
            "helper_signals": helper_signals,
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
    rows = list(
        Submission.objects.filter(
            student__classroom=classroom,
            uploaded_at__gte=day_start,
            uploaded_at__lt=day_end,
        )
        .select_related("student", "material")
        .order_by("student__display_name", "material__title", "uploaded_at", "id")
    )

    file_count = 0
    used_paths: set[str] = set()
    with _temporary_zip_archive() as (tmp, archive):
        for sub in rows:
            student_name = safe_filename(sub.student.display_name)
            material_name = safe_filename(sub.material.title)
            original = safe_filename(sub.original_filename or Path(sub.file.name).name)
            stamp = timezone.localtime(sub.uploaded_at).strftime("%H%M%S")
            candidate = _reserve_archive_path(
                f"{student_name}/{material_name}/{stamp}_{original}",
                used_paths,
                fallback=f"{student_name}/{material_name}/{stamp}_{sub.id}_{original}",
            )
            if not _write_submission_file_to_archive(
                archive,
                submission=sub,
                arcname=candidate,
                allow_file_fallback=False,
            ):
                continue
            file_count += 1
        if file_count == 0:
            archive.writestr(
                "README.txt",
                (
                    "No submission files were available for this class today.\n"
                    "This can happen when there were no uploads or file sources were unavailable.\n"
                ),
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
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
]
