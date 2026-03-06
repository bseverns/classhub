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
    StudentOutcomeEvent,
    StudentSupportTag,
    Submission,
)
from .content_links import parse_course_lesson_url
from .filenames import safe_filename
from .markdown_content import load_lesson_markdown
from .telemetry_reads import student_events_queryset, student_outcome_events_queryset
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


def _support_tag_choices() -> list[dict[str, str]]:
    return [{"value": str(value), "label": str(label)} for value, label in StudentSupportTag.TAG_CHOICES]


def _support_tags_by_student(*, classroom, students: list[StudentIdentity]) -> dict[int, list[dict[str, str]]]:
    by_student: dict[int, list[dict[str, str]]] = {}
    student_ids = [int(student.id) for student in students if getattr(student, "id", None) is not None]
    if not student_ids:
        return by_student
    rows = (
        StudentSupportTag.objects.filter(classroom=classroom, student_id__in=student_ids)
        .values("student_id", "tag")
        .order_by("student_id", "tag", "-id")
    )
    for row in rows:
        student_id = int(row["student_id"])
        tag = str(row["tag"] or "")
        if not tag:
            continue
        bucket = by_student.setdefault(student_id, [])
        bucket.append({"value": tag, "label": StudentSupportTag.label_for(tag)})
    return by_student


def build_certificate_eligibility_rows(
    *,
    classroom,
    students: list[StudentIdentity] | None = None,
    certificate_min_sessions: int | None = None,
    certificate_min_artifacts: int | None = None,
) -> dict:
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
    if students is None:
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
            student_outcome_events_queryset().filter(classroom_id=int(classroom.id), student_id__in=student_ids)
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

    eligible_students = 0
    rows: list[dict] = []
    for student in students:
        student_id = int(student.id)
        session_count = int(sessions_by_student.get(student_id, 0))
        artifact_count = int(artifacts_by_student.get(student_id, 0))
        milestone_count = int(milestones_by_student.get(student_id, 0))
        certificate_eligible = (
            session_count >= certificate_min_sessions and artifact_count >= certificate_min_artifacts
        )
        if certificate_eligible:
            eligible_students += 1
        rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "session_count": session_count,
                "artifact_count": artifact_count,
                "milestone_count": milestone_count,
                "certificate_eligible": certificate_eligible,
            }
        )
    return {
        "rows": rows,
        "eligible_students": int(eligible_students),
        "total_students": len(students),
        "certificate_min_sessions": int(certificate_min_sessions),
        "certificate_min_artifacts": int(certificate_min_artifacts),
    }


def _build_outcome_snapshot(*, classroom, students: list[StudentIdentity]) -> dict:
    window_days = _int_setting("CLASSHUB_OUTCOME_WINDOW_DAYS", 30)
    top_students_limit = _int_setting("CLASSHUB_OUTCOME_TOP_STUDENTS", 5)
    certificate_min_sessions = _int_setting("CLASSHUB_CERTIFICATE_MIN_SESSIONS", 8)
    certificate_min_artifacts = _int_setting("CLASSHUB_CERTIFICATE_MIN_ARTIFACTS", 6)
    active_since = timezone.now() - timedelta(days=window_days)

    student_ids = [int(student.id) for student in students]
    sessions_by_student: dict[int, int] = {}
    artifacts_by_student: dict[int, int] = {}
    milestones_by_student: dict[int, int] = {}
    if student_ids:
        for row in (
            student_outcome_events_queryset().filter(student_id__in=student_ids)
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

    total_sessions = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
    ).count()
    total_artifacts = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
    ).count()
    total_milestones = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
    ).count()
    active_students = (
        student_outcome_events_queryset().filter(
            classroom_id=int(classroom.id),
            created_at__gte=active_since,
            student_id__isnull=False,
        )
        .values("student_id")
        .distinct()
        .count()
    )

    eligible_students = 0
    rows: list[dict] = []
    for student in students:
        sid = int(student.id)
        sessions = sessions_by_student.get(sid, 0)
        artifacts = artifacts_by_student.get(sid, 0)
        milestones = milestones_by_student.get(sid, 0)
        eligible = sessions >= certificate_min_sessions and artifacts >= certificate_min_artifacts
        if eligible:
            eligible_students += 1
        if sessions or artifacts or milestones:
            rows.append(
                {
                    "display_name": student.display_name,
                    "session_count": sessions,
                    "artifact_count": artifacts,
                    "milestone_count": milestones,
                    "certificate_eligible": eligible,
                }
            )
    rows.sort(
        key=lambda row: (
            -int(row["session_count"]),
            -int(row["artifact_count"]),
            -int(row["milestone_count"]),
            str(row["display_name"]).lower(),
        )
    )

    return {
        "window_days": window_days,
        "total_sessions": int(total_sessions),
        "total_artifacts": int(total_artifacts),
        "total_milestones": int(total_milestones),
        "active_students": int(active_students),
        "eligible_students": int(eligible_students),
        "total_students": len(students),
        "certificate_min_sessions": certificate_min_sessions,
        "certificate_min_artifacts": certificate_min_artifacts,
        "top_students": rows[:top_students_limit],
    }


