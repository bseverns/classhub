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
}

SUPPORTED_EXTENSIONS = {".md", ".docx", ".zip"}
TEXT_EXTENSIONS = {".md", ".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
COURSE_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")
ZIP_SESSION_PATH_RE = re.compile(r"(?:^|/)(sessions?|lessons?)/", re.IGNORECASE)
ZIP_SESSION_FILE_RE = re.compile(r"(?:^|[_\-\s])session[_\-\s]*(\d{1,2})\b", re.IGNORECASE)


class SyllabusIngestError(ValueError):
    """Raised when uploaded syllabus input cannot be parsed safely."""


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
]
