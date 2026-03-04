"""Teacher class policy endpoints (retention presets)."""

from django.http import HttpResponse
from django.views.decorators.http import require_POST

from ...models import Class
from .shared_auth import (
    staff_can_manage_policy,
    staff_classroom_or_none,
    staff_member_required,
)
from .shared_routing import (
    _audit,
    _safe_internal_redirect,
    _teach_class_path,
    _with_notice,
)


def _parse_retention_preset(raw: str) -> str:
    value = (raw or "").strip().lower()
    allowed = {
        Class.RETENTION_ERASE_7_DAYS,
        Class.RETENTION_KEEP_SEMESTER,
        Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES,
    }
    return value if value in allowed else ""


@staff_member_required
@require_POST
def teach_set_retention_preset(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)
    if not staff_can_manage_policy(request.user, classroom):
        return HttpResponse("Forbidden", status=403)

    preset = _parse_retention_preset(request.POST.get("retention_preset") or "")
    if not preset:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), error="Invalid retention preset."),
            fallback=_teach_class_path(classroom.id),
        )

    if classroom.retention_preset == preset:
        return _safe_internal_redirect(
            request,
            _with_notice(_teach_class_path(classroom.id), notice="Retention preset unchanged."),
            fallback=_teach_class_path(classroom.id),
        )

    old_preset = classroom.retention_preset
    classroom.retention_preset = preset
    classroom.save(update_fields=["retention_preset"])
    _audit(
        request,
        action="class.set_retention_preset",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Set class retention preset to {preset}",
        metadata={
            "old_preset": old_preset,
            "retention_preset": preset,
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(_teach_class_path(classroom.id), notice="Retention preset updated."),
        fallback=_teach_class_path(classroom.id),
    )


__all__ = [
    "teach_set_retention_preset",
]
