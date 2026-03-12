"""Service helpers for teacher class dashboard/export view logic."""

from __future__ import annotations

from .teacher_roster_class_dashboard import (
    _build_facilitator_support_snapshot,
    _build_outcome_rollup,
    _build_outcome_snapshot,
    _detail_int,
    _material_submission_counts,
    _submission_counts_by_student,
    _support_tag_choices,
    _support_tags_by_student,
    build_certificate_eligibility_rows,
    build_dashboard_context_impl,
)
from .teacher_roster_class_exports import (
    export_class_outcomes_csv,
    export_class_summary_csv,
    export_submissions_today_archive,
)
from .teacher_tracker import _build_helper_signal_snapshot, _build_lesson_tracker_rows


def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:
    return build_dashboard_context_impl(
        request=request,
        classroom=classroom,
        normalize_order_fn=normalize_order_fn,
        build_lesson_tracker_rows=_build_lesson_tracker_rows,
        build_helper_signal_snapshot=_build_helper_signal_snapshot,
        support_tag_choices=_support_tag_choices,
        support_tags_by_student=_support_tags_by_student,
        material_submission_counts=_material_submission_counts,
        submission_counts_by_student=_submission_counts_by_student,
        build_facilitator_support_snapshot=_build_facilitator_support_snapshot,
        build_outcome_snapshot=_build_outcome_snapshot,
    )


__all__ = [
    "build_certificate_eligibility_rows",
    "build_dashboard_context",
    "export_class_outcomes_csv",
    "export_class_summary_csv",
    "export_submissions_today_archive",
]
