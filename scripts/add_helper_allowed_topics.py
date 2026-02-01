#!/usr/bin/env python3
"""
Add helper_allowed_topics to lesson front matter by extracting key bullets.

Usage:
  python3 scripts/add_helper_allowed_topics.py \
    --lessons-dir services/classhub/content/courses/piper_scratch_12_session/lessons \
    --write

Without --write, it prints a preview and makes no changes.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
LIST_RE = re.compile(r"^\s*[-*]\s+(.*)")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.*)")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
SECTION_NAMES = {"watch", "do", "submit", "help", "extend"}


def _split_front_matter(raw: str):
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        return "", raw
    front_matter = match.group(1)
    body = raw[match.end():]
    return front_matter, body


def _has_helper_allowed(front_matter: str) -> bool:
    return "helper_allowed_topics" in front_matter


def _collect_section_bullets(body: str) -> list[str]:
    current = None
    items: list[str] = []
    for line in body.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            title = heading.group(2).strip().lower()
            current = title if title in SECTION_NAMES else None
            continue
        if current is None:
            continue
        m = CHECKBOX_RE.match(line) or LIST_RE.match(line)
        if m:
            items.append(m.group(1).strip())
            continue
        if current == "submit" and line.strip().lower().startswith("upload:"):
            items.append(line.strip())
    return items


def _topic_from_item(item: str) -> str:
    text = item.strip()
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\([^)]*\)", "", text).strip()
    text = text.replace("—", "-").replace("–", "-")
    lower = text.lower()
    if lower.startswith("upload"):
        ext = re.search(r"\.\w+", lower)
        return f"upload {ext.group(0)}" if ext else "upload file"
    if lower.startswith("download"):
        ext = re.search(r"\.\w+", lower)
        return f"download {ext.group(0)}" if ext else "download file"
    if lower.startswith("open scratch"):
        return "open scratch"
    if lower.startswith("make one tiny change"):
        return "make a small change"
    if lower.startswith("re-open"):
        return "re-open project"
    if "save" in lower and ".sb3" in lower:
        return "save .sb3"
    # Keep first clause, limit length.
    text = text.split(" and ")[0]
    words = text.split()
    text = " ".join(words[:6])
    return text.lower().strip()


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _yaml_quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f"\"{escaped}\""


def _insert_helper_allowed(front_matter: str, topics: list[str]) -> str:
    lines = front_matter.splitlines()
    insert_at = len(lines)
    block = ["helper_allowed_topics:"]
    for topic in topics:
        block.append(f"  - {_yaml_quote(topic)}")
    return "\n".join(lines[:insert_at] + block + lines[insert_at:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lessons-dir", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    if not lessons_dir.exists():
        raise SystemExit(f"Lessons dir not found: {lessons_dir}")

    for path in sorted(lessons_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        front_matter, body = _split_front_matter(raw)
        if not front_matter:
            continue
        if _has_helper_allowed(front_matter):
            continue
        bullets = _collect_section_bullets(body)
        topics = _dedupe([_topic_from_item(b) for b in bullets])
        if not topics:
            continue
        new_front = _insert_helper_allowed(front_matter, topics[:8])
        new_raw = raw.replace(front_matter, new_front, 1)
        if args.write:
            path.write_text(new_raw, encoding="utf-8")
        else:
            print(f"[preview] {path.name}: {topics[:8]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
