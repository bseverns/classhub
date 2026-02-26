"""Teacher tracker service helpers."""

from datetime import datetime, time as dt_time, timedelta
import re

from django.db import models
from django.utils import timezone

from ..models import (
    Class,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
)
from .content_links import parse_course_lesson_url
from .helper_topics import build_allowed_topics, build_lesson_topics
from .markdown_content import load_lesson_markdown, load_teacher_material_html
from .release_state import lesson_release_override_map, lesson_release_state
from .teacher_tracker_types import (
    ClassDigestRow,
    HelperSignalIntentRow,
    HelperSignalSnapshot,
    HelperSignalStudentRow,
    LessonTrackerDropboxRow,
    LessonTrackerHelperDefaults,
    LessonTrackerRow,
)

_SAFE_INTENT_RE = re.compile(r"^[a-z0-9_-]{1,32}$")


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


def _build_class_digest_rows(classes: list[Class], *, since: timezone.datetime) -> list[ClassDigestRow]:
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


def _local_day_window() -> tuple[timezone.datetime, timezone.datetime]:
    today = timezone.localdate()
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, dt_time.min), zone)
    end = start + timedelta(days=1)
    return start, end


def _build_helper_signal_snapshot(
    *,
    classroom: Class,
    students: list[StudentIdentity],
    window_hours: int = 24,
    top_students: int = 5,
) -> HelperSignalSnapshot:
    window_hours = max(int(window_hours), 1)
    top_students = max(int(top_students), 1)
    since = timezone.now() - timedelta(hours=window_hours)

    rows = list(
        StudentEvent.objects.filter(
            classroom=classroom,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            created_at__gte=since,
        ).values("student_id", "details")
    )

    total_events = len(rows)
    intent_counts: dict[str, int] = {}
    compacted_events = 0
    follow_up_total = 0
    student_counts: dict[int, dict] = {}

    for row in rows:
        details = row.get("details")
        if not isinstance(details, dict):
            details = {}

        intent = str(details.get("intent") or "").strip().lower()
        if intent and _SAFE_INTENT_RE.fullmatch(intent):
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        if bool(details.get("conversation_compacted")):
            compacted_events += 1

        try:
            follow_count = int(details.get("follow_up_suggestions_count") or 0)
        except Exception:
            follow_count = 0
        if follow_count > 0:
            follow_up_total += follow_count

        try:
            student_id = int(row.get("student_id") or 0)
        except Exception:
            student_id = 0
        if student_id <= 0:
            continue
        bucket = student_counts.setdefault(student_id, {"chat_count": 0, "intent_counts": {}})
        bucket["chat_count"] += 1
        if intent and _SAFE_INTENT_RE.fullmatch(intent):
            intent_bucket: dict[str, int] = bucket["intent_counts"]
            intent_bucket[intent] = intent_bucket.get(intent, 0) + 1

    intent_rows: list[HelperSignalIntentRow] = [
        {"intent": intent, "count": count}
        for intent, count in sorted(intent_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    names_by_student_id = {int(st.id): st.display_name for st in students if getattr(st, "id", None)}
    busiest_students: list[HelperSignalStudentRow] = []
    for student_id, bucket in student_counts.items():
        intent_bucket: dict[str, int] = bucket.get("intent_counts") or {}
        if intent_bucket:
            primary_intent = sorted(intent_bucket.items(), key=lambda item: (-item[1], item[0]))[0][0]
        else:
            primary_intent = ""
        busiest_students.append(
            {
                "student_id": student_id,
                "display_name": names_by_student_id.get(student_id, f"Student #{student_id}"),
                "chat_count": int(bucket.get("chat_count") or 0),
                "primary_intent": primary_intent,
            }
        )
    busiest_students.sort(key=lambda row: (-row["chat_count"], row["display_name"].lower()))

    if total_events > 0:
        avg_follow = round(float(follow_up_total) / float(total_events), 1)
    else:
        avg_follow = 0.0

    return {
        "since": since,
        "window_hours": window_hours,
        "total_events": total_events,
        "intent_rows": intent_rows,
        "compacted_events": compacted_events,
        "avg_follow_up_suggestions": avg_follow,
        "busiest_students": busiest_students[:top_students],
    }


def _build_lesson_tracker_rows(
    request, classroom_id: int, modules: list[Module], student_count: int
) -> list[LessonTrackerRow]:
    rows: list[LessonTrackerRow] = []
    upload_material_ids = []
    module_materials_map: dict[int, list[Material]] = {}
    teacher_material_html_by_lesson: dict[tuple[str, str], str] = {}
    lesson_title_by_lesson: dict[tuple[str, str], str] = {}
    lesson_release_by_lesson: dict[tuple[str, str], dict] = {}
    helper_defaults_by_lesson: dict[tuple[str, str], LessonTrackerHelperDefaults] = {}
    release_override_map = lesson_release_override_map(classroom_id)

    for module in modules:
        prefetched = getattr(module, "_prefetched_objects_cache", {}).get("materials")
        if prefetched is None:
            raise ValueError(
                "lesson tracker requires modules prefetched with materials; use prefetch_related('materials')"
            )
        mats = list(prefetched)
        mats.sort(key=lambda m: (m.order_index, m.id))
        module_materials_map[module.id] = mats
        for mat in mats:
            if mat.type == Material.TYPE_UPLOAD:
                upload_material_ids.append(mat.id)

    submission_counts = _material_submission_counts(upload_material_ids)
    latest_upload_map = _material_latest_upload_map(upload_material_ids)

    for module in modules:
        mats = module_materials_map.get(module.id, [])
        dropboxes: list[LessonTrackerDropboxRow] = []
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
                    "topics": build_lesson_topics(front_matter),
                    "allowed_topics": build_allowed_topics(front_matter),
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


__all__ = [
    "_material_submission_counts",
    "_material_latest_upload_map",
    "_build_class_digest_rows",
    "_local_day_window",
    "_build_helper_signal_snapshot",
    "_build_lesson_tracker_rows",
]
