"""Teacher gallery moderation/session controls."""

from .shared import (
    HttpResponse,
    Material,
    Module,
    Submission,
    _audit,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _teach_class_path,
    _teach_module_path,
    _with_notice,
    require_POST,
    staff_can_delete_submissions,
    staff_can_manage_policy,
    staff_member_required,
    timezone,
)


@staff_member_required
@require_POST
def teach_set_module_gallery_enabled(request, module_id: int):
    module = Module.objects.select_related("classroom").filter(id=module_id).first()
    if not module:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, module.classroom):
        return HttpResponse("Forbidden", status=403)

    enable_gallery = (request.POST.get("gallery_enabled") or "").strip() == "1"
    module.gallery_enabled = bool(enable_gallery)
    module.save(update_fields=["gallery_enabled"])
    _audit(
        request,
        action="module.gallery_enabled_set",
        classroom=module.classroom,
        target_type="Module",
        target_id=str(module.id),
        summary=f"Set module gallery enabled={module.gallery_enabled}",
        metadata={"gallery_enabled": module.gallery_enabled},
    )

    notice = "Session gallery enabled." if module.gallery_enabled else "Session gallery disabled."
    destination = _with_notice(_teach_module_path(module.id), notice=notice)
    return _safe_internal_redirect(request, destination, fallback=_teach_class_path(module.classroom_id))


@staff_member_required
@require_POST
def teach_moderate_gallery_submission(request, material_id: int, submission_id: int):
    material = Material.objects.select_related("module__classroom").filter(id=material_id).first()
    if not material or material.type != Material.TYPE_GALLERY:
        return HttpResponse("Not found", status=404)
    if not staff_can_delete_submissions(
        request.user,
        material.module.classroom,
        module_id=material.module_id,
    ):
        return HttpResponse("Forbidden", status=403)

    submission = (
        Submission.objects.filter(id=submission_id, material=material)
        .select_related("student", "material__module__classroom")
        .first()
    )
    if not submission:
        return HttpResponse("Not found", status=404)

    approve = (request.POST.get("approve") or "").strip() == "1"
    if approve:
        if not submission.is_published:
            if submission.is_gallery_shared:
                submission.is_gallery_shared = False
                submission.save(update_fields=["is_gallery_shared"])
        else:
            submission.is_gallery_shared = True
            if submission.published_at is None:
                submission.published_at = timezone.now()
            submission.save(update_fields=["is_gallery_shared", "published_at"])
    else:
        if submission.is_gallery_shared:
            submission.is_gallery_shared = False
            submission.save(update_fields=["is_gallery_shared"])

    _audit(
        request,
        action="submission.gallery_moderation_set",
        classroom=material.module.classroom,
        target_type="Submission",
        target_id=str(submission.id),
        summary=f"Set gallery moderation approved={bool(submission.is_gallery_shared)}",
        metadata={
            "material_id": material.id,
            "module_id": material.module_id,
            "student_id": submission.student_id,
            "approved": bool(submission.is_gallery_shared),
            "student_published": bool(submission.is_published),
        },
    )

    return_to = (request.POST.get("return_to") or "").strip() or f"/teach/material/{material.id}/submissions"
    safe_return = _safe_teacher_return_path(return_to, fallback=f"/teach/material/{material.id}/submissions")
    return _safe_internal_redirect(request, safe_return, fallback=f"/teach/material/{material.id}/submissions")


__all__ = [
    "teach_set_module_gallery_enabled",
    "teach_moderate_gallery_submission",
]
