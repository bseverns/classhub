"""Teacher class, roster, module, and submission endpoints."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

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
    lesson_rows = _build_lesson_tracker_rows(request, classroom.id, modules, student_count)
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
    StudentEvent.objects.filter(student=student).delete()
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
            "student_events_deleted": student_event_count,
            "session_epoch": classroom.session_epoch,
        },
    )
    notice = (
        f"Deleted student data for student #{student_id}: "
        f"{submission_count} submission(s), {student_event_count} event record(s)."
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice=notice),
        fallback=_teach_class_path(classroom.id),
    )


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


@staff_member_required
@require_POST
def teach_add_module(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    title = (request.POST.get("title") or "").strip()[:200]
    if not title:
        return _safe_internal_redirect(request, _teach_class_path(classroom.id), fallback="/teach")

    max_idx = classroom.modules.aggregate(models.Max("order_index")).get("order_index__max")
    order_index = int(max_idx) + 1 if max_idx is not None else 0

    mod = Module.objects.create(classroom=classroom, title=title, order_index=order_index)
    _audit(
        request,
        action="module.add",
        classroom=classroom,
        target_type="Module",
        target_id=str(mod.id),
        summary=f"Added module {mod.title}",
        metadata={"order_index": order_index},
    )
    return _safe_internal_redirect(request, _teach_module_path(mod.id), fallback=_teach_class_path(classroom.id))


@staff_member_required
@require_POST
def teach_move_module(request, class_id: int):
    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return HttpResponse("Not found", status=404)

    module_id = int(request.POST.get("module_id") or 0)
    direction = (request.POST.get("direction") or "").strip()

    modules = list(classroom.modules.all())
    modules.sort(key=lambda m: (m.order_index, m.id))

    if not _apply_directional_reorder(modules, target_id=module_id, direction=direction):
        return _safe_internal_redirect(request, _teach_class_path(classroom.id), fallback="/teach")
    _audit(
        request,
        action="module.reorder",
        classroom=classroom,
        target_type="Module",
        target_id=str(module_id),
        summary=f"Reordered module {module_id}",
        metadata={"direction": direction},
    )

    return _safe_internal_redirect(request, _teach_class_path(classroom.id), fallback="/teach")


@staff_member_required
def teach_module(request, module_id: int):
    module = Module.objects.select_related("classroom").prefetch_related("materials").filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)

    mats = list(module.materials.all())
    mats.sort(key=lambda m: (m.order_index, m.id))
    _normalize_order(mats)
    mats = list(module.materials.all())

    return render(
        request,
        "teach_module.html",
        {
            "classroom": module.classroom,
            "module": module,
            "materials": mats,
        },
    )


@staff_member_required
@require_POST
def teach_add_material(request, module_id: int):
    module = Module.objects.select_related("classroom").filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)

    mtype = (request.POST.get("type") or Material.TYPE_LINK).strip()
    title = (request.POST.get("title") or "").strip()[:200]
    if not title:
        return _safe_internal_redirect(request, _teach_module_path(module.id), fallback=_teach_class_path(module.classroom_id))

    max_idx = module.materials.aggregate(models.Max("order_index")).get("order_index__max")
    order_index = int(max_idx) + 1 if max_idx is not None else 0

    mat = Material.objects.create(module=module, title=title, type=mtype, order_index=order_index)

    if mtype == Material.TYPE_LINK:
        mat.url = (request.POST.get("url") or "").strip()
        mat.save(update_fields=["url"])
    elif mtype == Material.TYPE_TEXT:
        mat.body = (request.POST.get("body") or "").strip()
        mat.save(update_fields=["body"])
    elif mtype == Material.TYPE_UPLOAD:
        mat.accepted_extensions = (request.POST.get("accepted_extensions") or ".sb3").strip()
        try:
            mat.max_upload_mb = int(request.POST.get("max_upload_mb") or 50)
        except Exception:
            mat.max_upload_mb = 50
        mat.save(update_fields=["accepted_extensions", "max_upload_mb"])
    _audit(
        request,
        action="material.add",
        classroom=module.classroom,
        target_type="Material",
        target_id=str(mat.id),
        summary=f"Added material {mat.title}",
        metadata={"type": mtype, "module_id": module.id},
    )

    return _safe_internal_redirect(request, _teach_module_path(module.id), fallback=_teach_class_path(module.classroom_id))


@staff_member_required
@require_POST
def teach_move_material(request, module_id: int):
    module = Module.objects.filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)

    material_id = int(request.POST.get("material_id") or 0)
    direction = (request.POST.get("direction") or "").strip()

    mats = list(module.materials.all())
    mats.sort(key=lambda m: (m.order_index, m.id))

    if not _apply_directional_reorder(mats, target_id=material_id, direction=direction):
        return _safe_internal_redirect(request, _teach_module_path(module.id), fallback=_teach_class_path(module.classroom_id))
    _audit(
        request,
        action="material.reorder",
        classroom=module.classroom,
        target_type="Material",
        target_id=str(material_id),
        summary=f"Reordered material {material_id}",
        metadata={"direction": direction, "module_id": module.id},
    )

    return _safe_internal_redirect(request, _teach_module_path(module.id), fallback=_teach_class_path(module.classroom_id))


@staff_member_required
def teach_material_submissions(request, material_id: int):
    material = (
        Material.objects.select_related("module__classroom")
        .filter(id=material_id)
        .first()
    )
    if not material or material.type != Material.TYPE_UPLOAD:
        return HttpResponse("Not found", status=404)

    classroom = material.module.classroom
    students = list(classroom.students.all().order_by("created_at", "id"))

    all_subs = list(
        Submission.objects.filter(material=material)
        .select_related("student")
        .order_by("-uploaded_at", "-id")
    )

    latest_by_student = {}
    count_by_student = {}
    for s in all_subs:
        sid = s.student_id
        count_by_student[sid] = count_by_student.get(sid, 0) + 1
        if sid not in latest_by_student:
            latest_by_student[sid] = s

    show = (request.GET.get("show") or "all").strip()

    if request.GET.get("download") == "zip_latest":
        with _temporary_zip_archive() as (tmp, z):
            for st in students:
                s = latest_by_student.get(st.id)
                if not s:
                    continue
                base_name = safe_filename(st.display_name)
                orig = safe_filename(s.original_filename or Path(s.file.name).name)
                arc = f"{base_name}/{orig}"
                if not _write_submission_file_to_archive(
                    z,
                    submission=s,
                    arcname=arc,
                    allow_file_fallback=False,
                ):
                    continue

        download_name = safe_attachment_filename(
            f"{safe_filename(classroom.name)}_material_{material.id}_latest.zip"
        )
        tmp.seek(0)
        response = FileResponse(
            tmp,
            as_attachment=True,
            filename=download_name,
            content_type="application/zip",
        )
        apply_download_safety(response)
        apply_no_store(response, private=True, pragma=True)
        return response

    rows = []
    missing = 0
    for st in students:
        latest = latest_by_student.get(st.id)
        c = count_by_student.get(st.id, 0)
        if not latest:
            missing += 1
        rows.append(
            {
                "student": st,
                "latest": latest,
                "count": c,
            }
        )

    if show == "missing":
        rows = [r for r in rows if r["latest"] is None]
    elif show == "submitted":
        rows = [r for r in rows if r["latest"] is not None]

    return render(
        request,
        "teach_material_submissions.html",
        {
            "classroom": classroom,
            "module": material.module,
            "material": material,
            "rows": rows,
            "missing": missing,
            "student_count": len(students),
            "show": show,
        },
    )



__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
    "teach_add_module",
    "teach_move_module",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
