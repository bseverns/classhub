#!/usr/bin/env python3
"""Guardrail: lesson front matter course slug must match its course folder slug."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


COURSES_ROOT = Path("services/classhub/content/courses")
COURSE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
FRONT_MATTER_KEY_RE = re.compile(r"^(course|course_slug)\s*:\s*(.+?)\s*$", flags=re.MULTILINE)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course-slug", default="", help="Validate only one course folder slug")
    return parser.parse_args()


def _read_front_matter(path: Path) -> tuple[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive IO guard
        return "", f"{path}: unable to read lesson markdown: {exc}"
    if not raw.startswith("---"):
        return "", f"{path}: missing front matter block (expected leading '---')"
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return "", f"{path}: unterminated front matter block"
    return parts[1], ""


def _normalize_scalar(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        return ""
    if value[0] in {"'", '"'} and len(value) >= 2 and value[-1] == value[0]:
        return value[1:-1].strip()
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    return value


def _extract_course_values(front_matter: str) -> tuple[str, str]:
    values: dict[str, str] = {}
    for match in FRONT_MATTER_KEY_RE.finditer(front_matter):
        key = match.group(1)
        values[key] = _normalize_scalar(match.group(2))
    return values.get("course", ""), values.get("course_slug", "")


def _course_dirs_for_slug(course_slug: str) -> list[Path]:
    slug = str(course_slug or "").strip()
    if slug:
        return [COURSES_ROOT / slug]
    if not COURSES_ROOT.exists():
        return []
    return sorted(path for path in COURSES_ROOT.iterdir() if path.is_dir())


def main() -> int:
    args = _parse_args()
    failures: list[str] = []
    checked_lessons = 0

    if not COURSES_ROOT.exists():
        print(f"[lesson-course-slug-guard] FAIL: courses root not found: {COURSES_ROOT}", file=sys.stderr)
        return 1

    course_dirs = _course_dirs_for_slug(args.course_slug)
    for course_dir in course_dirs:
        if not course_dir.exists():
            failures.append(f"{course_dir}: course directory not found")
            continue
        lessons_dir = course_dir / "lessons"
        if not lessons_dir.exists():
            failures.append(f"{course_dir}: missing lessons directory")
            continue

        lesson_files = sorted(path for path in lessons_dir.glob("*.md") if path.is_file())
        if not lesson_files:
            failures.append(f"{lessons_dir}: no lesson markdown files found")
            continue

        expected_slug = course_dir.name
        for lesson_path in lesson_files:
            checked_lessons += 1
            front_matter, read_error = _read_front_matter(lesson_path)
            if read_error:
                failures.append(read_error)
                continue

            course_value, course_slug_value = _extract_course_values(front_matter)
            if course_value and course_slug_value and course_value != course_slug_value:
                failures.append(
                    f"{lesson_path}: front matter 'course' ('{course_value}') does not match "
                    f"'course_slug' ('{course_slug_value}')"
                )

            effective_slug = course_slug_value or course_value
            if not effective_slug:
                failures.append(f"{lesson_path}: front matter missing 'course' (or 'course_slug')")
                continue
            if not COURSE_SLUG_RE.fullmatch(effective_slug):
                failures.append(
                    f"{lesson_path}: front matter course slug '{effective_slug}' is invalid "
                    "(expected letters/numbers/_/- only)"
                )
                continue
            if effective_slug != expected_slug:
                failures.append(
                    f"{lesson_path}: front matter course slug '{effective_slug}' does not match "
                    f"folder slug '{expected_slug}'"
                )

    if failures:
        print("[lesson-course-slug-guard] FAIL: lesson course slug drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[lesson-course-slug-guard] keep lesson front matter course slug aligned to course folder slug",
            file=sys.stderr,
        )
        return 1

    print(
        "[lesson-course-slug-guard] OK "
        f"({checked_lessons} lessons checked across {len(course_dirs)} course(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
