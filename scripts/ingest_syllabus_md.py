#!/usr/bin/env python3
"""
Parse a syllabus Markdown or DOCX file and scaffold a course.

Inputs:
  --sessions-md  Teacher-facing session plan (.md or .docx) (required)
  --overview-md  Public-facing syllabus (.md or .docx) (optional)

Output:
  services/classhub/content/courses/<slug>/course.yaml
  services/classhub/content/courses/<slug>/lessons/*.md
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


COURSES_ROOT = Path("services/classhub/content/courses")

SESSION_TEMPLATE_RE = re.compile(
    r"^\s{0,3}(?:#\s*)?session\s*(\d{1,2})\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
SESSION_VERBOSE_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?session\s*(\d{1,2})\s*[:\-–—]\s*(.+?)\s*$",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)")
BULLET_RE = re.compile(r"^\s*[-*•]\s+(.*)")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+(.*)")
META_RE = re.compile(r"^\*{0,2}(.+?)\*{0,2}\s*:\s*(.+)$")
GRADE_RANGE_RE = re.compile(r"\b(k|\d{1,2})\s*(?:-|to|through|–|—)\s*(\d{1,2})\b", re.IGNORECASE)
AGE_RANGE_RE = re.compile(r"\bages?\s*(\d{1,2})\s*(?:-|to|through|–|—)\s*(\d{1,2})\b", re.IGNORECASE)
SESSION_COUNT_RE = re.compile(r"(\d{1,2})\s*(?:sessions?|meetings?|weeks?)\b", re.IGNORECASE)

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
}


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "session"


def _yaml_quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f"\"{escaped}\""


def _yaml_list(key: str, items: list[str], indent: int = 0) -> str:
    if not items:
        return ""
    pad = " " * indent
    out = f"{pad}{key}:\n"
    for item in items:
        out += f"{pad}  - {_yaml_quote(item)}\n"
    return out


def _extract_bullets(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        m = BULLET_RE.match(line) or NUMBERED_RE.match(line)
        if m:
            items.append(m.group(1).strip())
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
            items.append(stripped)
    return items


def _normalize_meta_key(raw: str) -> str:
    token = re.sub(r"\s+", " ", str(raw or "").strip().lower())
    token = token.replace("_", " ").replace("/", " ")
    token = re.sub(r"\s+", " ", token).strip()
    if not token:
        return ""
    if token in META_KEY_ALIASES:
        return META_KEY_ALIASES[token]
    return token.replace("-", " ").replace(" ", "_")


def _read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml_data = zf.read("word/document.xml")
    root = ET.fromstring(xml_data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        texts = [node.text for node in para.findall(".//w:t", ns) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return _read_docx_text(path)
    return path.read_text(encoding="utf-8")


def _session_header_match(line: str, session_parse_mode: str):
    mode = (session_parse_mode or "auto").strip().lower()
    if mode == "template":
        return SESSION_TEMPLATE_RE.match(line)
    if mode == "verbose":
        return SESSION_VERBOSE_RE.match(line)
    return SESSION_VERBOSE_RE.match(line) or SESSION_TEMPLATE_RE.match(line)


def _parse_inline_metadata(
    raw: str,
    *,
    stop_on_session_header: bool = False,
    session_parse_mode: str = "auto",
    line_limit: int = 220,
) -> dict[str, str]:
    info: dict[str, str] = {}
    lines = raw.splitlines()
    for idx, line in enumerate(lines):
        if line_limit and idx >= line_limit:
            break
        if stop_on_session_header and _session_header_match(line, session_parse_mode):
            break
        m = META_RE.match(line.strip())
        if not m:
            continue
        key = _normalize_meta_key(m.group(1))
        value = m.group(2).strip()
        if key and value:
            info[key] = value
    return info


def _first_h1_title(raw: str) -> str:
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _collect_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            title = heading.group(2).strip().lower()
            current = title
            sections.setdefault(current, [])
            continue
        stripped = line.strip().rstrip(":").lower()
        if any(stripped.startswith(name) for name in SECTION_NAMES):
            current = next((name for name in SECTION_NAMES if stripped.startswith(name)), stripped)
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _find_section(sections: dict[str, list[str]], keyword: str) -> list[str]:
    for key, lines in sections.items():
        if keyword in key:
            return lines
    return []


def _parse_sessions(raw: str, *, session_parse_mode: str = "auto") -> list[dict]:
    lines = raw.splitlines()
    indices = []
    for idx, line in enumerate(lines):
        if _session_header_match(line, session_parse_mode):
            indices.append(idx)
    sessions = []
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(lines)
        header = lines[start]
        m = _session_header_match(header, session_parse_mode)
        if not m:
            continue
        session_num = int(m.group(1))
        title = m.group(2).strip()
        body_lines = lines[start + 1 : end]
        ui_level_override = _extract_session_ui_level(body_lines)
        sessions.append({
            "session": session_num,
            "title": title,
            "body_lines": body_lines,
            "ui_level_override": ui_level_override,
        })
    return sessions


def _has_session_headers(raw: str, *, session_parse_mode: str = "auto") -> bool:
    return any(_session_header_match(line, session_parse_mode) for line in raw.splitlines())


def _parse_overview(raw: str) -> dict:
    info = _parse_inline_metadata(raw)
    title = _first_h1_title(raw)
    if title and "title" not in info:
        info["title"] = title
    return info


def _extract_minutes(text: str) -> int | None:
    source = (text or "").lower()
    if not source:
        return None
    minutes = None
    m = re.search(r"(\d+)\s*(hour|hours|hr|hrs)", source)
    if m:
        minutes = int(m.group(1)) * 60
    m = re.search(r"(\d+)\s*(minute|minutes|min|mins)", source)
    if m:
        minutes = int(m.group(1))
    return minutes


def _extract_session_count(text: str) -> int | None:
    source = (text or "").lower()
    if not source:
        return None
    sessions = None
    m = re.search(r"for\s+(\d+)\s+weeks", source)
    if m:
        sessions = int(m.group(1))
    if sessions:
        return sessions
    m = SESSION_COUNT_RE.search(source)
    if m:
        return int(m.group(1))
    return None


def _normalize_ui_level(raw: str) -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return ""
    token = token.replace("/", "_").replace("-", "_").replace(" ", "_")
    token = re.sub(r"_+", "_", token).strip("_")
    if token in UI_LEVEL_VALUES:
        return token
    return UI_LEVEL_ALIASES.get(token, "")


def _grade_token_to_int(raw: str) -> int | None:
    token = str(raw or "").strip().lower()
    if token == "k":
        return 0
    if token.isdigit():
        return int(token)
    return None


def _infer_ui_level_from_grade_band(raw: str) -> str:
    text = str(raw or "").strip().lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"(st|nd|rd|th)", "", text)
    match = GRADE_RANGE_RE.search(text)
    if not match:
        return ""
    start = _grade_token_to_int(match.group(1))
    end = _grade_token_to_int(match.group(2))
    if start is None or end is None:
        return ""
    high = max(start, end)
    if high <= 5:
        return "elementary"
    if high <= 12:
        return "secondary"
    return "advanced"


def _infer_ui_level_from_age_band(raw: str) -> str:
    text = str(raw or "").strip().lower().replace("–", "-").replace("—", "-")
    match = AGE_RANGE_RE.search(text)
    if not match:
        return ""
    low = int(match.group(1))
    high = int(match.group(2))
    if high <= 10:
        return "elementary"
    if low >= 11 and high <= 18:
        return "secondary"
    if low >= 18:
        return "advanced"
    return ""


def _pick_first(meta: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return ""


def _resolve_ui_level(meta: dict[str, str], *, default_ui_level: str) -> str:
    explicit = _pick_first(meta, "ui_level", "program_profile", "learner_level")
    normalized = _normalize_ui_level(explicit)
    if normalized:
        return normalized
    grade_band = _pick_first(meta, "grade_band", "grade_level")
    inferred_grade = _infer_ui_level_from_grade_band(grade_band)
    if inferred_grade:
        return inferred_grade
    age_band = _pick_first(meta, "age_band", "ages")
    inferred_age = _infer_ui_level_from_age_band(age_band)
    if inferred_age:
        return inferred_age
    fallback = _normalize_ui_level(default_ui_level)
    return fallback or "secondary"


def _extract_session_ui_level(body_lines: list[str]) -> str:
    for line in body_lines[:30]:
        m = META_RE.match(line.strip())
        if not m:
            continue
        key = _normalize_meta_key(m.group(1))
        if key not in {"ui_level", "program_profile", "learner_level", "grade_band", "age_band"}:
            continue
        normalized = _normalize_ui_level(m.group(2))
        if normalized:
            return normalized
        inferred = _infer_ui_level_from_grade_band(m.group(2)) or _infer_ui_level_from_age_band(m.group(2))
        if inferred:
            return inferred
    return ""


def _strip_session_config_lines(body_lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in body_lines:
        m = META_RE.match(line.strip())
        if m:
            key = _normalize_meta_key(m.group(1))
            if key in {"ui_level", "program_profile", "learner_level", "grade_band", "age_band"}:
                continue
        out.append(line)
    return out


def _build_lesson_front_matter(
    course_slug: str,
    session_num: int,
    title: str,
    duration: int,
    mission: str,
    needs: list[str],
    checkpoints: list[str],
    quick_fixes: list[str],
    extensions: list[str],
    teacher_prep: list[str],
    ui_level_override: str = "",
) -> str:
    out = "---\n"
    out += f"course: {course_slug}\n"
    out += f"session: {session_num}\n"
    out += f"slug: s{session_num:02d}-{_slugify(title)}\n"
    out += f"title: {_yaml_quote(title)}\n"
    out += f"duration_minutes: {duration}\n"
    if ui_level_override:
        out += f"ui_level: {ui_level_override}\n"
    if mission:
        out += f"makes: {_yaml_quote(mission)}\n"
    out += _yaml_list("needs", needs)
    out += _yaml_list("done_looks_like", checkpoints)
    if quick_fixes:
        out += "help:\n"
        out += _yaml_list("quick_fixes", quick_fixes, indent=2)
    out += _yaml_list("extend", extensions)
    if teacher_prep:
        out += "teacher_panel:\n"
        out += _yaml_list("prep", teacher_prep, indent=2)
    out += "---\n"
    return out


def _render_course_yaml(
    slug: str,
    title: str,
    sessions: list[dict],
    duration: int,
    grade_band: str,
    age_band: str,
    needs: list[str],
    ui_level: str,
    program_profile: str,
) -> str:
    lesson_entries = []
    for session in sessions:
        session_num = session["session"]
        lesson_title = session["title"]
        lesson_slug = f"s{session_num:02d}-{_slugify(lesson_title)}"
        filename = f"{session_num:02d}-{_slugify(lesson_title)}.md"
        lesson_entries.append(
            f"""  - session: {session_num}
    slug: {lesson_slug}
    title: {_yaml_quote(lesson_title)}
    file: lessons/{filename}"""
        )

    lines = [
        f"slug: {slug}",
        f"title: {_yaml_quote(title)}",
        f"ui_level: {ui_level}",
        f"program_profile: {program_profile}",
        f"sessions: {len(sessions)}",
        f"default_duration_minutes: {duration}",
    ]
    if grade_band:
        lines.append(f"grade_band: {_yaml_quote(grade_band)}")
    if age_band:
        lines.append(f"age_band: {_yaml_quote(age_band)}")
    needs_block = _yaml_list("needs", needs).rstrip()
    if needs_block:
        lines.append(needs_block)
    lines.append(f"helper_reference: {slug}")
    lines.append("lessons:")
    lines.append(chr(10).join(lesson_entries))
    return "\n".join(lines) + "\n"


def _build_lesson_payload(course_slug: str, session: dict, duration: int) -> dict[str, str]:
    session_num = int(session["session"])
    lesson_title = str(session["title"]).strip()
    filename = f"{session_num:02d}-{_slugify(lesson_title)}.md"
    body_lines = list(session.get("body_lines") or [])

    mission = ""
    for line in body_lines:
        m = re.search(r"(?:\*{0,2})Mission(?:\*{0,2})\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            mission = m.group(1).strip()
            break

    sections = _collect_sections(body_lines)
    needs_items = _extract_bullets(_find_section(sections, "materials"))
    checkpoints = _extract_bullets(_find_section(sections, "checkpoints"))
    quick_fixes = _extract_bullets(_find_section(sections, "common stuck points"))
    if not quick_fixes:
        quick_fixes = _extract_bullets(_find_section(sections, "stuck points"))
    extensions = _extract_bullets(_find_section(sections, "extensions"))
    teacher_prep = _extract_bullets(_find_section(sections, "teacher prep"))

    ui_level_override = str(session.get("ui_level_override") or "").strip()
    front_matter = _build_lesson_front_matter(
        course_slug,
        session_num,
        lesson_title,
        duration,
        mission,
        needs_items,
        checkpoints,
        quick_fixes,
        extensions,
        teacher_prep,
        ui_level_override=ui_level_override,
    )
    cleaned_body = "\n".join(_strip_session_config_lines(body_lines)).strip()
    if not cleaned_body:
        cleaned_body = f"# {lesson_title}\n\n(Write lesson body.)"
    return {
        "filename": filename,
        "front_matter": front_matter,
        "body": cleaned_body + "\n",
    }


def _write_course(
    slug: str,
    title: str,
    sessions: list[dict],
    duration: int,
    grade_band: str,
    age_band: str,
    needs: list[str],
    ui_level: str,
    program_profile: str,
) -> Path:
    course_dir = COURSES_ROOT / slug
    lessons_dir = course_dir / "lessons"
    course_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir.mkdir(parents=True, exist_ok=True)

    for session in sessions:
        payload = _build_lesson_payload(slug, session, duration)
        (lessons_dir / payload["filename"]).write_text(
            payload["front_matter"] + payload["body"],
            encoding="utf-8",
        )

    course_yaml = _render_course_yaml(
        slug,
        title,
        sessions,
        duration,
        grade_band,
        age_band,
        needs,
        ui_level,
        program_profile,
    )
    (course_dir / "course.yaml").write_text(course_yaml, encoding="utf-8")
    return course_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions-md", required=True)
    parser.add_argument("--overview-md")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title")
    parser.add_argument("--sessions", type=int)
    parser.add_argument("--duration", type=int)
    parser.add_argument("--grade-band", default="")
    parser.add_argument("--age-band", default="")
    parser.add_argument("--default-ui-level", default="secondary")
    parser.add_argument(
        "--session-parse-mode",
        choices=["auto", "template", "verbose"],
        default="auto",
        help="Header parser mode for session boundaries.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sessions_path = Path(args.sessions_md)
    sessions_raw = _read_text(sessions_path)
    if not _has_session_headers(sessions_raw, session_parse_mode=args.session_parse_mode):
        print("[warn] No session headers found. Expected lines like: 'Session 01: Title' or '## Session 1: Title'.")
    sessions = _parse_sessions(sessions_raw, session_parse_mode=args.session_parse_mode)
    if not sessions:
        raise SystemExit("No sessions found. Expected headings like: Session 01: Title")

    overview_info: dict[str, str] = {}
    if args.overview_md:
        overview_raw = _read_text(Path(args.overview_md))
        overview_info = _parse_overview(overview_raw)

    sessions_preamble_info = _parse_inline_metadata(
        sessions_raw,
        stop_on_session_header=True,
        session_parse_mode=args.session_parse_mode,
    )
    merged_info = {**overview_info, **sessions_preamble_info}
    default_ui_level = _normalize_ui_level(args.default_ui_level) or "secondary"
    ui_level = _resolve_ui_level(merged_info, default_ui_level=default_ui_level)
    explicit_program_profile = _normalize_ui_level(_pick_first(merged_info, "program_profile"))
    program_profile = explicit_program_profile or ui_level

    title = args.title or _pick_first(merged_info, "title") or _first_h1_title(sessions_raw)
    if not title:
        raise SystemExit("Missing course title. Provide --title or include a top-level # Title in overview.md")

    duration_candidates = [
        _pick_first(merged_info, "meeting_time"),
        _pick_first(merged_info, "session_length"),
        _pick_first(merged_info, "duration"),
    ]
    derived_duration = next((m for m in (_extract_minutes(text) for text in duration_candidates) if m), None)

    session_candidates = [
        _pick_first(merged_info, "total_sessions"),
        _pick_first(merged_info, "meeting_time"),
    ]
    derived_sessions = next((s for s in (_extract_session_count(text) for text in session_candidates) if s), None)

    duration = args.duration or derived_duration or 75
    grade_band = args.grade_band or _pick_first(merged_info, "grade_band", "grade_level")
    age_band = args.age_band or _pick_first(merged_info, "age_band") or "5th-7th"
    needs = []
    platform = _pick_first(merged_info, "platform")
    if platform:
        needs.append(platform)

    expected_sessions = args.sessions or derived_sessions
    if expected_sessions and expected_sessions != len(sessions):
        print(f"[warn] Parsed {len(sessions)} sessions, but metadata indicates {expected_sessions}.")

    course_dir = COURSES_ROOT / args.slug
    if course_dir.exists() and any(course_dir.iterdir()) and not args.force:
        raise SystemExit(f"Course folder already exists: {course_dir} (use --force to overwrite)")

    if args.dry_run:
        print("[dry-run] course.yaml:")
        print(
            _render_course_yaml(
                args.slug,
                title,
                sessions,
                duration,
                grade_band,
                age_band,
                needs,
                ui_level,
                program_profile,
            )
        )
        for session in sessions:
            payload = _build_lesson_payload(args.slug, session, duration)
            print(f"[dry-run] lessons/{payload['filename']}:")
            print(payload["front_matter"] + payload["body"].rstrip("\n"))
        return 0

    _write_course(
        args.slug,
        title,
        sessions,
        duration,
        grade_band,
        age_band,
        needs,
        ui_level,
        program_profile,
    )
    print(f"Created course at {course_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
