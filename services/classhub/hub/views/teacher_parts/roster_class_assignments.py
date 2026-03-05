"""Superuser class-staff assignment endpoints."""

from .shared import (
    Class,
    ClassStaffAssignment,
    _audit,
    _parse_positive_int,
    _safe_internal_redirect,
    _with_notice,
    get_user_model,
    require_POST,
    staff_member_required,
)


def _require_superuser(request):
    if request.user.is_superuser:
        return None
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error="Only superusers can manage organizations.", extra={"org_admin": "1"}),
        fallback="/teach",
    )


def _class_assignment_form_values(request):
    return {
        "org_admin": "1",
        "class_assignment_class_id": (request.POST.get("class_assignment_class_id") or "").strip(),
        "class_assignment_user_id": (request.POST.get("class_assignment_user_id") or "").strip(),
        "class_assignment_active": "1" if (request.POST.get("class_assignment_active") or "").strip() == "1" else "0",
        "class_assignment_bulk_user_id": (request.POST.get("class_assignment_bulk_user_id") or "").strip(),
        "class_assignment_return_to": (request.POST.get("class_assignment_return_to") or "").strip(),
    }


def _class_assignment_error(request, message: str, form_values: dict):
    return_to = form_values.get("class_assignment_return_to") or "/teach"
    return _safe_internal_redirect(
        request,
        _with_notice(return_to, error=message, extra=form_values),
        fallback="/teach",
    )


def _resolve_teacher_user(user_id: int):
    User = get_user_model()
    return User.objects.filter(id=user_id, is_staff=True, is_active=True, is_superuser=False).first()


def _parse_selected_class_ids(raw_values: list[str]) -> set[int]:
    selected_ids: set[int] = set()
    for raw in raw_values:
        parsed = _parse_positive_int((raw or "").strip(), min_value=1, max_value=2_147_483_647)
        if parsed is not None:
            selected_ids.add(parsed)
    return selected_ids


def _apply_bulk_assignment_set(*, user, selected_class_ids: set[int]) -> tuple[int, int]:
    existing_active_ids = set(
        int(cid) for cid in ClassStaffAssignment.objects.filter(user=user, is_active=True).values_list("classroom_id", flat=True)
    )
    to_deactivate = existing_active_ids - selected_class_ids
    deactivated = 0
    if to_deactivate:
        deactivated = ClassStaffAssignment.objects.filter(user=user, classroom_id__in=to_deactivate, is_active=True).update(
            is_active=False
        )

    existing_rows = {
        int(row.classroom_id): row
        for row in ClassStaffAssignment.objects.filter(user=user, classroom_id__in=selected_class_ids)
    }
    activated = 0
    for class_id in sorted(selected_class_ids):
        row = existing_rows.get(class_id)
        if row is None:
            ClassStaffAssignment.objects.create(classroom_id=class_id, user=user, is_active=True)
            activated += 1
        elif not row.is_active:
            row.is_active = True
            row.save(update_fields=["is_active", "updated_at"])
            activated += 1
    return activated, int(deactivated)


@staff_member_required
@require_POST
def teach_upsert_class_staff_assignment(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    form_values = _class_assignment_form_values(request)

    class_id = _parse_positive_int(form_values["class_assignment_class_id"], min_value=1, max_value=2_147_483_647)
    user_id = _parse_positive_int(form_values["class_assignment_user_id"], min_value=1, max_value=2_147_483_647)
    if class_id is None or user_id is None:
        return _class_assignment_error(request, "Select both a class and a teacher account.", form_values)
    classroom = Class.objects.filter(id=class_id).first()
    user = _resolve_teacher_user(user_id)
    if classroom is None:
        return _class_assignment_error(request, "Class not found.", form_values)
    if user is None:
        return _class_assignment_error(request, "Teacher account not found.", form_values)

    is_active = form_values["class_assignment_active"] == "1"
    assignment, created = ClassStaffAssignment.objects.get_or_create(
        classroom=classroom,
        user=user,
        defaults={"is_active": is_active},
    )
    if assignment.is_active != is_active:
        assignment.is_active = is_active
        assignment.save(update_fields=["is_active", "updated_at"])
    status_label = "active" if assignment.is_active else "inactive"
    _audit(
        request,
        action="class.staff_assignment.upsert",
        classroom=classroom,
        target_type="ClassStaffAssignment",
        target_id=str(assignment.id),
        summary=f"Set class assignment for {user.username} in {classroom.name}",
        metadata={"classroom_id": classroom.id, "user_id": user.id, "is_active": assignment.is_active, "created": created},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            form_values.get("class_assignment_return_to") or "/teach",
            notice=f"Set class assignment for {user.username} in {classroom.name} ({status_label}).",
            extra=form_values,
        ),
        fallback="/teach",
    )


@staff_member_required
@require_POST
def teach_bulk_set_class_staff_assignments(request):
    denied = _require_superuser(request)
    if denied is not None:
        return denied
    form_values = _class_assignment_form_values(request)

    user_id = _parse_positive_int(form_values["class_assignment_bulk_user_id"], min_value=1, max_value=2_147_483_647)
    if user_id is None:
        return _class_assignment_error(request, "Select a teacher account for bulk class assignment.", form_values)
    user = _resolve_teacher_user(user_id)
    if user is None:
        return _class_assignment_error(request, "Teacher account not found.", form_values)

    selected_ids = _parse_selected_class_ids(request.POST.getlist("class_assignment_bulk_class_ids"))
    valid_ids = set(int(cid) for cid in Class.objects.filter(id__in=selected_ids).values_list("id", flat=True))
    if selected_ids and valid_ids != selected_ids:
        return _class_assignment_error(request, "One or more selected classes no longer exist.", form_values)
    activated, deactivated = _apply_bulk_assignment_set(user=user, selected_class_ids=valid_ids)
    _audit(
        request,
        action="class.staff_assignment.bulk_set",
        target_type="User",
        target_id=str(user.id),
        summary=f"Bulk-set class assignments for {user.username}",
        metadata={"user_id": user.id, "selected_class_count": len(valid_ids), "activated_count": activated, "deactivated_count": deactivated},
    )
    return _safe_internal_redirect(
        request,
        _with_notice(
            "/teach",
            notice=(
                f"Updated class assignments for {user.username}. "
                f"Selected {len(valid_ids)} classes, activated {activated}, deactivated {deactivated}."
            ),
            extra={"org_admin": "1", "class_assignment_bulk_user_id": str(user.id)},
        ),
        fallback="/teach",
    )


__all__ = [
    "teach_bulk_set_class_staff_assignments",
    "teach_upsert_class_staff_assignment",
]
