"""Teacher class landing page configuration endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import Material, Module
from ...services.content_links import parse_course_lesson_url
from ...services.content_links import safe_external_url
from .shared_auth import staff_can_manage_policy, staff_classroom_or_none, staff_member_required
from .shared_routing import _audit, _safe_internal_redirect, _teach_class_path, _with_notice


def _normalize_class_landing_hero_url(raw: str) -> tuple[str, str]:
    value = str(raw or "").strip()[:500]
    if not value:
        return "", ""
    if value.startswith("/") and not value.startswith("//"):
        return value, ""
    safe_value = safe_external_url(value)
    if safe_value:
        return safe_value, ""
    return "", "Hero image URL must start with / or use http/https."


def _has_lesson_link(module: Module) -> bool:
    for material in module.materials.all():
        if material.type != Material.TYPE_LINK or not material.url:
            continue
        if parse_course_lesson_url(material.url):
            return True
    return False


def _normalize_landing_default_module_id(*, classroom, raw: str) -> tuple[Module | None, str]:
    value = str(raw or "").strip()
    if not value:
        return None, ""
    try:
        module_id = int(value)
    except (TypeError, ValueError):
        return None, "Default highlighted lesson is not valid."

    module = (
        Module.objects.filter(classroom=classroom, id=module_id)
        .prefetch_related("materials")
        .first()
    )
    if not module:
        return None, "Default highlighted lesson is not valid for this class."
    if not _has_lesson_link(module):
        return None, "Default highlighted lesson must have a valid lesson link."
    return module, ""


@staff_member_required
@require_POST
def teach_update_class_landing(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    landing_title = (request.POST.get("student_landing_title") or "").strip()[:200]
    landing_message = (request.POST.get("student_landing_message") or "").strip()[:4000]
    landing_hero_url, hero_error = _normalize_class_landing_hero_url(request.POST.get("student_landing_hero_url"))
    raw_default_module_id = request.POST.get("student_landing_default_module_id")
    if raw_default_module_id is None:
        default_module = classroom.student_landing_default_module
        default_module_error = ""
    else:
        default_module, default_module_error = _normalize_landing_default_module_id(
            classroom=classroom,
            raw=raw_default_module_id,
        )
    if hero_error:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error=hero_error),
            fallback=_teach_class_path(classroom.id),
        )
    if default_module_error:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error=default_module_error),
            fallback=_teach_class_path(classroom.id),
        )

    classroom.student_landing_title = landing_title
    classroom.student_landing_message = landing_message
    classroom.student_landing_hero_url = landing_hero_url
    classroom.student_landing_default_module = default_module
    classroom.save(
        update_fields=[
            "student_landing_title",
            "student_landing_message",
            "student_landing_hero_url",
            "student_landing_default_module",
        ]
    )
    _audit(
        request,
        action="class.update_student_landing",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Updated student landing page for {classroom.name}",
        metadata={
            "has_title": bool(landing_title),
            "has_message": bool(landing_message),
            "has_hero_url": bool(landing_hero_url),
            "default_module_id": default_module.id if default_module else None,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice="Student landing page updated."),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = ["teach_update_class_landing"]
