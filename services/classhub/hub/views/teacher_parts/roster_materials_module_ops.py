"""Teacher module/material management endpoints."""

from ...services.content_links import is_supported_image_filename, parse_lesson_asset_download_url
from .roster_materials_module_support import build_image_asset_preview_map, populate_material_fields
from .shared import (
    HttpResponse,
    Material,
    Module,
    Submission,
    _apply_directional_reorder,
    _audit,
    _normalize_order,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _teach_class_path,
    _teach_module_path,
    _title_from_video_filename,
    _with_notice,
    models,
    render,
    require_POST,
    staff_can_access_classroom,
    staff_can_manage_classroom,
    staff_classroom_or_none,
    staff_member_required,
)

_ALLOWED_MATERIAL_TYPES = {
    Material.TYPE_LINK,
    Material.TYPE_TEXT,
    Material.TYPE_UPLOAD,
    Material.TYPE_GALLERY,
    Material.TYPE_CHECKLIST,
    Material.TYPE_REFLECTION,
    Material.TYPE_RUBRIC,
}


@staff_member_required
@require_POST
def teach_add_module(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

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
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

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
    if not staff_can_access_classroom(request.user, module.classroom):
        return HttpResponse("Not found", status=404)

    mats = list(module.materials.all())
    mats.sort(key=lambda m: (m.order_index, m.id))
    _normalize_order(mats)
    mats = list(module.materials.all())
    notice = (request.GET.get("notice") or "").strip()
    gallery_material_ids = [int(mat.id) for mat in mats if mat.type == Material.TYPE_GALLERY]
    gallery_artifacts_published = 0
    gallery_artifacts_approved = 0
    if gallery_material_ids:
        gallery_qs = Submission.objects.filter(material_id__in=gallery_material_ids)
        gallery_artifacts_published = gallery_qs.filter(is_published=True).count()
        gallery_artifacts_approved = gallery_qs.filter(is_gallery_shared=True).count()
    image_assets_by_material = build_image_asset_preview_map(materials=mats)

    return render(
        request,
        "teach_module.html",
        {
            "classroom": module.classroom,
            "module": module,
            "materials": mats,
            "notice": notice,
            "gallery_material_count": len(gallery_material_ids),
            "gallery_artifacts_published": gallery_artifacts_published,
            "gallery_artifacts_approved": gallery_artifacts_approved,
            "image_assets_by_material": image_assets_by_material,
        },
    )


@staff_member_required
@require_POST
def teach_add_material(request, module_id: int):
    module = Module.objects.select_related("classroom").filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, module.classroom):
        return HttpResponse("Forbidden", status=403)
    default_return = _teach_module_path(module.id)
    return_to = _safe_teacher_return_path((request.POST.get("return_to") or "").strip(), fallback=default_return)

    mtype = (request.POST.get("type") or Material.TYPE_LINK).strip()
    if mtype not in _ALLOWED_MATERIAL_TYPES:
        mtype = Material.TYPE_LINK
    title = (request.POST.get("title") or "").strip()[:200]
    if mtype == Material.TYPE_LINK and request.FILES.get("asset_file") and not title:
        title = _title_from_video_filename(getattr(request.FILES.get("asset_file"), "name", ""))[:200]
    if not title:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Enter a material title."),
            fallback=default_return,
        )
    if mtype == Material.TYPE_LINK and request.FILES.get("asset_file"):
        filename = (getattr(request.FILES.get("asset_file"), "name", "") or "").strip()
        if not is_supported_image_filename(filename):
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, error="Use PNG, JPG, GIF, or WEBP for lesson images."),
                fallback=default_return,
            )

    max_idx = module.materials.aggregate(models.Max("order_index")).get("order_index__max")
    order_index = int(max_idx) + 1 if max_idx is not None else 0

    mat = Material.objects.create(module=module, title=title, type=mtype, order_index=order_index)
    populate_material_fields(material=mat, request=request, material_type=mtype)
    asset_id = parse_lesson_asset_download_url(mat.url) if mtype == Material.TYPE_LINK else 0
    _audit(
        request,
        action="material.add",
        classroom=module.classroom,
        target_type="Material",
        target_id=str(mat.id),
        summary=f"Added material {mat.title}",
        metadata={"type": mtype, "module_id": module.id, "image_asset_id": asset_id or None},
    )

    return _safe_internal_redirect(
        request,
        _with_notice(return_to, notice=f"Added material: {mat.title}."),
        fallback=default_return,
    )


@staff_member_required
@require_POST
def teach_move_material(request, module_id: int):
    module = Module.objects.select_related("classroom").filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, module.classroom):
        return HttpResponse("Forbidden", status=403)

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


__all__ = [
    "teach_add_material",
    "teach_add_module",
    "teach_module",
    "teach_move_material",
    "teach_move_module",
]
