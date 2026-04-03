#!/usr/bin/env python3
"""
Generate per-lesson helper reference files from course markdown.

Usage:
  python scripts/generate_lesson_references.py \
    --course services/classhub/content/courses/piper_scratch_12_session/course.yaml \
    --out services/homework_helper/tutor/reference

This writes one file per lesson: <out>/<lesson_slug>.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - CLI dependency guard
    print(
        "[generate-lesson-references] FAIL: PyYAML is required. "
        "Run this from the project Python environment or install repo deps first.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
LIST_RE = re.compile(r"^(\s*[-*]|\s*\d+[.)])\s+")
SAFE_KEY_RE = re.compile(r"^[a-z0-9_-]+$")

WANTED_SECTIONS = {
    "goal",
    "watch",
    "do",
    "submit",
    "help",
    "extend",
    "teacher panel",
}


def normalize_reference_items(raw_items) -> list[str]:
    items: list[str] = []
    for raw in list(raw_items or []):
        if isinstance(raw, dict):
            for key, value in raw.items():
                left = str(key or "").strip()
                right = str(value or "").strip()
                if left and right:
                    items.append(f"{left}: {right}")
                elif left:
                    items.append(left)
                elif right:
                    items.append(right)
            continue
        text = str(raw or "").strip()
        if text:
            items.append(text)
    return items


def parse_front_matter(raw: str) -> tuple[dict, str]:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")
            return fm, body
    return {}, raw


def collect_sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in body.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            title = heading.group(2).strip()
            key = title.lower()
            current = key
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        if LIST_RE.match(line):
            sections[current].append(LIST_RE.sub("", line).strip())
        elif line.strip().startswith("**") and ":" in line:
            sections[current].append(line.strip().strip("*"))
        elif line.strip().startswith("Stop point:"):
            sections[current].append(line.strip())
    return sections


def select_section(sections: dict[str, list[str]], name: str, max_items: int = 6) -> list[str]:
    items: list[str] = []
    for key, values in sections.items():
        if key == name or key.startswith(name):
            items.extend(values)
    # De-dupe while preserving order.
    seen = set()
    uniq = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq[:max_items]


def render_reference(
    lesson_slug: str,
    title: str,
    session: int | None,
    fm: dict,
    sections: dict[str, list[str]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Reference: {lesson_slug}")
    lines.append("")
    lines.append("## Lesson summary")
    lines.append(f"- Title: {title}")
    if session is not None:
        lines.append(f"- Session: {session}")
    makes = fm.get("makes")
    needs = fm.get("needs")
    if makes:
        lines.append(f"- Makes: {makes}")

    if needs:
        lines.append("")
        lines.append("## STEM technologies in scope")
        for item in needs:
            text = str(item or "").strip()
            if text:
                lines.append(f"- {text}")

    quick_fixes: list[str] = []
    help_meta = fm.get("help") or {}
    if isinstance(help_meta, dict):
        quick_fixes = normalize_reference_items(help_meta.get("quick_fixes"))

    def add_section(label: str, key: str):
        items = select_section(sections, key)
        if not items:
            return
        lines.append("")
        lines.append(f"## {label}")
        for item in items:
            lines.append(f"- {item}")

    add_section("Watch", "watch")
    add_section("Lesson tasks", "do")
    add_section("Submission and workflow", "submit")

    tech_troubleshooting = list(quick_fixes)
    tech_troubleshooting.extend(select_section(sections, "common stuck issues"))
    if tech_troubleshooting:
        seen = set()
        lines.append("")
        lines.append("## Technology-first troubleshooting")
        for item in tech_troubleshooting:
            if not item or item in seen:
                continue
            seen.add(item)
            lines.append(f"- {item}")

    add_section("Support and guidance", "help")
    add_section("Extend", "extend")
    add_section("Teacher notes", "teacher panel")
    lines.append("")
    lines.append("## Scratch-only reminder")
    lines.append("- Provide Scratch block steps only. Do not answer in text languages like Pascal/Python/Java.")
    lines.append("")
    return "\n".join(lines)


def generate_reference_text(*, lesson_meta: dict, course_dir: Path) -> tuple[str, str]:
    slug = lesson_meta.get("slug")
    if not slug or not SAFE_KEY_RE.match(slug):
        raise ValueError(f"Invalid lesson slug: {slug}")

    rel = lesson_meta.get("file")
    if not rel:
        raise ValueError(f"Lesson '{slug}' is missing 'file'")

    lesson_path = course_dir / rel
    raw = lesson_path.read_text(encoding="utf-8")
    fm, body = parse_front_matter(raw)
    sections = collect_sections(body)
    title = lesson_meta.get("title") or fm.get("title") or slug
    session = lesson_meta.get("session")
    return slug, render_reference(slug, title, session, fm, sections)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", required=True, help="Path to course.yaml")
    parser.add_argument("--out", required=True, help="Output directory for references")
    args = parser.parse_args()

    course_path = Path(args.course)
    out_dir = Path(args.out)
    manifest = yaml.safe_load(course_path.read_text(encoding="utf-8")) or {}
    course_dir = course_path.parent
    lessons = manifest.get("lessons") or []

    out_dir.mkdir(parents=True, exist_ok=True)

    for lesson in lessons:
        rel = lesson.get("file")
        if not rel:
            continue
        slug, ref_text = generate_reference_text(lesson_meta=lesson, course_dir=course_dir)
        (out_dir / f"{slug}.md").write_text(ref_text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
