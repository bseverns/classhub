"""Teacher module/material helper routines."""

from ...services.content_links import (
    build_asset_url,
    is_supported_image_filename,
    parse_course_lesson_url,
    parse_lesson_asset_download_url,
)
from .shared import (
    LessonAsset,
    LessonAssetFolder,
    Material,
    Module,
    _normalize_optional_slug_tag,
)

_MODULE_IMAGE_FOLDER_PATH = "lesson-images"


def _module_lesson_tags(module: Module) -> tuple[str, str]:
    for item in module.materials.all():
        if item.type != Material.TYPE_LINK:
            continue
        parsed = parse_course_lesson_url(item.url)
        if parsed:
            return parsed
    return "", ""


def _default_module_image_folder() -> LessonAssetFolder:
    folder, _created = LessonAssetFolder.objects.get_or_create(
        path=_MODULE_IMAGE_FOLDER_PATH,
        defaults={"display_name": "Lesson images"},
    )
    return folder


def _create_image_asset_for_module(*, module: Module, request, title: str) -> tuple[LessonAsset | None, str]:
    file_obj = request.FILES.get("asset_file")
    if not file_obj:
        return None, "Choose an image file to upload."

    original_filename = (getattr(file_obj, "name", "") or "").strip()
    if not is_supported_image_filename(original_filename):
        return None, "Use PNG, JPG, GIF, or WEBP for lesson images."

    folder = _default_module_image_folder()
    course_slug, lesson_slug = _module_lesson_tags(module)
    asset = LessonAsset.objects.create(
        folder=folder,
        course_slug=_normalize_optional_slug_tag(course_slug),
        lesson_slug=_normalize_optional_slug_tag(lesson_slug),
        title=title[:200],
        description=(request.POST.get("asset_description") or "").strip(),
        original_filename=original_filename[:255],
        file=file_obj,
        is_active=True,
    )
    return asset, ""


def build_image_asset_preview_map(*, materials: list[Material]) -> dict[int, dict]:
    by_material: dict[int, int] = {}
    asset_ids: list[int] = []
    for material in materials:
        if material.type != Material.TYPE_LINK:
            continue
        asset_id = parse_lesson_asset_download_url(material.url)
        if not asset_id:
            continue
        by_material[material.id] = asset_id
        asset_ids.append(asset_id)
    if not asset_ids:
        return {}

    assets = {
        asset.id: asset
        for asset in LessonAsset.objects.filter(id__in=asset_ids).only(
            "id",
            "title",
            "description",
            "original_filename",
            "file",
        )
    }
    preview_map: dict[int, dict] = {}
    for material_id, asset_id in by_material.items():
        asset = assets.get(asset_id)
        if asset is None:
            continue
        filename = asset.original_filename or getattr(asset.file, "name", "")
        if not is_supported_image_filename(filename):
            continue
        preview_map[material_id] = {
            "asset_id": asset.id,
            "src": build_asset_url(f"/lesson-asset/{asset.id}/download"),
            "title": asset.title,
            "description": asset.description or "",
            "original_filename": filename,
        }
    return preview_map


def populate_material_fields(*, material: Material, request, material_type: str) -> None:
    if material_type == Material.TYPE_LINK:
        image_asset, image_error = _create_image_asset_for_module(
            module=material.module,
            request=request,
            title=material.title,
        )
        if image_error:
            image_asset = None
        if image_asset is not None:
            material.url = f"/lesson-asset/{image_asset.id}/download"
            material.save(update_fields=["url"])
            return
        material.url = (request.POST.get("url") or "").strip()
        material.save(update_fields=["url"])
    elif material_type == Material.TYPE_TEXT:
        material.body = (request.POST.get("body") or "").strip()
        material.save(update_fields=["body"])
    elif material_type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
        default_exts = ".sb3" if material_type == Material.TYPE_UPLOAD else ".png,.jpg,.jpeg,.webp,.gif,.pdf,.sb3"
        material.accepted_extensions = (request.POST.get("accepted_extensions") or default_exts).strip()
        try:
            material.max_upload_mb = int(request.POST.get("max_upload_mb") or 50)
        except Exception:
            material.max_upload_mb = 50
        material.save(update_fields=["accepted_extensions", "max_upload_mb"])
    elif material_type in {Material.TYPE_CHECKLIST, Material.TYPE_REFLECTION}:
        prompt_key = "checklist_items" if material_type == Material.TYPE_CHECKLIST else "reflection_prompt"
        material.body = (request.POST.get(prompt_key) or "").strip()
        material.save(update_fields=["body"])
    elif material_type == Material.TYPE_RUBRIC:
        material.body = (request.POST.get("rubric_criteria") or "").strip()
        try:
            material.rubric_scale_max = max(2, min(int(request.POST.get("rubric_scale_max") or 4), 10))
        except Exception:
            material.rubric_scale_max = 4
        material.save(update_fields=["body", "rubric_scale_max"])