def _detail_int(details: dict, key: str) -> int:
    try:
        return int((details or {}).get(key) or 0)
    except Exception:
        return 0


def _build_facilitator_support_snapshot(*, classroom, students: list[StudentIdentity], modules: list[Module]) -> dict:
    now = timezone.now()
    module_titles = {int(module.id): str(module.title) for module in modules}
    material_rows = Material.objects.filter(module__classroom=classroom).values("id", "title", "module_id")
    material_lookup: dict[int, dict] = {}
    for row in material_rows:
        material_lookup[int(row["id"])] = {
            "title": str(row["title"] or ""),
            "module_title": module_titles.get(int(row["module_id"] or 0), ""),
        }
    student_by_id = {int(student.id): student for student in students}

    micro_event_types = {
        StudentEvent.EVENT_MICRO_CHECK_CAN_DO_THIS,
        StudentEvent.EVENT_MICRO_CHECK_STUCK,
        StudentEvent.EVENT_MICRO_CHECK_TAUGHT_SOMEONE,
    }
    activity_events = student_events_queryset().filter(
        classroom_id=int(classroom.id),
        student_id__isnull=False,
        event_type__in=list(micro_event_types | {StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED}),
    ).only("student_id", "event_type", "details", "created_at").order_by("-created_at", "-id")

    latest_signal_by_student: dict[int, StudentEvent] = {}
    latest_stuck_by_student: dict[int, StudentEvent] = {}
    latest_resolved_by_student: dict[int, StudentEvent] = {}
    for event in activity_events:
        student_id = int(event.student_id or 0)
        if student_id <= 0:
            continue
        if event.event_type in micro_event_types and student_id not in latest_signal_by_student:
            latest_signal_by_student[student_id] = event
        if event.event_type == StudentEvent.EVENT_MICRO_CHECK_STUCK and student_id not in latest_stuck_by_student:
            latest_stuck_by_student[student_id] = event
        if event.event_type == StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED and student_id not in latest_resolved_by_student:
            latest_resolved_by_student[student_id] = event

    stuck_rows: list[dict] = []
    for student_id, stuck_event in latest_stuck_by_student.items():
        student = student_by_id.get(student_id)
        if student is None:
            continue
        resolved_event = latest_resolved_by_student.get(student_id)
        if resolved_event and resolved_event.created_at >= stuck_event.created_at:
            continue
        latest_signal = latest_signal_by_student.get(student_id)
        if latest_signal and latest_signal.created_at > stuck_event.created_at and latest_signal.event_type != StudentEvent.EVENT_MICRO_CHECK_STUCK:
            continue
        module_id = _detail_int(stuck_event.details, "module_id")
        waiting_minutes = max(int((now - stuck_event.created_at).total_seconds() // 60), 0)
        stuck_rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "module_id": module_id,
                "module_title": module_titles.get(module_id, ""),
                "requested_at": stuck_event.created_at,
                "waiting_minutes": waiting_minutes,
            }
        )
    stuck_rows.sort(
        key=lambda row: (
            -int(row["waiting_minutes"]),
            str(row["display_name"]).lower(),
        )
    )

    delete_request_events = (
        student_events_queryset().filter(
            classroom_id=int(classroom.id),
            student_id__isnull=False,
            event_type__in=[
                StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
                StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
            ],
        )
        .only("student_id", "event_type", "created_at")
        .order_by("-created_at", "-id")
    )
    latest_delete_request_by_student: dict[int, StudentEvent] = {}
    latest_delete_resolved_by_student: dict[int, StudentEvent] = {}
    for event in delete_request_events:
        student_id = int(event.student_id or 0)
        if student_id <= 0:
            continue
        if (
            event.event_type == StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST
            and student_id not in latest_delete_request_by_student
        ):
            latest_delete_request_by_student[student_id] = event
        if (
            event.event_type == StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED
            and student_id not in latest_delete_resolved_by_student
        ):
            latest_delete_resolved_by_student[student_id] = event

    delete_request_rows: list[dict] = []
    for student_id, request_event in latest_delete_request_by_student.items():
        student = student_by_id.get(student_id)
        if student is None:
            continue
        resolved_event = latest_delete_resolved_by_student.get(student_id)
        if resolved_event and resolved_event.created_at >= request_event.created_at:
            continue
        waiting_minutes = max(int((now - request_event.created_at).total_seconds() // 60), 0)
        delete_request_rows.append(
            {
                "student_id": student_id,
                "display_name": student.display_name,
                "requested_at": request_event.created_at,
                "waiting_minutes": waiting_minutes,
            }
        )
    delete_request_rows.sort(
        key=lambda row: (
            -int(row["waiting_minutes"]),
            str(row["display_name"]).lower(),
        )
    )

    upload_error_limit = _int_setting("CLASSHUB_UPLOAD_ERROR_FEED_LIMIT", 10)
    upload_error_rows: list[dict] = []
    recent_upload_errors = (
        student_events_queryset().filter(
            classroom_id=int(classroom.id),
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD_ERROR,
            student_id__isnull=False,
        )
        .only("student_id", "details", "created_at")
        .order_by("-created_at", "-id")[:upload_error_limit]
    )
    for event in recent_upload_errors:
        student_id = int(event.student_id or 0)
        student = student_by_id.get(student_id)
        if student is None:
            continue
        details = event.details if isinstance(event.details, dict) else {}
        material_id = _detail_int(details, "material_id")
        material_meta = material_lookup.get(material_id, {})
        reason_code = str(details.get("reason_code") or "").strip() or "upload_error"
        upload_error_rows.append(
            {
                "display_name": student.display_name,
                "material_title": str(material_meta.get("title") or ""),
                "module_title": str(material_meta.get("module_title") or ""),
                "reason_code": reason_code.replace("_", " "),
                "created_at": event.created_at,
            }
        )

    idle_minutes_threshold = _int_setting("CLASSHUB_FACILITATOR_IDLE_MINUTES", 20)
    idle_rows: list[dict] = []
    for student in students:
        if student.last_seen_at is None:
            continue
        idle_minutes = int((now - student.last_seen_at).total_seconds() // 60)
        if idle_minutes < idle_minutes_threshold:
            continue
        idle_rows.append(
            {
                "student_id": int(student.id),
                "display_name": student.display_name,
                "idle_minutes": max(idle_minutes, 0),
                "last_seen_at": student.last_seen_at,
            }
        )
    idle_rows.sort(key=lambda row: (-int(row["idle_minutes"]), str(row["display_name"]).lower()))
    idle_rows = idle_rows[: _int_setting("CLASSHUB_FACILITATOR_IDLE_LIST_LIMIT", 12)]

    return {
        "generated_at": now,
        "stuck_rows": stuck_rows,
        "stuck_count": len(stuck_rows),
        "delete_request_rows": delete_request_rows,
        "delete_request_count": len(delete_request_rows),
        "upload_error_rows": upload_error_rows,
        "upload_error_count": len(upload_error_rows),
        "idle_rows": idle_rows,
        "idle_minutes_threshold": idle_minutes_threshold,
    }


def build_dashboard_context(*, request, classroom, normalize_order_fn) -> dict:
    modules = list(classroom.modules.prefetch_related("materials").all())
    modules.sort(key=lambda module: (module.order_index, module.id))
    normalize_order_fn(modules)
    modules = list(classroom.modules.prefetch_related("materials").all())
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
            student_outcome_events_queryset().filter(student_id__in=student_ids)
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
            student_outcome_events_queryset().filter(student_id__in=student_ids)
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

    class_sessions_total = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
    ).count()
    class_artifacts_total = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
    ).count()
    class_milestones_total = student_outcome_events_queryset().filter(
        classroom_id=int(classroom.id),
        event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
    ).count()
    class_active_outcome_students = (
        student_outcome_events_queryset().filter(
            classroom_id=int(classroom.id),
            created_at__gte=active_since,
            student_id__isnull=False,
        )
        .values("student_id")
        .distinct()
        .count()
    )

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
            "session_completions": class_sessions_total,
            "artifact_submissions": class_artifacts_total,
            "milestones": class_milestones_total,
            "eligible_students": eligible_students,
            "certificate_issued_students": len(issued_by_student),
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
