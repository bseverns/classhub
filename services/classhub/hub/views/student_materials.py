"""Student material response endpoints (checklist/reflection/rubric)."""

import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from ..models import Material, StudentMaterialResponse, StudentOutcomeEvent
from ..services.student_home import build_material_access_map, parse_checklist_items, parse_rubric_criteria

logger = logging.getLogger(__name__)


def _resolve_material_with_lock_check(request, *, material_id: int, expected_type: str):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return None, redirect("/")

    material = Material.objects.select_related("module__classroom").filter(id=material_id).first()
    if not material or material.module.classroom_id != request.classroom.id or material.type != expected_type:
        return None, HttpResponse("Not found", status=404)

    _material_ids, access_map = build_material_access_map(
        request,
        classroom=request.classroom,
        modules=[material.module],
    )
    if access_map.get(material.id, {}).get("is_locked"):
        locked_labels = {
            Material.TYPE_CHECKLIST: "Checklist",
            Material.TYPE_REFLECTION: "Reflection",
            Material.TYPE_RUBRIC: "Rubric",
        }
        return None, HttpResponse(f"{locked_labels.get(expected_type, 'Material')} is locked for this lesson.", status=403)
    return material, None


def _record_material_milestone_event(*, request, material: Material, trigger: str, source: str) -> None:
    try:
        StudentOutcomeEvent.objects.create(
            classroom=request.classroom,
            student=request.student,
            module=material.module,
            material=material,
            event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
            source=source,
            details={"trigger": trigger, "material_id": material.id},
        )
    except Exception:
        logger.exception("student_milestone_event_write_failed material_id=%s trigger=%s", material.id, trigger)


@require_POST
def material_checklist(request, material_id: int):
    material, error_response = _resolve_material_with_lock_check(
        request,
        material_id=material_id,
        expected_type=Material.TYPE_CHECKLIST,
    )
    if error_response:
        return error_response

    checklist_items = parse_checklist_items(material.body)
    checked_indexes: list[int] = []
    for raw in request.POST.getlist("checked_item"):
        try:
            idx = int(raw)
        except Exception:
            continue
        if idx < 0 or idx >= len(checklist_items) or idx in checked_indexes:
            continue
        checked_indexes.append(idx)
    checked_indexes.sort()

    response_obj, _created = StudentMaterialResponse.objects.get_or_create(
        material=material,
        student=request.student,
        defaults={"checklist_checked": checked_indexes},
    )
    previously_complete = bool(checklist_items) and len(response_obj.checklist_checked or []) >= len(checklist_items)
    if response_obj.checklist_checked != checked_indexes:
        response_obj.checklist_checked = checked_indexes
        response_obj.save(update_fields=["checklist_checked", "updated_at"])

    now_complete = bool(checklist_items) and len(checked_indexes) >= len(checklist_items)
    if not previously_complete and now_complete:
        _record_material_milestone_event(
            request=request,
            material=material,
            trigger="checklist_completed",
            source="classhub.material_checklist",
        )
    return redirect("/student")


@require_POST
def material_reflection(request, material_id: int):
    material, error_response = _resolve_material_with_lock_check(
        request,
        material_id=material_id,
        expected_type=Material.TYPE_REFLECTION,
    )
    if error_response:
        return error_response

    reflection_text = (request.POST.get("reflection_text") or "").strip()[:2000]
    response_obj, _created = StudentMaterialResponse.objects.get_or_create(
        material=material,
        student=request.student,
        defaults={"reflection_text": reflection_text},
    )
    previously_had_text = bool((response_obj.reflection_text or "").strip())
    if response_obj.reflection_text != reflection_text:
        response_obj.reflection_text = reflection_text
        response_obj.save(update_fields=["reflection_text", "updated_at"])

    if not previously_had_text and reflection_text:
        _record_material_milestone_event(
            request=request,
            material=material,
            trigger="reflection_submitted",
            source="classhub.material_reflection",
        )
    return redirect("/student")


@require_POST
def material_rubric(request, material_id: int):
    material, error_response = _resolve_material_with_lock_check(
        request,
        material_id=material_id,
        expected_type=Material.TYPE_RUBRIC,
    )
    if error_response:
        return error_response

    criteria = parse_rubric_criteria(material.body)
    scale_max = max(int(getattr(material, "rubric_scale_max", 4) or 4), 2)
    score_limit = min(scale_max, 10)
    rubric_scores: list[int] = []
    for idx in range(len(criteria)):
        raw = (request.POST.get(f"criterion_{idx}") or "").strip()
        try:
            score = int(raw)
        except Exception:
            score = 0
        if score < 1 or score > score_limit:
            score = 0
        rubric_scores.append(score)
    rubric_feedback = (request.POST.get("rubric_feedback") or "").strip()[:2000]

    response_obj, _created = StudentMaterialResponse.objects.get_or_create(
        material=material,
        student=request.student,
        defaults={"rubric_scores": rubric_scores, "rubric_feedback": rubric_feedback},
    )
    old_scores = response_obj.rubric_scores if isinstance(response_obj.rubric_scores, list) else []
    previously_submitted = bool(any(int(v or 0) > 0 for v in old_scores) or (response_obj.rubric_feedback or "").strip())
    if response_obj.rubric_scores != rubric_scores or response_obj.rubric_feedback != rubric_feedback:
        response_obj.rubric_scores = rubric_scores
        response_obj.rubric_feedback = rubric_feedback
        response_obj.save(update_fields=["rubric_scores", "rubric_feedback", "updated_at"])

    now_submitted = bool(any(score > 0 for score in rubric_scores) or rubric_feedback)
    if not previously_submitted and now_submitted:
        _record_material_milestone_event(
            request=request,
            material=material,
            trigger="rubric_submitted",
            source="classhub.material_rubric",
        )
    return redirect("/student")


__all__ = [
    "material_checklist",
    "material_reflection",
    "material_rubric",
]
