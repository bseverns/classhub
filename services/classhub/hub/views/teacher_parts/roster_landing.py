"""Teacher class landing page configuration endpoints."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...services.content_links import safe_external_url
from .shared_auth import staff_can_manage_classroom, staff_classroom_or_none, staff_member_required
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


@staff_member_required
@require_POST
def teach_update_class_landing(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_classroom(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    landing_title = (request.POST.get("student_landing_title") or "").strip()[:200]
    landing_message = (request.POST.get("student_landing_message") or "").strip()[:4000]
    landing_hero_url, hero_error = _normalize_class_landing_hero_url(request.POST.get("student_landing_hero_url"))
    if hero_error:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error=hero_error),
            fallback=_teach_class_path(classroom.id),
        )

    classroom.student_landing_title = landing_title
    classroom.student_landing_message = landing_message
    classroom.student_landing_hero_url = landing_hero_url
    classroom.save(update_fields=["student_landing_title", "student_landing_message", "student_landing_hero_url"])
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
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice="Student landing page updated."),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = ["teach_update_class_landing"]
