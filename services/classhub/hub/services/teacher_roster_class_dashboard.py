"""Dashboard context helpers for teacher class roster surfaces."""

from __future__ import annotations

from django.conf import settings

from ..models import Material, Module, StudentIdentity
from .content_links import parse_course_lesson_url
from .teacher_dashboard_sections.facilitator_support import (
    build_facilitator_support_snapshot as _facilitator_support_snapshot_impl,
)
from .teacher_dashboard_sections.outcomes import (
    build_certificate_eligibility_rows as _certificate_eligibility_rows_impl,
    build_outcome_rollup as _outcome_rollup_impl,
    build_outcome_snapshot as _outcome_snapshot_impl,
)
from .teacher_dashboard_sections.roster import (
    material_submission_counts as _material_submission_counts_impl,
    submission_counts_by_student as _submission_counts_by_student_impl,
    support_tag_choices as _support_tag_choices_impl,
    support_tags_by_student as _support_tags_by_student_impl,
)
from .teacher_dashboard_sections.shared import detail_int as _detail_int_impl


def _material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:
    return _material_submission_counts_impl(upload_material_ids)


def _submission_counts_by_student(*, classroom, students: list) -> dict[int, int]:
    return _submission_counts_by_student_impl(classroom=classroom, students=students)


def _support_tag_choices() -> list[dict[str, str]]:
    return _support_tag_choices_impl()


def _support_tags_by_student(*, classroom, students: list[StudentIdentity]) -> dict[int, list[dict[str, str]]]:
    return _support_tags_by_student_impl(classroom=classroom, students=students)


def _build_outcome_rollup(
    *,
    classroom,
    students: list[StudentIdentity],
    active_window_days: int = 30,
    include_class_metrics: bool = False,
    include_outcome_windows: bool = False,
) -> dict:
    return _outcome_rollup_impl(
        classroom=classroom,
        students=students,
        active_window_days=active_window_days,
        include_class_metrics=include_class_metrics,
        include_outcome_windows=include_outcome_windows,
    )


def build_certificate_eligibility_rows(
    *,
    classroom,
    students: list[StudentIdentity] | None = None,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> dict:
    return _certificate_eligibility_rows_impl(
        classroom=classroom,
        students=students,
        certificate_min_sessions=certificate_min_sessions,
        certificate_min_artifacts=certificate_min_artifacts,
    )


def _build_outcome_snapshot(*, classroom, students: list[StudentIdentity]) -> dict:
    return _outcome_snapshot_impl(classroom=classroom, students=students)


def _detail_int(details: dict, key: str) -> int:
    # Compatibility shim for older tests/imports.
    return _detail_int_impl(details, key)


def _build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:
    return _facilitator_support_snapshot_impl(
        classroom=classroom,
        students=students,
        modules=modules,
    )


def _landing_lesson_choices(modules: list[Module]) -> list[dict]:
    choices: list[dict] = []
    for module in modules:
        lesson_url = ""
        for material in module.materials.all():
            if material.type != Material.TYPE_LINK or not material.url:
                continue
            if not parse_course_lesson_url(material.url):
                continue
            lesson_url = material.url
            break
        if not lesson_url:
            continue
        choices.append(
            {
                "module_id": module.id,
                "module_title": module.title,
                "lesson_url": lesson_url,
            }
        )
    return choices


def build_dashboard_context_impl(
    *,
    request,
    classroom,
    normalize_order_fn,
    build_lesson_tracker_rows,
    build_helper_signal_snapshot,
    support_tag_choices,
    support_tags_by_student,
    material_submission_counts,
    submission_counts_by_student,
    build_facilitator_support_snapshot,
    build_outcome_snapshot,
) -> dict:
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))
    normalize_order_fn(modules)
    modules.sort(key=lambda module: (module.order_index, module.id))

    upload_material_ids: list[int] = []
    for module in modules:
        for material in module.materials.all():
            if material.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
                upload_material_ids.append(material.id)

    student_count = classroom.students.count()
    students = list(classroom.students.all().order_by("created_at", "id"))
    lesson_rows = build_lesson_tracker_rows(
        request,
        classroom.id,
        modules,
        student_count,
        class_session_epoch=classroom.session_epoch,
    )
    helper_signals = build_helper_signal_snapshot(
        classroom=classroom,
        students=students,
        window_hours=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_WINDOW_HOURS", 24) or 24), 1),
        top_students=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_TOP_STUDENTS", 5) or 5), 1),
    )
    return {
        "modules": modules,
        "student_count": student_count,
        "students": students,
        "support_tag_choices": support_tag_choices(),
        "support_tags_by_student": support_tags_by_student(
            classroom=classroom,
            students=students,
        ),
        "submission_counts": material_submission_counts(upload_material_ids),
        "submission_counts_by_student": submission_counts_by_student(
            classroom=classroom,
            students=students,
        ),
        "lesson_rows": lesson_rows,
        "landing_lesson_choices": _landing_lesson_choices(modules),
        "helper_signals": helper_signals,
        "facilitator_support": build_facilitator_support_snapshot(
            classroom=classroom,
            students=students,
            modules=modules,
        ),
        "outcome_snapshot": build_outcome_snapshot(classroom=classroom, students=students),
    }


__all__ = [
    "_build_facilitator_support_snapshot",
    "_build_outcome_rollup",
    "_build_outcome_snapshot",
    "_detail_int",
    "_material_submission_counts",
    "_submission_counts_by_student",
    "_support_tag_choices",
    "_support_tags_by_student",
    "build_certificate_eligibility_rows",
    "build_dashboard_context_impl",
]
