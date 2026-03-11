"""Service helpers for teacher class dashboard/export view logic."""

from __future__ import annotations

import csv
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.db import models
from django.utils import timezone

from ..models import (
    CertificateIssuance,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    StudentMaterialResponse,
    Submission,
)
from .content_links import parse_course_lesson_url
from .filenames import safe_filename
from .markdown_content import load_lesson_markdown
from .telemetry_reads import student_events_queryset
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
from .teacher_dashboard_sections.shared import detail_int as _detail_int_impl, int_setting as _int_setting_impl
from .teacher_tracker import _build_helper_signal_snapshot, _build_lesson_tracker_rows
from .zip_exports import (
    reserve_archive_path,
    temporary_zip_archive,
    write_submission_file_to_archive,
)


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


def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:
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
    lesson_rows = _build_lesson_tracker_rows(
        request,
        classroom.id,
        modules,
        student_count,
        class_session_epoch=classroom.session_epoch,
    )
    helper_signals = _build_helper_signal_snapshot(
        classroom=classroom,
        students=students,
        window_hours=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_WINDOW_HOURS", 24) or 24), 1),
        top_students=max(int(getattr(settings, "CLASSHUB_HELPER_SIGNAL_TOP_STUDENTS", 5) or 5), 1),
    )
    return {
        "modules": modules,
        "student_count": student_count,
        "students": students,
        "support_tag_choices": _support_tag_choices(),
        "support_tags_by_student": _support_tags_by_student(
            classroom=classroom,
            students=students,
        ),
        "submission_counts": _material_submission_counts(upload_material_ids),
        "submission_counts_by_student": _submission_counts_by_student(
            classroom=classroom,
            students=students,
        ),
        "lesson_rows": lesson_rows,
        "helper_signals": helper_signals,
        "facilitator_support": _build_facilitator_support_snapshot(
            classroom=classroom,
            students=students,
            modules=modules,
        ),
        "outcome_snapshot": _build_outcome_snapshot(classroom=classroom, students=students),
    }


def export_submissions_today_archive(*, classroom, day_start, day_end):
    rows = list(
        Submission.objects.filter(
            student__classroom=classroom,
            uploaded_at__gte=day_start,
            uploaded_at__lt=day_end,
        )
        .select_related("student", "material")
        .order_by("student__display_name", "material__title", "uploaded_at", "id")
    )

    file_count = 0
    used_paths: set[str] = set()
    with temporary_zip_archive() as (tmp, archive):
        for submission in rows:
            student_name = safe_filename(submission.student.display_name)
            material_name = safe_filename(submission.material.title)
            original = safe_filename(submission.original_filename or submission.file.name.rsplit("/", 1)[-1])
            stamp = timezone.localtime(submission.uploaded_at).strftime("%H%M%S")
            candidate = reserve_archive_path(
                f"{student_name}/{material_name}/{stamp}_{original}",
                used_paths,
                fallback=f"{student_name}/{material_name}/{stamp}_{submission.id}_{original}",
            )
            if not write_submission_file_to_archive(
                archive,
                submission=submission,
                arcname=candidate,
                allow_file_fallback=False,
            ):
                continue
            file_count += 1
        if file_count == 0:
            archive.writestr(
                "README.txt",
                (
                    "No submission files were available for this class today.\n"
                    "This can happen when there were no uploads or file sources were unavailable.\n"
                ),
            )
    return tmp, file_count


