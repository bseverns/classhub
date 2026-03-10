"""Course/lesson file rendering and write helpers for syllabus ingestion."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from .syllabus_ingest_contracts import COURSE_SLUG_RE, SyllabusIngestError, _ZipLessonImage
from .syllabus_ingest_text_parse import (
    _collect_sections,
    _extract_bullets,
    _find_section,
    _normalize_meta_key,
    _parse_metadata_line,
    _slugify,
)
from .syllabus_ingest_zip_helpers import (
    _safe_binary_extension,
    _safe_child_path,
    _safe_lesson_filename,
)


def _yaml_quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(key: str, items: list[str], indent: int = 0) -> str:
    if not items:
        return ""
    pad = " " * indent
    out = f"{pad}{key}:\n"
    for item in items:
        out += f"{pad}  - {_yaml_quote(item)}\n"
    return out


def _strip_session_config_lines(body_lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in body_lines:
        parsed = _parse_metadata_line(line)
        if parsed:
            key = _normalize_meta_key(parsed[0])
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
    support_images: list[str] | None = None,
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
    if support_images:
        out += _yaml_list("support_images", support_images)
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


def _build_lesson_payload(
    course_slug: str,
    session: dict,
    duration: int,
    *,
    support_images: list[str] | None = None,
) -> dict[str, str]:
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
        support_images=support_images or [],
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
    *,
    root_dir: Path,
    slug: str,
    title: str,
    sessions: list[dict],
    duration: int,
    grade_band: str,
    age_band: str,
    needs: list[str],
    ui_level: str,
    program_profile: str,
    overwrite: bool,
    lesson_images: list[_ZipLessonImage] | None = None,
) -> Path:
    safe_slug = str(slug or "").strip().lower()
    if not COURSE_SLUG_RE.fullmatch(safe_slug):
        raise SyllabusIngestError("Course slug can use lowercase letters, numbers, underscores, and dashes.")
    root_resolved = Path(root_dir).resolve()
    root_resolved.mkdir(parents=True, exist_ok=True)
    destination = _safe_child_path(
        root_resolved,
        safe_slug,
        error_message="Resolved course path escapes configured courses root.",
    )

    if destination.exists():
        if not overwrite:
            raise SyllabusIngestError(f"Course '{slug}' already exists. Enable overwrite to replace it.")
        shutil.rmtree(destination)

    tmp_dir = _safe_child_path(
        root_resolved,
        f".tmp-{uuid.uuid4().hex}",
        error_message="Temporary write path is unsafe.",
    )
    lessons_dir = _safe_child_path(
        tmp_dir,
        "lessons",
        error_message="Temporary lessons path is unsafe.",
    )
    tmp_dir.mkdir(parents=True, exist_ok=False)
    lessons_dir.mkdir(parents=True, exist_ok=False)
    support_image_paths_by_session: dict[int, list[str]] = {}
    if lesson_images:
        valid_sessions = {int(row.get("session") or 0) for row in sessions if int(row.get("session") or 0) > 0}
        lesson_support_dir = _safe_child_path(
            tmp_dir,
            "lesson_support_images",
            error_message="Temporary support image path is unsafe.",
        )
        lesson_support_dir.mkdir(parents=True, exist_ok=False)
        for image in lesson_images:
            if int(image.session) not in valid_sessions:
                continue
            output_filename = str(image.output_filename or "").strip()
            if not output_filename:
                continue
            _safe_binary_extension(output_filename)
            output_path = _safe_child_path(
                lesson_support_dir,
                output_filename,
                error_message="Generated support image path is unsafe.",
            )
            output_path.write_bytes(image.raw)
            rel_path = f"lesson_support_images/{output_filename}"
            support_image_paths_by_session.setdefault(int(image.session), []).append(rel_path)

    try:
        for session in sessions:
            session_num = int(session.get("session") or 0)
            payload = _build_lesson_payload(
                slug,
                session,
                duration,
                support_images=support_image_paths_by_session.get(session_num, []),
            )
            lesson_filename = _safe_lesson_filename(payload.get("filename", ""))
            lesson_path = _safe_child_path(
                lessons_dir,
                lesson_filename,
                error_message="Generated lesson path is unsafe.",
            )
            lesson_path.write_text(
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
        (tmp_dir / "course.yaml").write_text(course_yaml, encoding="utf-8")
        tmp_dir.replace(destination)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    return destination


__all__ = [
    "_write_course",
]
