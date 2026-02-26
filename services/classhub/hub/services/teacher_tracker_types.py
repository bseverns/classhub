"""Typed contracts for teacher tracker service payloads."""

from __future__ import annotations

from typing import TypedDict

from django.utils import timezone

from ..models import Class, Module


class ClassDigestRow(TypedDict):
    classroom: Class
    student_total: int
    new_students_since: int
    submission_total_since: int
    helper_access_total_since: int
    students_without_submissions: int
    last_submission_at: timezone.datetime | None


class HelperSignalIntentRow(TypedDict):
    intent: str
    count: int


class HelperSignalStudentRow(TypedDict):
    student_id: int
    display_name: str
    chat_count: int
    primary_intent: str


class HelperSignalSnapshot(TypedDict):
    since: timezone.datetime
    window_hours: int
    total_events: int
    intent_rows: list[HelperSignalIntentRow]
    compacted_events: int
    avg_follow_up_suggestions: float
    busiest_students: list[HelperSignalStudentRow]


class LessonTrackerDropboxRow(TypedDict):
    id: int
    title: str
    submitted: int
    missing: int
    last_uploaded_at: timezone.datetime | None


class LessonTrackerHelperDefaults(TypedDict):
    context: str
    topics: list[str]
    allowed_topics: list[str]
    reference: str


class LessonTrackerHelperTuning(TypedDict):
    has_override: bool
    context_value: str
    topics_value: str
    allowed_topics_value: str
    reference_value: str
    default_context: str
    default_topics: list[str]
    default_allowed_topics: list[str]
    default_reference: str


class LessonTrackerRow(TypedDict):
    module: Module
    lesson_title: str
    lesson_url: str
    course_slug: str
    lesson_slug: str
    dropboxes: list[LessonTrackerDropboxRow]
    review_url: str
    review_label: str
    teacher_material_html: str
    release_state: dict[str, object]
    helper_tuning: LessonTrackerHelperTuning


__all__ = [
    "ClassDigestRow",
    "HelperSignalIntentRow",
    "HelperSignalSnapshot",
    "HelperSignalStudentRow",
    "LessonTrackerDropboxRow",
    "LessonTrackerHelperDefaults",
    "LessonTrackerHelperTuning",
    "LessonTrackerRow",
]

