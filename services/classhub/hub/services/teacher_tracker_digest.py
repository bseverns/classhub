"""Class digest helpers for teacher dashboard tracker panels."""

from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta

from django.db import models
from django.utils import timezone

from ..models import Class, StudentEvent, StudentIdentity, Submission
from .teacher_tracker_cache import _cache_get_or_build
from .teacher_tracker_types import ClassDigestRow
from .telemetry_reads import student_events_queryset


def _compute_class_digest_rows(classes: list[Class], *, since: timezone.datetime) -> list[ClassDigestRow]:
    class_ids = [int(c.id) for c in classes if c and c.id]
    if not class_ids:
        return []

    student_totals: dict[int, int] = {}
    for row in (
        StudentIdentity.objects.filter(classroom_id__in=class_ids)
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        student_totals[int(row["classroom_id"])] = int(row["total"] or 0)

    students_with_submissions: dict[int, int] = {}
    for row in (
        Submission.objects.filter(student__classroom_id__in=class_ids)
        .values("student__classroom_id")
        .annotate(total=models.Count("student_id", distinct=True))
    ):
        students_with_submissions[int(row["student__classroom_id"])] = int(row["total"] or 0)

    submission_totals_since: dict[int, int] = {}
    for row in (
        Submission.objects.filter(
            material__module__classroom_id__in=class_ids,
            uploaded_at__gte=since,
        )
        .values("material__module__classroom_id")
        .annotate(total=models.Count("id"))
    ):
        submission_totals_since[int(row["material__module__classroom_id"])] = int(row["total"] or 0)

    helper_events_since: dict[int, int] = {}
    for row in (
        student_events_queryset().filter(
            classroom_id__in=class_ids,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            created_at__gte=since,
        )
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        helper_events_since[int(row["classroom_id"])] = int(row["total"] or 0)

    new_students_since: dict[int, int] = {}
    for row in (
        StudentIdentity.objects.filter(
            classroom_id__in=class_ids,
            created_at__gte=since,
        )
        .values("classroom_id")
        .annotate(total=models.Count("id"))
    ):
        new_students_since[int(row["classroom_id"])] = int(row["total"] or 0)

    last_submission_at: dict[int, timezone.datetime] = {}
    for row in (
        Submission.objects.filter(material__module__classroom_id__in=class_ids)
        .values("material__module__classroom_id")
        .annotate(last_uploaded_at=models.Max("uploaded_at"))
    ):
        class_id = int(row["material__module__classroom_id"])
        last_submission_at[class_id] = row["last_uploaded_at"]

    rows: list[ClassDigestRow] = []
    for classroom in classes:
        classroom_id = int(classroom.id)
        student_total = int(student_totals.get(classroom_id, 0))
        with_submissions = int(students_with_submissions.get(classroom_id, 0))
        students_without_submissions = max(student_total - with_submissions, 0)
        rows.append(
            {
                "classroom": classroom,
                "student_total": student_total,
                "new_students_since": int(new_students_since.get(classroom_id, 0)),
                "submission_total_since": int(submission_totals_since.get(classroom_id, 0)),
                "helper_access_total_since": int(helper_events_since.get(classroom_id, 0)),
                "students_without_submissions": students_without_submissions,
                "last_submission_at": last_submission_at.get(classroom_id),
            }
        )
    return rows


def _serialize_class_digest_rows(rows: list[ClassDigestRow]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for row in rows:
        classroom = row.get("classroom")
        if not classroom or not getattr(classroom, "id", None):
            continue
        payload.append(
            {
                "classroom_id": int(classroom.id),
                "student_total": int(row.get("student_total") or 0),
                "new_students_since": int(row.get("new_students_since") or 0),
                "submission_total_since": int(row.get("submission_total_since") or 0),
                "helper_access_total_since": int(row.get("helper_access_total_since") or 0),
                "students_without_submissions": int(row.get("students_without_submissions") or 0),
                "last_submission_at": row.get("last_submission_at"),
            }
        )
    return payload


def _hydrate_class_digest_rows(payload: list[dict[str, object]], classes: list[Class]) -> list[ClassDigestRow]:
    classes_by_id = {int(classroom.id): classroom for classroom in classes if getattr(classroom, "id", None)}
    hydrated: list[ClassDigestRow] = []
    for cached in payload:
        try:
            classroom_id = int(cached.get("classroom_id") or 0)
        except Exception:
            classroom_id = 0
        classroom = classes_by_id.get(classroom_id)
        if classroom is None:
            continue
        hydrated.append(
            {
                "classroom": classroom,
                "student_total": int(cached.get("student_total") or 0),
                "new_students_since": int(cached.get("new_students_since") or 0),
                "submission_total_since": int(cached.get("submission_total_since") or 0),
                "helper_access_total_since": int(cached.get("helper_access_total_since") or 0),
                "students_without_submissions": int(cached.get("students_without_submissions") or 0),
                "last_submission_at": cached.get("last_submission_at"),
            }
        )
    return hydrated


def _build_class_digest_rows(classes: list[Class], *, since: timezone.datetime) -> list[ClassDigestRow]:
    class_signature = ",".join(
        f"{int(classroom.id)}:{int(getattr(classroom, 'session_epoch', 0) or 0)}"
        for classroom in classes
        if getattr(classroom, "id", None)
    )
    # Cache in minute windows so near-identical requests coalesce.
    since_bucket = int(since.timestamp()) // 60
    cached_payload = _cache_get_or_build(
        "class-digest",
        key_parts=[class_signature, str(since_bucket)],
        builder=lambda: _serialize_class_digest_rows(_compute_class_digest_rows(classes, since=since)),
    )
    if not isinstance(cached_payload, list):
        return _compute_class_digest_rows(classes, since=since)
    return _hydrate_class_digest_rows(cached_payload, classes)


def _local_day_window() -> tuple[timezone.datetime, timezone.datetime]:
    today = timezone.localdate()
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, dt_time.min), zone)
    end = start + timedelta(days=1)
    return start, end


__all__ = ["_build_class_digest_rows", "_local_day_window"]
