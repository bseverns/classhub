#!/usr/bin/env python3
"""
Scaffold a new course folder with course.yaml, lesson markdown, and a reference file.

Usage:
  python3 scripts/new_course_scaffold.py \
    --slug robotics_intro \
    --title "Robotics: Sensors + Motion" \
    --sessions 8 \
    --duration 75 \
    --age-band "5th-7th"
"""
from __future__ import annotations

import argparse
from pathlib import Path


COURSES_ROOT = Path("services/classhub/content/courses")
REFERENCE_ROOT = Path("services/homework_helper/tutor/reference")


def _lesson_slug(i: int) -> str:
    return f"s{i:02d}-lesson-{i:02d}"


def _lesson_filename(i: int) -> str:
    return f"lessons/{i:02d}-lesson-{i:02d}.md"


def _lesson_title(i: int) -> str:
    return f"Session {i}"


def _lesson_front_matter(course_slug: str, i: int, duration: int) -> str:
    slug = _lesson_slug(i)
    title = _lesson_title(i)
    return f"""---
course: {course_slug}
session: {i}
slug: {slug}
title: {title}
duration_minutes: {duration}
makes: <short outcome>
needs:
  - <tools or materials>
privacy:
  - <privacy guardrails>
videos: []
submission:
  type: file
  accepted:
    - .<ext>
  naming: <example>
done_looks_like:
  - <objective check>
help:
  quick_fixes:
    - <common fix>
extend:
  - <optional stretch>
teacher_panel:
  purpose: <goal>
  snags:
    - <common pitfalls>
  assessment:
    - <what to look for>
---
"""


def _lesson_body() -> str:
    return """## Watch

## Do

## Submit

## Help

## Extend (optional)
"""


def _course_manifest(slug: str, title: str, sessions: int, duration: int, age_band: str) -> str:
    lessons = []
    for i in range(1, sessions + 1):
        lessons.append(
            f"""  - session: {i}
    slug: {_lesson_slug(i)}
    title: "{_lesson_title(i)}"
    file: {_lesson_filename(i)}"""
        )
    lessons_block = "\n".join(lessons)
    return f"""slug: {slug}
title: "{title}"
sessions: {sessions}
default_duration_minutes: {duration}
age_band: "{age_band}"
needs:
  - <tools or materials>
privacy:
  - <privacy guardrails>
helper_reference: {slug}
lessons:
{lessons_block}
"""


def _reference_file(slug: str, title: str, age_band: str) -> str:
    return f"""# Reference: {slug}

## Audience + environment
- Age range: {age_band}
- Devices: <describe the hardware>
- Core work happens in: <primary tool/app>

## Goal of the class
- <main objective>

## What students can do
- <capabilities>

## What students should NOT do
- <constraints>

## Vocabulary to use
- <key terms>

## Common misconceptions to correct
- <misconception> -> <correction>

## Scratch-only reminder (if applicable)
- Provide blocks-based steps only. Do not answer in text languages unless the course uses them.

## Off-topic handling
- If a question is unrelated, redirect to the current lesson tasks.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--sessions", type=int, required=True)
    parser.add_argument("--duration", type=int, default=75)
    parser.add_argument("--age-band", default="5th-7th")
    args = parser.parse_args()

    course_dir = COURSES_ROOT / args.slug
    lessons_dir = course_dir / "lessons"
    course_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir.mkdir(parents=True, exist_ok=True)

    # course.yaml
    (course_dir / "course.yaml").write_text(
        _course_manifest(args.slug, args.title, args.sessions, args.duration, args.age_band),
        encoding="utf-8",
    )

    # lessons
    for i in range(1, args.sessions + 1):
        lesson_path = course_dir / _lesson_filename(i)
        lesson_path.write_text(
            _lesson_front_matter(args.slug, i, args.duration) + _lesson_body(),
            encoding="utf-8",
        )

    # reference
    REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (REFERENCE_ROOT / f"{args.slug}.md").write_text(
        _reference_file(args.slug, args.title, args.age_band),
        encoding="utf-8",
    )

    print(f"Created course scaffold at {course_dir}")
    print(f"Created reference file at {REFERENCE_ROOT / f'{args.slug}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
