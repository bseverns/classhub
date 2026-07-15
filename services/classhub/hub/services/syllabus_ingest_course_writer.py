"""Course/lesson file rendering and write helpers for syllabus ingestion."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from .syllabus_ingest_contracts import (
    COURSE_SLUG_RE,
    HANDOUT_READING_LEVELS,
    SyllabusIngestError,
    _ZipLessonImage,
)
from .syllabus_ingest_text_parse import (
    _collect_sections,
    _extract_bullets,
    _find_section,
    _normalize_meta_key,
    _parse_markdown_heading,
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


def _yaml_mapping_list(key: str, rows: list[dict[str, str]], indent: int = 0) -> str:
    if not rows:
        return ""
    pad = " " * indent
    out = f"{pad}{key}:\n"
    for row in rows:
        term = str(row.get("term") or "").strip()
        definition = str(row.get("definition") or "").strip()
        if not term or not definition:
            continue
        out += f"{pad}  - term: {_yaml_quote(term)}\n"
        out += f"{pad}    definition: {_yaml_quote(definition)}\n"
    return out


def _yaml_submission(submission: dict) -> str:
    if not submission:
        return ""
    out = "submission:\n"
    for key in ("type", "naming"):
        value = str(submission.get(key) or "").strip()
        if value:
            out += f"  {key}: {_yaml_quote(value)}\n"
    out += _yaml_list("accepted", list(submission.get("accepted") or []), indent=2)
    return out


def _yaml_materials(rows: list[dict]) -> str:
    if not rows:
        return ""
    out = "materials:\n"
    for row in rows:
        out += f"  - type: {_yaml_quote(str(row['type']))}\n"
        out += f"    title: {_yaml_quote(str(row['title']))}\n"
        for key in ("prompt",):
            if row.get(key):
                out += f"    {key}: {_yaml_quote(str(row[key]))}\n"
        for key in ("items", "criteria", "accepted"):
            if row.get(key):
                out += _yaml_list(key, list(row[key]), indent=4)
        for key in ("scale_max", "max_upload_mb"):
            if row.get(key):
                out += f"    {key}: {int(row[key])}\n"
    return out


def _yaml_offline_handout_fields(offline_handout: dict[str, list[str] | str], *, indent: int) -> str:
    pad = " " * indent
    out = ""
    for key in ("title", "subtitle", "goal"):
        value = str(offline_handout.get(key) or "").strip()
        if value:
            out += f"{pad}{key}: {_yaml_quote(value)}\n"
    for key in ("do_now", "safety", "submit", "comment"):
        items = [str(item).strip() for item in (offline_handout.get(key) or []) if str(item).strip()]
        if items:
            out += _yaml_list(key, items, indent=indent)
    return out


def _yaml_offline_handout(offline_handout: dict[str, list[str] | str]) -> str:
    if not offline_handout:
        return ""
    out = "offline_handout:\n"
    out += _yaml_offline_handout_fields(offline_handout, indent=2)
    reading_levels = offline_handout.get("reading_levels")
    if isinstance(reading_levels, dict):
        reading_level_lines = ""
        for reading_level in HANDOUT_READING_LEVELS:
            selected = reading_levels.get(reading_level)
            if not isinstance(selected, dict):
                continue
            body = _yaml_offline_handout_fields(selected, indent=6)
            if not body:
                continue
            reading_level_lines += f"    {reading_level}:\n{body}"
        if reading_level_lines:
            out += "  reading_levels:\n"
            out += reading_level_lines
    localized = offline_handout.get("localized")
    if isinstance(localized, dict):
        localized_lines = ""
        for language_code in ("es", "so", "ksw"):
            selected = localized.get(language_code)
            if not isinstance(selected, dict):
                continue
            body = _yaml_offline_handout_fields(selected, indent=6)
            if body:
                localized_lines += f"    {language_code}:\n{body}"
        if localized_lines:
            out += "  localized:\n"
            out += localized_lines
    return out


def _parse_glossary_entries(lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _extract_bullets(lines):
        term, _, definition = item.partition(":")
        term = term.strip()
        definition = definition.strip()
        if not term or not definition:
            continue
        rows.append({"term": term, "definition": definition})
    return rows


def _parse_offline_handout(lines: list[str]) -> dict[str, list[str] | str]:
    parsed: dict[str, list[str] | str] = {}
    scalar_fields = {"title", "subtitle", "goal"}
    list_fields = {"do_now", "safety", "submit", "comment"}
    for item in _extract_bullets(lines):
        key_raw, _, value = item.partition(":")
        key = _normalize_meta_key(key_raw)
        text = value.strip()
        if not key or not text:
            continue
        reading_level = ""
        for candidate in HANDOUT_READING_LEVELS:
            prefix = f"{candidate}_"
            if key.startswith(prefix):
                reading_level = candidate
                key = key[len(prefix) :]
                break
        localized_language = ""
        for label, code in (("spanish", "es"), ("somali", "so"), ("sgaw_karen", "ksw"), ("karen", "ksw")):
            prefix = f"{label}_"
            if key.startswith(prefix):
                localized_language = code
                key = key[len(prefix) :]
                break
        if key not in scalar_fields and key not in list_fields:
            continue
        target = parsed
        if localized_language:
            localized = parsed.setdefault("localized", {})
            if not isinstance(localized, dict):
                continue
            target = localized.setdefault(localized_language, {})
            if not isinstance(target, dict):
                continue
        if reading_level:
            reading_levels = parsed.setdefault("reading_levels", {})
            if not isinstance(reading_levels, dict):
                continue
            target = reading_levels.setdefault(reading_level, {})
            if not isinstance(target, dict):
                continue
        if key in scalar_fields:
            target[key] = text
            continue
        target.setdefault(key, [])
        cast_list = target[key]
        if isinstance(cast_list, list):
            cast_list.append(text)
    return parsed


def _parse_submission(lines: list[str]) -> dict:
    parsed: dict = {}
    for item in _extract_bullets(lines):
        key_raw, _, value = item.partition(":")
        key = _normalize_meta_key(key_raw)
        value = value.strip()
        if key in {"type", "naming"} and value:
            parsed[key] = value.lower() if key == "type" else value
        elif key == "accepted" and value:
            parsed[key] = [part.strip() for part in re.split(r"[,|]", value) if part.strip()]
    return parsed


def _parse_classhub_materials(lines: list[str]) -> list[dict]:
    rows: list[dict] = []
    for item in _extract_bullets(lines):
        parts = [part.strip() for part in item.split("|")]
        if len(parts) < 3:
            continue
        material_type = parts[0].lower()
        title = parts[1]
        body = parts[2]
        if material_type == "checklist":
            rows.append({"type": material_type, "title": title, "items": [v.strip() for v in body.split(";") if v.strip()]})
        elif material_type == "reflection":
            rows.append({"type": material_type, "title": title, "prompt": body})
        elif material_type == "rubric":
            row = {"type": material_type, "title": title, "criteria": [v.strip() for v in body.split(";") if v.strip()]}
            row["scale_max"] = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 4
            rows.append(row)
        elif material_type == "gallery":
            row = {"type": material_type, "title": title, "accepted": [v.strip() for v in re.split(r"[,;]", body) if v.strip()]}
            row["max_upload_mb"] = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 50
            rows.append(row)
    return rows


_METADATA_ONLY_SECTIONS = {
    "local anchors",
    "example variants",
    "community glossary",
    "offline handout",
    "submission",
    "classhub materials",
}


def _strip_front_matter_sections(body_lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    current_chunk: list[str] = []
    current_is_metadata = False

    def flush_chunk() -> None:
        if current_chunk and not current_is_metadata:
            cleaned.extend(current_chunk)
        current_chunk.clear()

    for line in body_lines:
        heading = _parse_markdown_heading(line)
        stripped = line.strip().rstrip(":").lower()
        section_name = ""
        if heading and heading[0] >= 2:
            section_name = heading[1].strip().lower()
        elif stripped in _METADATA_ONLY_SECTIONS:
            section_name = stripped
        if section_name:
            flush_chunk()
            current_is_metadata = section_name in _METADATA_ONLY_SECTIONS
            current_chunk.append(line)
            continue
        current_chunk.append(line)
    flush_chunk()
    return cleaned


def _strip_session_config_lines(body_lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in body_lines:
        parsed = _parse_metadata_line(line)
        if parsed:
            key = _normalize_meta_key(parsed[0])
            if key in {"ui_level", "program_profile", "learner_level", "grade_band", "age_band", "lesson_slug", "lesson_slug_(for_course.yaml)"}:
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
    local_anchors: list[str] | None = None,
    example_variants: list[str] | None = None,
    community_glossary: list[dict[str, str]] | None = None,
    offline_handout: dict[str, list[str] | str] | None = None,
    lesson_slug: str = "",
    submission: dict | None = None,
    materials: list[dict] | None = None,
) -> str:
    out = "---\n"
    out += f"course: {course_slug}\n"
    out += f"session: {session_num}\n"
    out += f"slug: {lesson_slug or f's{session_num:02d}-{_slugify(title)}'}\n"
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
    out += _yaml_list("local_anchors", local_anchors or [])
    out += _yaml_list("example_variants", example_variants or [])
    out += _yaml_mapping_list("community_glossary", community_glossary or [])
    out += _yaml_offline_handout(offline_handout or {})
    out += _yaml_submission(submission or {})
    out += _yaml_materials(materials or [])
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
        lesson_slug = str(session.get("lesson_slug") or "").strip() or f"s{session_num:02d}-{_slugify(lesson_title)}"
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
    needs_items = _extract_bullets(sections.get("materials", []))
    checkpoints = _extract_bullets(_find_section(sections, "checkpoints"))
    quick_fixes = _extract_bullets(_find_section(sections, "common stuck points"))
    if not quick_fixes:
        quick_fixes = _extract_bullets(_find_section(sections, "stuck points"))
    extensions = _extract_bullets(_find_section(sections, "extensions"))
    teacher_prep = _extract_bullets(_find_section(sections, "teacher prep"))
    local_anchors = _extract_bullets(_find_section(sections, "local anchors"))
    example_variants = _extract_bullets(_find_section(sections, "example variants"))
    community_glossary = _parse_glossary_entries(_find_section(sections, "community glossary"))
    offline_handout = _parse_offline_handout(_find_section(sections, "offline handout"))
    submission = _parse_submission(sections.get("submission", []))
    materials = _parse_classhub_materials(sections.get("classhub materials", []))

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
        local_anchors=local_anchors,
        example_variants=example_variants,
        community_glossary=community_glossary,
        offline_handout=offline_handout,
        lesson_slug=str(session.get("lesson_slug") or "").strip(),
        submission=submission,
        materials=materials,
    )
    cleaned_body = "\n".join(_strip_front_matter_sections(_strip_session_config_lines(body_lines))).strip()
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
