"""Teacher lesson tracker and digest helper functions."""

from datetime import datetime, time as dt_time, timedelta

from django.db import models
from django.utils import timezone

from ...models import (
    Class,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
)
from ...services.content_links import parse_course_lesson_url
from ...services.markdown_content import load_lesson_markdown, load_teacher_material_html
from ...services.release_state import lesson_release_override_map, lesson_release_state
from ..content import _build_allowed_topics, _build_lesson_topics


def _material_submission_counts(material_ids: list[int]) -> dict[int, int]:
    counts = {}
    if not material_ids:
        return counts
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id", "student_id")
        .distinct()
    )
    for row in rows:
        material_id = int(row["material_id"])
        counts[material_id] = counts.get(material_id, 0) + 1
    return counts


def _material_latest_upload_map(material_ids: list[int]) -> dict[int, timezone.datetime]:
    latest = {}
    if not material_ids:
        return latest
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id")
        .annotate(last_uploaded_at=models.Max("uploaded_at"))
    )
    for row in rows:
        latest[int(row["material_id"])] = row["last_uploaded_at"]
    return latest


def _build_class_digest_rows(classes: list[Class], *, since: timezone.datetime) -> list[dict]:
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
        StudentEvent.objects.filter(
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

    rows: list[dict] = []
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


def _local_day_window() -> tuple[timezone.datetime, timezone.datetime]:
    today = timezone.localdate()
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, dt_time.min), zone)
    end = start + timedelta(days=1)
    return start, end


def _build_lesson_tracker_rows(request, classroom_id: int, modules: list[Module], student_count: int) -> list[dict]:
    rows: list[dict] = []
    upload_material_ids = []
    module_materials_map: dict[int, list[Material]] = {}
    teacher_material_html_by_lesson: dict[tuple[str, str], str] = {}
    lesson_title_by_lesson: dict[tuple[str, str], str] = {}
    lesson_release_by_lesson: dict[tuple[str, str], dict] = {}
    helper_defaults_by_lesson: dict[tuple[str, str], dict] = {}
    release_override_map = lesson_release_override_map(classroom_id)

    for module in modules:
        mats = list(module.materials.all())
        mats.sort(key=lambda m: (m.order_index, m.id))
        module_materials_map[module.id] = mats
        for mat in mats:
            if mat.type == Material.TYPE_UPLOAD:
                upload_material_ids.append(mat.id)

    submission_counts = _material_submission_counts(upload_material_ids)
    latest_upload_map = _material_latest_upload_map(upload_material_ids)

    for module in modules:
        mats = module_materials_map.get(module.id, [])
        dropboxes = []
        for mat in mats:
            if mat.type != Material.TYPE_UPLOAD:
                continue
            submitted = submission_counts.get(mat.id, 0)
            dropboxes.append(
                {
                    "id": mat.id,
                    "title": mat.title,
                    "submitted": submitted,
                    "missing": max(student_count - submitted, 0),
                    "last_uploaded_at": latest_upload_map.get(mat.id),
                }
            )

        review_dropbox = None
        if dropboxes:
            review_dropbox = max(dropboxes, key=lambda d: (d["missing"], d["submitted"], -int(d["id"])))

        if review_dropbox and review_dropbox["missing"] > 0:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions?show=missing"
            review_label = f"Review missing now ({review_dropbox['missing']})"
        elif review_dropbox:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions"
            review_label = "Review submissions"
        else:
            review_url = ""
            review_label = ""

        seen_lessons = set()
        for mat in mats:
            if mat.type != Material.TYPE_LINK:
                continue
            parsed = parse_course_lesson_url(mat.url)
            if not parsed:
                continue
            lesson_key = parsed
            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)
            course_slug, lesson_slug = parsed

            if lesson_key not in teacher_material_html_by_lesson:
                teacher_material_html_by_lesson[lesson_key] = load_teacher_material_html(course_slug, lesson_slug)
                try:
                    front_matter, _body_markdown, lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
                except ValueError:
                    front_matter = {}
                    lesson_meta = {}
                lesson_title_by_lesson[lesson_key] = (
                    str(front_matter.get("title") or "").strip() or mat.title
                )
                helper_defaults_by_lesson[lesson_key] = {
                    "context": str(front_matter.get("title") or lesson_slug).strip() or lesson_slug,
                    "topics": _build_lesson_topics(front_matter),
                    "allowed_topics": _build_allowed_topics(front_matter),
                    "reference": str(lesson_meta.get("helper_reference") or "").strip(),
                }
                lesson_release_by_lesson[lesson_key] = lesson_release_state(
                    request,
                    front_matter,
                    lesson_meta,
                    classroom_id=classroom_id,
                    course_slug=course_slug,
                    lesson_slug=lesson_slug,
                    override_map=release_override_map,
                    respect_staff_bypass=False,
                )

            release_override = release_override_map.get(lesson_key)
            helper_context_override = (getattr(release_override, "helper_context_override", "") or "").strip()
            helper_topics_override = (getattr(release_override, "helper_topics_override", "") or "").strip()
            helper_allowed_topics_override = (getattr(release_override, "helper_allowed_topics_override", "") or "").strip()
            helper_reference_override = (getattr(release_override, "helper_reference_override", "") or "").strip()
            has_helper_override = bool(
                helper_context_override
                or helper_topics_override
                or helper_allowed_topics_override
                or helper_reference_override
            )

            helper_defaults = helper_defaults_by_lesson.get(
                lesson_key,
                {"context": lesson_slug, "topics": [], "allowed_topics": [], "reference": ""},
            )
            rows.append(
                {
                    "module": module,
                    "lesson_title": lesson_title_by_lesson.get(lesson_key, mat.title),
                    "lesson_url": mat.url,
                    "course_slug": course_slug,
                    "lesson_slug": lesson_slug,
                    "dropboxes": dropboxes,
                    "review_url": review_url,
                    "review_label": review_label,
                    "teacher_material_html": teacher_material_html_by_lesson.get(lesson_key, ""),
                    "release_state": lesson_release_by_lesson.get(lesson_key, {}),
                    "helper_tuning": {
                        "has_override": has_helper_override,
                        "context_value": helper_context_override,
                        "topics_value": helper_topics_override,
                        "allowed_topics_value": helper_allowed_topics_override,
                        "reference_value": helper_reference_override,
                        "default_context": helper_defaults.get("context", ""),
                        "default_topics": helper_defaults.get("topics", []),
                        "default_allowed_topics": helper_defaults.get("allowed_topics", []),
                        "default_reference": helper_defaults.get("reference", ""),
                    },
                }
            )

    return rows


__all__ = [name for name in globals() if not name.startswith("__")]
