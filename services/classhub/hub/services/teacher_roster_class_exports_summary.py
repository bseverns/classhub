"""Class summary CSV helpers for teacher roster surfaces."""

from __future__ import annotations

import csv
from datetime import timedelta
from io import StringIO

from django.db import models
from django.utils import timezone

from ..models import Material, StudentEvent, StudentIdentity, StudentMaterialResponse, Submission
from .content_links import parse_course_lesson_url
from .markdown_content import load_lesson_markdown
from .telemetry_reads import student_events_queryset


def _student_event_totals(*, student_ids: list[int], event_type: str) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in (
        student_events_queryset()
        .filter(student_id__in=student_ids, event_type=event_type)
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        totals[int(row["student_id"])] = int(row["total"] or 0)
    return totals


def _submission_totals_by_student(*, student_ids: list[int]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in Submission.objects.filter(student_id__in=student_ids).values("student_id").annotate(total=models.Count("id")):
        totals[int(row["student_id"])] = int(row["total"] or 0)
    return totals


def _rubric_totals_by_student(*, student_ids: list[int]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in (
        StudentMaterialResponse.objects.filter(student_id__in=student_ids, material__type=Material.TYPE_RUBRIC)
        .values("student_id")
        .annotate(total=models.Count("id"))
    ):
        totals[int(row["student_id"])] = int(row["total"] or 0)
    return totals


def _build_lesson_summary_rows(*, classroom) -> list[dict]:
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
        submissions_total = Submission.objects.filter(material_id__in=upload_material_ids).count() if upload_material_ids else 0
        submitters_total = (
            Submission.objects.filter(material_id__in=upload_material_ids).values("student_id").distinct().count()
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
    return lesson_rows


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

    joins_by_student = _student_event_totals(student_ids=student_ids, event_type=StudentEvent.EVENT_CLASS_JOIN)
    helper_by_student = _student_event_totals(student_ids=student_ids, event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS)
    submissions_by_student = _submission_totals_by_student(student_ids=student_ids)
    rubric_by_student = _rubric_totals_by_student(student_ids=student_ids)
    lesson_rows = _build_lesson_summary_rows(classroom=classroom)

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


__all__ = ["export_class_summary_csv"]
