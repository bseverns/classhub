"""Contracts and constants shared by syllabus ingest helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SESSION_CONNECTORS_TEMPLATE = {":"}
_SESSION_CONNECTORS_VERBOSE = {":", "-", "–", "—"}
_GRADE_RANGE_CONNECTORS = {"-", "to", "through"}
_SESSION_COUNT_UNITS = {"session", "sessions", "meeting", "meetings", "week", "weeks"}
HANDOUT_READING_LEVELS = ("simple", "standard")

UI_LEVEL_VALUES = {"elementary", "secondary", "advanced"}
UI_LEVEL_ALIASES = {
    "elementary": "elementary",
    "primary": "elementary",
    "k5": "elementary",
    "k_5": "elementary",
    "k-5": "elementary",
    "k6": "elementary",
    "k_6": "elementary",
    "k-6": "elementary",
    "secondary": "secondary",
    "middle": "secondary",
    "middle_school": "secondary",
    "high": "secondary",
    "high_school": "secondary",
    "advanced": "advanced",
    "adult": "advanced",
    "college": "advanced",
    "post_secondary": "advanced",
}

META_KEY_ALIASES = {
    "grade level": "grade_band",
    "grade band": "grade_band",
    "grades": "grade_band",
    "age band": "age_band",
    "ages": "age_band",
    "meeting time": "meeting_time",
    "meetingtime": "meeting_time",
    "session length": "session_length",
    "duration": "duration",
    "total sessions": "total_sessions",
    "sessions": "total_sessions",
    "program profile": "program_profile",
    "ui level": "ui_level",
    "learner level": "learner_level",
    "platform": "platform",
}

SECTION_NAMES = {
    "teacher prep",
    "materials",
    "agenda",
    "checkpoints",
    "common stuck points + fixes",
    "common stuck points",
    "stuck points",
    "extensions",
    "local anchors",
    "example variants",
    "community glossary",
    "offline handout",
    "submission",
    "classhub materials",
}

SUPPORTED_EXTENSIONS = {".md", ".docx", ".zip"}
TEXT_EXTENSIONS = {".md", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
COURSE_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")
LESSON_SLUG_RE = re.compile(r"^s(?P<session>\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*$")
ZIP_SESSION_PATH_RE = re.compile(r"(?:^|/)(sessions?|lessons?)/", re.IGNORECASE)
ZIP_SESSION_FILE_RE = re.compile(r"(?:^|[_\-\s])session[_\-\s]*(\d{1,2})\b", re.IGNORECASE)


class SyllabusIngestError(ValueError):
    """Raised when uploaded syllabus input cannot be parsed safely."""


def validate_final_lesson_slugs(sessions: list[dict]) -> None:
    """Validate explicit lesson slugs and reject duplicate compiled slugs."""
    seen: set[str] = set()
    for session in sessions:
        session_num = int(session.get("session") or 0)
        title = str(session.get("title") or "").strip()
        explicit_slug = str(session.get("lesson_slug") or "").strip()
        if explicit_slug:
            match = LESSON_SLUG_RE.fullmatch(explicit_slug)
            if not match:
                raise SyllabusIngestError(
                    f"Lesson slug for session {session_num:02d} must use sNN-lowercase-dashes format."
                )
            if int(match.group("session")) != session_num:
                raise SyllabusIngestError(
                    f"Lesson slug '{explicit_slug}' does not match session {session_num:02d}."
                )
            final_slug = explicit_slug
        else:
            title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "session"
            final_slug = f"s{session_num:02d}-{title_slug}"
        if final_slug in seen:
            raise SyllabusIngestError(f"Duplicate lesson slug: {final_slug}")
        seen.add(final_slug)


@dataclass(frozen=True)
class SyllabusIngestResult:
    course_slug: str
    course_title: str
    course_dir: Path
    lesson_count: int
    source_kind: str
    source_files: list[str]
    ui_level: str


@dataclass(frozen=True)
class _ZipTextDoc:
    path: str
    text: str
    size: int
    suffix: str


@dataclass(frozen=True)
class _ZipLessonImage:
    path: str
    session: int
    output_filename: str
    raw: bytes


__all__ = [
    "COURSE_SLUG_RE",
    "HANDOUT_READING_LEVELS",
    "LESSON_SLUG_RE",
    "IMAGE_EXTENSIONS",
    "META_KEY_ALIASES",
    "SECTION_NAMES",
    "SUPPORTED_EXTENSIONS",
    "TEXT_EXTENSIONS",
    "UI_LEVEL_ALIASES",
    "UI_LEVEL_VALUES",
    "ZIP_SESSION_FILE_RE",
    "ZIP_SESSION_PATH_RE",
    "SyllabusIngestError",
    "SyllabusIngestResult",
    "_GRADE_RANGE_CONNECTORS",
    "_SESSION_CONNECTORS_TEMPLATE",
    "_SESSION_CONNECTORS_VERBOSE",
    "_SESSION_COUNT_UNITS",
    "_ZipLessonImage",
    "_ZipTextDoc",
    "validate_final_lesson_slugs",
]
