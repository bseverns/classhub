"""Syllabus export helpers for backup/catalog workflows."""

from __future__ import annotations

import csv
import io
import re

from .content_links import courses_dir
from .markdown_content import load_course_manifest
from .zip_exports import temporary_zip_archive

_COURSE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")

CATALOG_FIELDS = [
    "course_slug",
    "course_title",
    "program_profile",
    "ui_level",
    "grade_band",
    "age_band",
    "sessions",
    "default_duration_minutes",
    "helper_reference",
    "lesson_session",
    "lesson_slug",
    "lesson_title",
    "lesson_file",
    "lesson_helper_reference",
]


def list_syllabus_courses() -> list[dict]:
    root = courses_dir()
    if not root.exists():
        return []

    rows: list[dict] = []
    for manifest_path in sorted(root.glob("*/course.yaml")):
        course_slug = manifest_path.parent.name
        manifest = load_course_manifest(course_slug)
        lessons = manifest.get("lessons") or []
        rows.append(
            {
                "slug": course_slug,
                "title": str(manifest.get("title") or course_slug).strip(),
                "lesson_count": len(lessons) if isinstance(lessons, list) else 0,
            }
        )
    return rows


def build_syllabus_catalog_rows() -> list[dict]:
    course_rows = list_syllabus_courses()
    rows: list[dict] = []
    for course in course_rows:
        course_slug = str(course.get("slug") or "").strip()
        if not course_slug:
            continue
        manifest = load_course_manifest(course_slug)
        lessons = manifest.get("lessons") or []
        shared_fields = {
            "course_slug": course_slug,
            "course_title": str(manifest.get("title") or course_slug).strip(),
            "program_profile": str(manifest.get("program_profile") or "").strip(),
            "ui_level": str(manifest.get("ui_level") or "").strip(),
            "grade_band": str(manifest.get("grade_band") or "").strip(),
            "age_band": str(manifest.get("age_band") or "").strip(),
            "sessions": str(manifest.get("sessions") or "").strip(),
            "default_duration_minutes": str(manifest.get("default_duration_minutes") or "").strip(),
            "helper_reference": str(manifest.get("helper_reference") or "").strip(),
        }
        if not isinstance(lessons, list) or not lessons:
            rows.append(
                {
                    **shared_fields,
                    "lesson_session": "",
                    "lesson_slug": "",
                    "lesson_title": "",
                    "lesson_file": "",
                    "lesson_helper_reference": "",
                }
            )
            continue
        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            rows.append(
                {
                    **shared_fields,
                    "lesson_session": str(lesson.get("session") or "").strip(),
                    "lesson_slug": str(lesson.get("slug") or "").strip(),
                    "lesson_title": str(lesson.get("title") or "").strip(),
                    "lesson_file": str(lesson.get("file") or "").strip(),
                    "lesson_helper_reference": str(lesson.get("helper_reference") or "").strip(),
                }
            )
    return rows


def build_syllabus_catalog_csv() -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=CATALOG_FIELDS)
    writer.writeheader()
    for row in build_syllabus_catalog_rows():
        writer.writerow({key: row.get(key, "") for key in CATALOG_FIELDS})
    return out.getvalue()


def build_syllabus_backup_zip(*, course_slug: str = ""):
    root = courses_dir()
    if not root.exists():
        raise FileNotFoundError(f"Courses root does not exist: {root}")

    selected_slug = (course_slug or "").strip()
    if selected_slug:
        if not _COURSE_SLUG_RE.fullmatch(selected_slug):
            raise ValueError("Invalid course slug.")
        selected_dir = root / selected_slug
        if not selected_dir.exists() or not selected_dir.is_dir():
            raise FileNotFoundError(f"Course not found: {selected_slug}")
        selected_dirs = [selected_dir]
    else:
        selected_dirs = sorted(path for path in root.iterdir() if path.is_dir())

    file_count = 0
    with temporary_zip_archive() as (tmp, archive):
        for course_dir in selected_dirs:
            for file_path in sorted(path for path in course_dir.rglob("*") if path.is_file()):
                rel = file_path.relative_to(root.parent)
                archive.write(file_path, arcname=rel.as_posix())
                file_count += 1
        tmp.seek(0)
        return tmp, file_count, len(selected_dirs)


__all__ = [
    "CATALOG_FIELDS",
    "build_syllabus_backup_zip",
    "build_syllabus_catalog_csv",
    "build_syllabus_catalog_rows",
    "list_syllabus_courses",
]