def export_class_summary_csv(*, classroom, active_window_days: int = 7) -> str:
    active_window_days = max(int(active_window_days or 0), 1)
    now = timezone.now()
    active_since = now - timedelta(days=active_window_days)

    students = list(
        StudentIdentity.objects.filter(classroom=classroom)
        .only("id", "display_name", "created_at", "last_seen_at")
        .order_by("display_name", "id")
    )
    student_ids = [int(student.id) for student in students]

    joins_total = student_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentEvent.EVENT_CLASS_JOIN,
    ).count()
    rejoins_total = student_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type__in=[StudentEvent.EVENT_REJOIN_DEVICE_HINT, StudentEvent.EVENT_REJOIN_RETURN_CODE],
    ).count()
    helper_access_total = student_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
    ).count()
    active_students = StudentIdentity.objects.filter(
        classroom=classroom,
        last_seen_at__gte=active_since,
    ).count()
    total_submissions = Submission.objects.filter(student__classroom=classroom).count()
    total_rubric_responses = StudentMaterialResponse.objects.filter(
        student__classroom=classroom,
        material__type=Material.TYPE_RUBRIC,
    ).count()
    total_rubric_responders = StudentMaterialResponse.objects.filter(
        student__classroom=classroom,
        material__type=Material.TYPE_RUBRIC,
    ).values("student_id").distinct().count()

    joins_by_student: dict[int, int] = {}
    for row in (
        student_events_queryset().filter(
            student_id__in=student_ids,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
        )
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        joins_by_student[int(row["student_id"])] = int(row["total"] or 0)

    helper_by_student: dict[int, int] = {}
    for row in (
        student_events_queryset().filter(
            student_id__in=student_ids,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
        )
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        helper_by_student[int(row["student_id"])] = int(row["total"] or 0)

    submissions_by_student: dict[int, int] = {}
    for row in (
        Submission.objects.filter(student_id__in=student_ids)
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        submissions_by_student[int(row["student_id"])] = int(row["total"] or 0)
    rubric_by_student: dict[int, int] = {}
    for row in (
        StudentMaterialResponse.objects.filter(student_id__in=student_ids, material__type=Material.TYPE_RUBRIC)
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        rubric_by_student[int(row["student_id"])] = int(row["total"] or 0)

    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))

    lesson_rows: list[dict] = []
    for module in modules:
        mats = list(module.materials.all())
        mats.sort(key=lambda material: (material.order_index, material.id))
        course_slug = ""
        lesson_slug = ""
        lesson_title = ""
        for material in mats:
            if material.type != Material.TYPE_LINK:
                continue
            parsed = parse_course_lesson_url(material.url)
            if not parsed:
                continue
            course_slug, lesson_slug = parsed
            try:
                front_matter, _body, _meta = load_lesson_markdown(course_slug, lesson_slug)
                lesson_title = str(front_matter.get("title") or lesson_slug).strip()
            except ValueError:
                lesson_title = lesson_slug
            break

        upload_material_ids = [
            material.id for material in mats if material.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}
        ]
        rubric_material_ids = [material.id for material in mats if material.type == Material.TYPE_RUBRIC]
        submissions_total = (
            Submission.objects.filter(material_id__in=upload_material_ids).count() if upload_material_ids else 0
        )
        submitters_total = (
            Submission.objects.filter(material_id__in=upload_material_ids)
            .values("student_id")
            .distinct()
            .count()
            if upload_material_ids
            else 0
        )
        rubric_responses_total = (
            StudentMaterialResponse.objects.filter(material_id__in=rubric_material_ids).count() if rubric_material_ids else 0
        )
        rubric_responders_total = (
            StudentMaterialResponse.objects.filter(material_id__in=rubric_material_ids)
            .values("student_id")
            .distinct()
            .count()
            if rubric_material_ids
            else 0
        )
        if not (course_slug or lesson_slug or upload_material_ids or rubric_material_ids):
            continue
        lesson_rows.append(
            {
                "course_slug": course_slug,
                "lesson_slug": lesson_slug,
                "lesson_title": lesson_title or lesson_slug or module.title,
                "module_title": module.title,
                "submissions": submissions_total,
                "submitters": submitters_total,
                "rubric_responses": rubric_responses_total,
                "rubric_responders": rubric_responders_total,
            }
        )

    fieldnames = [
        "row_type",
        "class_id",
        "class_name",
        "display_name",
        "course_slug",
        "lesson_slug",
        "lesson_title",
        "module_title",
        "joins",
        "rejoins",
        "active_students",
        "submissions",
        "submitters",
        "rubric_responses",
        "rubric_responders",
        "helper_accesses",
        "first_seen_at",
        "last_seen_at",
        "active_window_days",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()

    writer.writerow(
        {
            "row_type": "class_summary",
            "class_id": classroom.id,
            "class_name": classroom.name,
            "joins": joins_total,
            "rejoins": rejoins_total,
            "active_students": active_students,
            "submissions": total_submissions,
            "rubric_responses": total_rubric_responses,
            "rubric_responders": total_rubric_responders,
            "helper_accesses": helper_access_total,
            "active_window_days": active_window_days,
        }
    )

    for student in students:
        writer.writerow(
            {
                "row_type": "student_summary",
                "class_id": classroom.id,
                "class_name": classroom.name,
                "display_name": student.display_name,
                "joins": joins_by_student.get(int(student.id), 0),
                "submissions": submissions_by_student.get(int(student.id), 0),
                "rubric_responses": rubric_by_student.get(int(student.id), 0),
                "helper_accesses": helper_by_student.get(int(student.id), 0),
                "first_seen_at": (student.created_at.isoformat() if student.created_at else ""),
                "last_seen_at": (student.last_seen_at.isoformat() if student.last_seen_at else ""),
                "active_window_days": active_window_days,
            }
        )

    for lesson in lesson_rows:
        writer.writerow(
            {
                "row_type": "lesson_summary",
                "class_id": classroom.id,
                "class_name": classroom.name,
                "course_slug": lesson["course_slug"],
                "lesson_slug": lesson["lesson_slug"],
                "lesson_title": lesson["lesson_title"],
                "module_title": lesson["module_title"],
                "submissions": lesson["submissions"],
                "submitters": lesson["submitters"],
                "rubric_responses": lesson["rubric_responses"],
                "rubric_responders": lesson["rubric_responders"],
                "active_window_days": active_window_days,
            }
        )

    return out.getvalue()


def _int_setting(setting_name: str, default: int, *, minimum: int = 1) -> int:
    return _int_setting_impl(setting_name, default, minimum=minimum)


def export_class_outcomes_csv(
    *,
    classroom,
    active_window_days: int = 30,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> str:
    active_window_days = max(int(active_window_days or 0), 1)
    certificate_min_sessions = (
        _int_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8)
        if certificate_min_sessions is None
        else max(int(certificate_min_sessions), 1)
    )
    certificate_min_artifacts = (
        _int_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6)
        if certificate_min_artifacts is None
        else max(int(certificate_min_artifacts), 1)
    )

    students = list(
        StudentIdentity.objects.filter(classroom=classroom)
        .only("id", "display_name")
        .order_by("display_name", "id")
    )
    student_ids = [int(student.id) for student in students]
    rollup = _build_outcome_rollup(
        classroom=classroom,
        students=students,
        active_window_days=active_window_days,
        include_class_metrics=True,
        include_outcome_windows=True,
    )
    sessions_by_student: dict[int, int] = rollup["sessions_by_student"]
    artifacts_by_student: dict[int, int] = rollup["artifacts_by_student"]
    milestones_by_student: dict[int, int] = rollup["milestones_by_student"]
    outcome_windows: dict[int, tuple[str, str]] = rollup["outcome_windows"]

    eligible_students = 0
    issued_by_student: dict[int, str] = {}
    if student_ids:
        for row in CertificateIssuance.objects.filter(classroom=classroom, student_id__in=student_ids).values(
            "student_id",
            "issued_at",
        ):
            issued_by_student[int(row["student_id"])] = (
                row["issued_at"].isoformat() if row.get("issued_at") else ""
            )
    for student in students:
        sid = int(student.id)
        if (
            sessions_by_student.get(sid, 0) >= certificate_min_sessions
            and artifacts_by_student.get(sid, 0) >= certificate_min_artifacts
        ):
            eligible_students += 1

    fieldnames = [
        "row_type",
        "class_id",
        "class_name",
        "display_name",
        "session_completions",
        "artifact_submissions",
        "milestones",
        "certificate_eligible",
        "certificate_issued",
        "certificate_issued_at",
        "certificate_issued_students",
        "eligible_students",
        "total_students",
        "active_outcome_students",
        "first_outcome_at",
        "last_outcome_at",
        "certificate_min_sessions",
        "certificate_min_artifacts",
        "active_window_days",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()

    writer.writerow(
        {
            "row_type": "class_outcome_summary",
            "class_id": classroom.id,
            "class_name": classroom.name,
            "session_completions": rollup["total_sessions"],
            "artifact_submissions": rollup["total_artifacts"],
            "milestones": rollup["total_milestones"],
            "eligible_students": eligible_students,
            "certificate_issued_students": len(issued_by_student),
            "total_students": len(students),
            "active_outcome_students": rollup["active_students"],
            "certificate_min_sessions": certificate_min_sessions,
            "certificate_min_artifacts": certificate_min_artifacts,
            "active_window_days": active_window_days,
        }
    )

    for student in students:
        sid = int(student.id)
        sessions = sessions_by_student.get(sid, 0)
        artifacts = artifacts_by_student.get(sid, 0)
        eligible = sessions >= certificate_min_sessions and artifacts >= certificate_min_artifacts
        first_outcome, last_outcome = outcome_windows.get(sid, ("", ""))
        certificate_issued_at = issued_by_student.get(sid, "")
        writer.writerow(
            {
                "row_type": "student_outcome_summary",
                "class_id": classroom.id,
                "class_name": classroom.name,
                "display_name": student.display_name,
                "session_completions": sessions,
                "artifact_submissions": artifacts,
                "milestones": milestones_by_student.get(sid, 0),
                "certificate_eligible": "yes" if eligible else "no",
                "certificate_issued": "yes" if certificate_issued_at else "no",
                "certificate_issued_at": certificate_issued_at,
                "first_outcome_at": first_outcome,
                "last_outcome_at": last_outcome,
                "certificate_min_sessions": certificate_min_sessions,
                "certificate_min_artifacts": certificate_min_artifacts,
                "active_window_days": active_window_days,
            }
        )

    return out.getvalue()


__all__ = [
    "build_certificate_eligibility_rows",
    "build_dashboard_context",
    "export_class_outcomes_csv",
    "export_class_summary_csv",
    "export_submissions_today_archive",
]
