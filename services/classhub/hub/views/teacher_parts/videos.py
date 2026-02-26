"""Teacher lesson video and asset endpoints."""

from .shared import (
    IntegrityError,
    LessonAsset,
    LessonAssetFolder,
    LessonVideo,
    OperationalError,
    ProgrammingError,
    _audit,
    _lesson_asset_redirect_params,
    _lesson_video_redirect_params,
    _next_lesson_video_order,
    _normalize_optional_slug_tag,
    _safe_internal_redirect,
    _title_from_video_filename,
    build_asset_url,
    iter_course_lesson_options,
    render,
    staff_member_required,
)


@staff_member_required
def teach_videos(request):
    try:
        class_id = int((request.GET.get("class_id") or request.POST.get("class_id") or "0").strip())
    except Exception:
        class_id = 0

    all_options = iter_course_lesson_options()
    by_course: dict[str, dict] = {}
    for row in all_options:
        course_slug = row["course_slug"]
        if course_slug not in by_course:
            by_course[course_slug] = {
                "course_slug": course_slug,
                "course_title": row["course_title"],
                "lessons": [],
            }
        by_course[course_slug]["lessons"].append(
            {
                "lesson_slug": row["lesson_slug"],
                "lesson_title": row["lesson_title"],
                "session": row["session"],
            }
        )

    course_rows = list(by_course.values())
    course_rows.sort(key=lambda c: (c["course_title"].lower(), c["course_slug"]))
    for course_row in course_rows:
        course_row["lessons"].sort(key=lambda l: ((l["session"] or 0), l["lesson_title"].lower(), l["lesson_slug"]))

    selected_course_slug = (request.GET.get("course_slug") or request.POST.get("course_slug") or "").strip()
    if not selected_course_slug and course_rows:
        selected_course_slug = course_rows[0]["course_slug"]

    selected_course = next((c for c in course_rows if c["course_slug"] == selected_course_slug), None)
    lesson_rows = selected_course["lessons"] if selected_course else []
    selected_lesson_slug = (request.GET.get("lesson_slug") or request.POST.get("lesson_slug") or "").strip()
    if not selected_lesson_slug and lesson_rows:
        selected_lesson_slug = lesson_rows[0]["lesson_slug"]

    notice = (request.GET.get("notice") or "").strip()
    error = ""

    try:
        LessonVideo.objects.only("id").first()
        lesson_video_table_available = True
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonvideo" in str(exc).lower():
            lesson_video_table_available = False
        else:
            raise

    if not lesson_video_table_available:
        class_back_link = f"/teach/class/{class_id}" if class_id else "/teach/lessons"
        return render(
            request,
            "teach_videos.html",
            {
                "course_rows": course_rows,
                "selected_course_slug": selected_course_slug,
                "selected_lesson_slug": selected_lesson_slug,
                "lesson_rows": lesson_rows,
                "lesson_video_rows": [],
                "published_count": 0,
                "draft_count": 0,
                "class_id": class_id,
                "class_back_link": class_back_link,
                "notice": notice,
                "error": "Lesson video table is missing. Run `python manage.py migrate` in `classhub_web`.",
            },
        )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if not selected_course_slug or not selected_lesson_slug:
            error = "Select a course + lesson first."
        elif action == "add":
            title = (request.POST.get("title") or "").strip()[:200]
            minutes_raw = (request.POST.get("minutes") or "").strip()
            outcome = (request.POST.get("outcome") or "").strip()[:300]
            source_url = (request.POST.get("source_url") or "").strip()
            video_file = request.FILES.get("video_file")
            is_active = (request.POST.get("is_active") or "1").strip() == "1"

            if not title:
                error = "Title is required."
            elif not source_url and not video_file:
                error = "Provide either a video URL or upload a video file."
            elif source_url and video_file:
                error = "Use URL or file upload, not both."
            else:
                minutes = None
                if minutes_raw:
                    try:
                        minutes = max(int(minutes_raw), 0)
                    except Exception:
                        error = "Minutes must be a whole number."

                if not error:
                    row = LessonVideo.objects.create(
                        course_slug=selected_course_slug,
                        lesson_slug=selected_lesson_slug,
                        title=title,
                        minutes=minutes,
                        outcome=outcome,
                        source_url=source_url,
                        video_file=video_file,
                        order_index=_next_lesson_video_order(selected_course_slug, selected_lesson_slug),
                        is_active=is_active,
                    )
                    _audit(
                        request,
                        action="lesson_video.add",
                        target_type="LessonVideo",
                        target_id=str(row.id),
                        summary=f"Added lesson video {selected_course_slug}/{selected_lesson_slug}",
                        metadata={"course_slug": selected_course_slug, "lesson_slug": selected_lesson_slug, "is_active": is_active},
                    )
                    notice = "Video saved." if is_active else "Video saved as draft."
        elif action == "bulk_upload":
            files = [f for f in request.FILES.getlist("video_files") if (getattr(f, "name", "") or "").strip()]
            title_prefix = (request.POST.get("title_prefix") or "").strip()[:80]
            is_active = (request.POST.get("bulk_is_active") or "1").strip() == "1"

            if not files:
                error = "Select one or more video files to upload."
            else:
                next_order = _next_lesson_video_order(selected_course_slug, selected_lesson_slug)
                added = 0
                for file_obj in files:
                    file_title = _title_from_video_filename(file_obj.name)
                    if title_prefix:
                        file_title = f"{title_prefix}: {file_title}"[:200]
                    row = LessonVideo.objects.create(
                        course_slug=selected_course_slug,
                        lesson_slug=selected_lesson_slug,
                        title=file_title,
                        source_url="",
                        video_file=file_obj,
                        order_index=next_order,
                        is_active=is_active,
                    )
                    _audit(
                        request,
                        action="lesson_video.bulk_add_item",
                        target_type="LessonVideo",
                        target_id=str(row.id),
                        summary=f"Bulk uploaded lesson video {selected_course_slug}/{selected_lesson_slug}",
                        metadata={"course_slug": selected_course_slug, "lesson_slug": selected_lesson_slug, "is_active": is_active},
                    )
                    next_order += 1
                    added += 1
                status_label = "published" if is_active else "draft"
                notice = f"Uploaded {added} video file(s) as {status_label}."
        elif action == "delete":
            try:
                video_id = int(request.POST.get("video_id") or 0)
            except Exception:
                video_id = 0
            item = LessonVideo.objects.filter(
                id=video_id,
                course_slug=selected_course_slug,
                lesson_slug=selected_lesson_slug,
            ).first()
            if item:
                item_id = item.id
                item.delete()
                _audit(
                    request,
                    action="lesson_video.delete",
                    target_type="LessonVideo",
                    target_id=str(item_id),
                    summary=f"Removed lesson video {selected_course_slug}/{selected_lesson_slug}",
                    metadata={"course_slug": selected_course_slug, "lesson_slug": selected_lesson_slug},
                )
                notice = "Video removed."
        elif action == "set_active":
            try:
                video_id = int(request.POST.get("video_id") or 0)
            except Exception:
                video_id = 0
            should_be_active = (request.POST.get("active") or "0").strip() == "1"
            item = LessonVideo.objects.filter(
                id=video_id,
                course_slug=selected_course_slug,
                lesson_slug=selected_lesson_slug,
            ).first()
            if item:
                item.is_active = should_be_active
                item.save(update_fields=["is_active", "updated_at"])
                _audit(
                    request,
                    action="lesson_video.set_active",
                    target_type="LessonVideo",
                    target_id=str(item.id),
                    summary=f"Set lesson video active={should_be_active}",
                    metadata={"course_slug": selected_course_slug, "lesson_slug": selected_lesson_slug, "is_active": should_be_active},
                )
                notice = "Video published." if should_be_active else "Video moved to draft."
        elif action == "move":
            try:
                video_id = int(request.POST.get("video_id") or 0)
            except Exception:
                video_id = 0
            direction = (request.POST.get("direction") or "").strip()
            rows = list(
                LessonVideo.objects.filter(course_slug=selected_course_slug, lesson_slug=selected_lesson_slug)
                .order_by("order_index", "id")
            )
            idx = next((i for i, row in enumerate(rows) if row.id == video_id), None)
            if idx is not None:
                if direction == "up" and idx > 0:
                    rows[idx - 1], rows[idx] = rows[idx], rows[idx - 1]
                elif direction == "down" and idx < len(rows) - 1:
                    rows[idx + 1], rows[idx] = rows[idx], rows[idx + 1]
                for i, row in enumerate(rows):
                    if row.order_index != i:
                        row.order_index = i
                        row.save(update_fields=["order_index"])
                _audit(
                    request,
                    action="lesson_video.reorder",
                    target_type="LessonVideo",
                    target_id=str(video_id),
                    summary=f"Reordered lesson videos for {selected_course_slug}/{selected_lesson_slug}",
                    metadata={"course_slug": selected_course_slug, "lesson_slug": selected_lesson_slug, "direction": direction},
                )
                notice = "Video order updated."

        if not error:
            query = _lesson_video_redirect_params(selected_course_slug, selected_lesson_slug, class_id, notice)
            return _safe_internal_redirect(request, f"/teach/videos?{query}", fallback="/teach/videos")

    lesson_video_rows = list(
        LessonVideo.objects.filter(course_slug=selected_course_slug, lesson_slug=selected_lesson_slug)
        .order_by("order_index", "id")
    ) if selected_course_slug and selected_lesson_slug else []
    for row in lesson_video_rows:
        row.stream_url = build_asset_url(f"/lesson-video/{row.id}/stream")
    published_count = sum(1 for row in lesson_video_rows if row.is_active)
    draft_count = max(len(lesson_video_rows) - published_count, 0)

    class_back_link = f"/teach/class/{class_id}" if class_id else "/teach/lessons"
    return render(
        request,
        "teach_videos.html",
        {
            "course_rows": course_rows,
            "selected_course_slug": selected_course_slug,
            "selected_lesson_slug": selected_lesson_slug,
            "lesson_rows": lesson_rows,
            "lesson_video_rows": lesson_video_rows,
            "published_count": published_count,
            "draft_count": draft_count,
            "class_id": class_id,
            "class_back_link": class_back_link,
            "notice": notice,
            "error": error,
        },
    )


