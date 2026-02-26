"""Teacher module/material/submission endpoints."""

from .shared import (
    FileResponse,
    HttpResponse,
    Material,
    Module,
    Path,
    Submission,
    _apply_directional_reorder,
    _audit,
    _normalize_order,
    _safe_internal_redirect,
    _teach_class_path,
    _teach_module_path,
    _temporary_zip_archive,
    _write_submission_file_to_archive,
    apply_download_safety,
    apply_no_store,
    models,
    render,
    require_POST,
    safe_attachment_filename,
    safe_filename,
    staff_can_access_classroom,
    staff_can_manage_classroom,
    staff_classroom_or_none,
    staff_member_required,
)
from ...services.teacher_material_reviews import build_rubric_material_rows

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
    if not staff_can_manage_classroom(request.user, module.classroom):
        return HttpResponse("Forbidden", status=403)

    allowed_types = {Material.TYPE_LINK, Material.TYPE_TEXT, Material.TYPE_UPLOAD, Material.TYPE_GALLERY, Material.TYPE_CHECKLIST, Material.TYPE_REFLECTION, Material.TYPE_RUBRIC}
    mtype = (request.POST.get("type") or Material.TYPE_LINK).strip()
    if mtype not in allowed_types:
        mtype = Material.TYPE_LINK
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
    elif mtype in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
        default_exts = ".sb3" if mtype == Material.TYPE_UPLOAD else ".png,.jpg,.jpeg,.webp,.gif,.pdf,.sb3"
        mat.accepted_extensions = (request.POST.get("accepted_extensions") or default_exts).strip()
        try:
            mat.max_upload_mb = int(request.POST.get("max_upload_mb") or 50)
        except Exception:
            mat.max_upload_mb = 50
        mat.save(update_fields=["accepted_extensions", "max_upload_mb"])
    elif mtype in {Material.TYPE_CHECKLIST, Material.TYPE_REFLECTION}:
        prompt_key = "checklist_items" if mtype == Material.TYPE_CHECKLIST else "reflection_prompt"
        mat.body = (request.POST.get(prompt_key) or "").strip()
        mat.save(update_fields=["body"])
    elif mtype == Material.TYPE_RUBRIC:
        mat.body = (request.POST.get("rubric_criteria") or "").strip()
        try:
            mat.rubric_scale_max = max(2, min(int(request.POST.get("rubric_scale_max") or 4), 10))
        except Exception:
            mat.rubric_scale_max = 4
        mat.save(update_fields=["body", "rubric_scale_max"])
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


@staff_member_required
def teach_material_submissions(request, material_id: int):
    material = (
        Material.objects.select_related("module__classroom")
        .filter(id=material_id)
        .first()
    )
    if not material or material.type not in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY, Material.TYPE_RUBRIC}:
        return HttpResponse("Not found", status=404)

    classroom = material.module.classroom
    if not staff_can_access_classroom(request.user, classroom):
        return HttpResponse("Not found", status=404)
    students = list(classroom.students.all().order_by("created_at", "id"))

    all_subs = []
    if material.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
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
    if material.type == Material.TYPE_RUBRIC:
        rows, missing = build_rubric_material_rows(material=material, students=students, show=show)
        return render(
            request,
            "teach_material_submissions.html",
            {
                "classroom": classroom,
                "module": material.module,
                "material": material,
                "rows": rows,
                "student_count": len(students),
                "missing": missing,
                "show": show,
                "is_rubric": True,
            },
        )

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
    "teach_add_module",
    "teach_move_module",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
