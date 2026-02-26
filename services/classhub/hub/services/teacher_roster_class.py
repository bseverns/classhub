"""Service helpers for teacher class dashboard/export view logic."""

from __future__ import annotations

import csv
from datetime import timedelta
from io import StringIO

from django.conf import settings
from django.db import models
from django.utils import timezone

from ..models import Material, StudentEvent, StudentIdentity, StudentOutcomeEvent, Submission
from .content_links import parse_course_lesson_url
from .filenames import safe_filename
from .markdown_content import load_lesson_markdown
from .teacher_tracker import _build_helper_signal_snapshot, _build_lesson_tracker_rows
from .zip_exports import (
    reserve_archive_path,
    temporary_zip_archive,
    write_submission_file_to_archive,
)


def _material_submission_counts(upload_material_ids: list[int]) -> dict[int, int]:
    submission_counts: dict[int, int] = {}
    if not upload_material_ids:
        return submission_counts
    rows = (
        Submission.objects.filter(material_id__in=upload_material_ids)
        .values("material_id")
        .annotate(total=models.Count("student_id", distinct=True))
    )
    for row in rows:
        material_id = int(row["material_id"])
        submission_counts[material_id] = int(row["total"])
    return submission_counts


def _submission_counts_by_student(*, classroom, students: list) -> dict[int, int]:
    submission_counts: dict[int, int] = {}
    if not students:
        return submission_counts
    rows = (
        Submission.objects.filter(student__classroom=classroom)
        .values("student_id")
        .annotate(total=models.Count("id"))
    )
    for row in rows:
        submission_counts[int(row["student_id"])] = int(row["total"])
    return submission_counts


def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))
    normalize_order_fn(modules)
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))

    upload_material_ids: list[int] = []
    for module in modules:
        for material in module.materials.all():
            if material.type == Material.TYPE_UPLOAD:
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
        "submission_counts": _material_submission_counts(upload_material_ids),
        "submission_counts_by_student": _submission_counts_by_student(
            classroom=classroom,
            students=students,
        ),
        "lesson_rows": lesson_rows,
        "helper_signals": helper_signals,
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

    joins_total = StudentEvent.objects.filter(
        classroom=classroom,
        event_type=StudentEvent.EVENT_CLASS_JOIN,
    ).count()
    rejoins_total = StudentEvent.objects.filter(
        classroom=classroom,
        event_type__in=[StudentEvent.EVENT_REJOIN_DEVICE_HINT, StudentEvent.EVENT_REJOIN_RETURN_CODE],
    ).count()
    helper_access_total = StudentEvent.objects.filter(
        classroom=classroom,
        event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
    ).count()
    active_students = StudentIdentity.objects.filter(
        classroom=classroom,
        last_seen_at__gte=active_since,
    ).count()
    total_submissions = Submission.objects.filter(student__classroom=classroom).count()

    joins_by_student: dict[int, int] = {}
    for row in (
        StudentEvent.objects.filter(
            student_id__in=student_ids,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
        )
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        joins_by_student[int(row["student_id"])] = int(row["total"] or 0)

    helper_by_student: dict[int, int] = {}
    for row in (
        StudentEvent.objects.filter(
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

        upload_material_ids = [material.id for material in mats if material.type == Material.TYPE_UPLOAD]
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
        if not (course_slug or lesson_slug or upload_material_ids):
            continue
        lesson_rows.append(
            {
                "course_slug": course_slug,
                "lesson_slug": lesson_slug,
                "lesson_title": lesson_title or lesson_slug or module.title,
                "module_title": module.title,
                "submissions": submissions_total,
                "submitters": submitters_total,
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
                "active_window_days": active_window_days,
            }
        )

    return out.getvalue()


def _int_setting(setting_name: str, default: int, *, minimum: int = 1) -> int:
    raw = getattr(settings, setting_name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = int(default)
    return max(value, minimum)


def export_class_outcomes_csv(
    *,
    classroom,
    active_window_days: int = 30,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> str:
    active_window_days = max(int(active_window_days or 0), 1)
    active_since = timezone.now() - timedelta(days=active_window_days)
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

    sessions_by_student: dict[int, int] = {}
    artifacts_by_student: dict[int, int] = {}
    milestones_by_student: dict[int, int] = {}
    if student_ids:
        for row in (
            StudentOutcomeEvent.objects.filter(student_id__in=student_ids)
            .values("student_id", "event_type")
            .annotate(total=models.Count("id"))
        ):
            student_id = int(row["student_id"])
            total = int(row["total"] or 0)
            event_type = str(row["event_type"] or "")
            if event_type == StudentOutcomeEvent.EVENT_SESSION_COMPLETED:
                sessions_by_student[student_id] = total
            elif event_type == StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED:
                artifacts_by_student[student_id] = total
            elif event_type == StudentOutcomeEvent.EVENT_MILESTONE_EARNED:
                milestones_by_student[student_id] = total

    outcome_windows: dict[int, tuple[str, str]] = {}
    if student_ids:
        for row in (
            StudentOutcomeEvent.objects.filter(student_id__in=student_ids)
            .values("student_id")
            .annotate(first=models.Min("created_at"), last=models.Max("created_at"))
        ):
            student_id = int(row["student_id"])
            first = row.get("first")
            last = row.get("last")
            outcome_windows[student_id] = (
                first.isoformat() if first else "",
                last.isoformat() if last else "",
            )

    class_sessions_total = StudentOutcomeEvent.objects.filter(
        classroom=classroom,
        event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
    ).count()
    class_artifacts_total = StudentOutcomeEvent.objects.filter(
        classroom=classroom,
        event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
    ).count()
    class_milestones_total = StudentOutcomeEvent.objects.filter(
        classroom=classroom,
        event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
    ).count()
    class_active_outcome_students = (
        StudentOutcomeEvent.objects.filter(
            classroom=classroom,
            created_at__gte=active_since,
            student__isnull=False,
        )
        .values("student_id")
        .distinct()
        .count()
    )

    eligible_students = 0
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
            "session_completions": class_sessions_total,
            "artifact_submissions": class_artifacts_total,
            "milestones": class_milestones_total,
            "eligible_students": eligible_students,
            "total_students": len(students),
            "active_outcome_students": class_active_outcome_students,
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
                "first_outcome_at": first_outcome,
                "last_outcome_at": last_outcome,
                "certificate_min_sessions": certificate_min_sessions,
                "certificate_min_artifacts": certificate_min_artifacts,
                "active_window_days": active_window_days,
            }
        )

    return out.getvalue()


__all__ = [
    "build_dashboard_context",
    "export_class_outcomes_csv",
    "export_class_summary_csv",
    "export_submissions_today_archive",
]