@staff_member_required
def teach_assets(request):
    """Teacher-managed reference file library with optional lesson tags."""
    try:
        selected_folder_id = int((request.GET.get("folder_id") or request.POST.get("folder_id") or "0").strip())
    except Exception:
        selected_folder_id = 0

    selected_course_slug = _normalize_optional_slug_tag(
        (request.GET.get("course_slug") or request.POST.get("course_slug") or "").strip()
    )
    selected_lesson_slug = _normalize_optional_slug_tag(
        (request.GET.get("lesson_slug") or request.POST.get("lesson_slug") or "").strip()
    )
    status = (request.GET.get("status") or request.POST.get("status") or "all").strip().lower()
    if status not in {"all", "active", "inactive"}:
        status = "all"

    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()

    try:
        LessonAssetFolder.objects.only("id").first()
        LessonAsset.objects.only("id").first()
        lesson_asset_tables_available = True
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonasset" in str(exc).lower():
            lesson_asset_tables_available = False
        else:
            raise

    if not lesson_asset_tables_available:
        return render(
            request,
            "teach_assets.html",
            {
                "folder_rows": [],
                "asset_rows": [],
                "selected_folder_id": selected_folder_id,
                "selected_course_slug": selected_course_slug,
                "selected_lesson_slug": selected_lesson_slug,
                "status": status,
                "active_count": 0,
                "inactive_count": 0,
                "notice": notice,
                "error": "Lesson asset tables are missing. Run `python manage.py migrate` in `classhub_web`.",
            },
        )

    folder_rows = list(LessonAssetFolder.objects.all().order_by("path", "id"))
    if not any(row.id == selected_folder_id for row in folder_rows):
        selected_folder_id = 0

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "create_folder":
            folder_path = (request.POST.get("folder_path") or "").strip()
            display_name = (request.POST.get("display_name") or "").strip()[:120]
            if not folder_path:
                error = "Folder path is required."
            else:
                folder = LessonAssetFolder(path=folder_path, display_name=display_name)
                try:
                    folder.save()
                except IntegrityError:
                    error = "That folder path already exists."
                else:
                    selected_folder_id = folder.id
                    _audit(
                        request,
                        action="lesson_asset_folder.create",
                        target_type="LessonAssetFolder",
                        target_id=str(folder.id),
                        summary=f"Created lesson asset folder {folder.path}",
                        metadata={"path": folder.path},
                    )
                    notice = f"Folder created: {folder.path}"

        elif action == "upload":
            try:
                upload_folder_id = int((request.POST.get("folder_id") or "0").strip())
            except Exception:
                upload_folder_id = 0
            folder = LessonAssetFolder.objects.filter(id=upload_folder_id).first()
            file_obj = request.FILES.get("asset_file")
            title = (request.POST.get("title") or "").strip()[:200]
            description = (request.POST.get("description") or "").strip()
            upload_course_slug = _normalize_optional_slug_tag((request.POST.get("course_slug") or "").strip())
            upload_lesson_slug = _normalize_optional_slug_tag((request.POST.get("lesson_slug") or "").strip())
            is_active = (request.POST.get("is_active") or "1").strip() == "1"

            if folder is None:
                error = "Select a folder before uploading."
            elif not file_obj:
                error = "Choose a file to upload."
            else:
                if not title:
                    title = _title_from_video_filename(getattr(file_obj, "name", ""))[:200]
                row = LessonAsset.objects.create(
                    folder=folder,
                    course_slug=upload_course_slug,
                    lesson_slug=upload_lesson_slug,
                    title=title,
                    description=description,
                    original_filename=(getattr(file_obj, "name", "") or "")[:255],
                    file=file_obj,
                    is_active=is_active,
                )
                _audit(
                    request,
                    action="lesson_asset.upload",
                    target_type="LessonAsset",
                    target_id=str(row.id),
                    summary=f"Uploaded lesson asset {row.title}",
                    metadata={
                        "folder": folder.path,
                        "course_slug": upload_course_slug,
                        "lesson_slug": upload_lesson_slug,
                        "is_active": is_active,
                    },
                )
                selected_folder_id = folder.id
                selected_course_slug = upload_course_slug
                selected_lesson_slug = upload_lesson_slug
                notice = "Asset uploaded."

        elif action == "set_active":
            try:
                asset_id = int((request.POST.get("asset_id") or "0").strip())
            except Exception:
                asset_id = 0
            should_be_active = (request.POST.get("active") or "0").strip() == "1"
            item = LessonAsset.objects.select_related("folder").filter(id=asset_id).first()
            if item:
                item.is_active = should_be_active
                item.save(update_fields=["is_active", "updated_at"])
                _audit(
                    request,
                    action="lesson_asset.set_active",
                    target_type="LessonAsset",
                    target_id=str(item.id),
                    summary=f"Set lesson asset active={should_be_active}",
                    metadata={"folder": item.folder.path, "is_active": should_be_active},
                )
                notice = "Asset is now visible to students." if should_be_active else "Asset moved to hidden draft."
                selected_folder_id = item.folder_id

        elif action == "delete":
            try:
                asset_id = int((request.POST.get("asset_id") or "0").strip())
            except Exception:
                asset_id = 0
            item = LessonAsset.objects.select_related("folder").filter(id=asset_id).first()
            if item:
                selected_folder_id = item.folder_id
                item_id = item.id
                folder_path = item.folder.path
                item.delete()
                _audit(
                    request,
                    action="lesson_asset.delete",
                    target_type="LessonAsset",
                    target_id=str(item_id),
                    summary="Deleted lesson asset",
                    metadata={"folder": folder_path},
                )
                notice = "Asset deleted."

        else:
            error = "Unknown action."

        if not error:
            query = _lesson_asset_redirect_params(
                folder_id=selected_folder_id,
                course_slug=selected_course_slug,
                lesson_slug=selected_lesson_slug,
                status=status,
                notice=notice,
            )
            return _safe_internal_redirect(request, f"/teach/assets?{query}", fallback="/teach/assets")

    asset_qs = LessonAsset.objects.select_related("folder").all()
    if selected_folder_id:
        asset_qs = asset_qs.filter(folder_id=selected_folder_id)
    if selected_course_slug:
        asset_qs = asset_qs.filter(course_slug=selected_course_slug)
    if selected_lesson_slug:
        asset_qs = asset_qs.filter(lesson_slug=selected_lesson_slug)
    if status == "active":
        asset_qs = asset_qs.filter(is_active=True)
    elif status == "inactive":
        asset_qs = asset_qs.filter(is_active=False)
    asset_rows = list(asset_qs.order_by("folder__path", "-updated_at", "id"))
    for row in asset_rows:
        row.download_url = build_asset_url(f"/lesson-asset/{row.id}/download")

    active_count = sum(1 for row in asset_rows if row.is_active)
    inactive_count = max(len(asset_rows) - active_count, 0)

    return render(
        request,
        "teach_assets.html",
        {
            "folder_rows": folder_rows,
            "asset_rows": asset_rows,
            "selected_folder_id": selected_folder_id,
            "selected_course_slug": selected_course_slug,
            "selected_lesson_slug": selected_lesson_slug,
            "status": status,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "notice": notice,
            "error": error,
        },
    )

__all__ = [
    "teach_videos",
    "teach_assets",
]
