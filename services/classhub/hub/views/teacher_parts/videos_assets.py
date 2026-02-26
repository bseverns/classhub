"""Teacher lesson asset management endpoints."""

from .shared import (
    IntegrityError,
    LessonAsset,
    LessonAssetFolder,
    OperationalError,
    ProgrammingError,
    _audit,
    _lesson_asset_redirect_params,
    _normalize_optional_slug_tag,
    _safe_internal_redirect,
    _title_from_video_filename,
    build_asset_url,
    render,
    staff_member_required,
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


__all__ = ["teach_assets"]
