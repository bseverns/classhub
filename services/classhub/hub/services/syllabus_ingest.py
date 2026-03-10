"""Teacher-facing syllabus ingestion helpers (.md/.docx/.zip)."""

from __future__ import annotations

import re
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

import defusedxml.ElementTree as ET
from django.utils._os import safe_join

from .content_links import courses_dir
from .syllabus_ingest_contracts import (
    COURSE_SLUG_RE,
    IMAGE_EXTENSIONS,
    META_KEY_ALIASES,
    SECTION_NAMES,
    SUPPORTED_EXTENSIONS,
    TEXT_EXTENSIONS,
    UI_LEVEL_ALIASES,
    UI_LEVEL_VALUES,
    ZIP_SESSION_FILE_RE,
    ZIP_SESSION_PATH_RE,
    SyllabusIngestError,
    SyllabusIngestResult,
    _GRADE_RANGE_CONNECTORS,
    _SESSION_CONNECTORS_TEMPLATE,
    _SESSION_CONNECTORS_VERBOSE,
    _SESSION_COUNT_UNITS,
    _ZipLessonImage,
    _ZipTextDoc,
)


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


def _collapse_spaces(value: str) -> str:
    return " ".join(str(value or "").split())


def _extract_bullet_text(line: str) -> str:
    stripped = str(line or "").lstrip()
    if len(stripped) < 2:
        return ""
    if stripped[0] not in {"-", "*", "•"}:
        return ""
    if not stripped[1].isspace():
        return ""
    return stripped[1:].strip()


def _extract_numbered_text(line: str) -> str:
    stripped = str(line or "").lstrip()
    if not stripped:
        return ""
    idx = 0
    while idx < len(stripped) and stripped[idx].isdigit():
        idx += 1
    if idx == 0 or idx >= len(stripped):
        return ""
    if stripped[idx] not in {".", ")"}:
        return ""
    idx += 1
    if idx >= len(stripped) or not stripped[idx].isspace():
        return ""
    return stripped[idx:].strip()


def _strip_emphasis_token(token: str) -> str:
    value = str(token or "").strip()
    if value.startswith("**") and value.endswith("**") and len(value) > 4:
        return value[2:-2].strip()
    if value.startswith("*") and value.endswith("*") and len(value) > 2:
        return value[1:-1].strip()
    return value


def _parse_metadata_line(line: str) -> tuple[str, str] | None:
    stripped = str(line or "").strip()
    if not stripped:
        return None
    colon = stripped.find(":")
    if colon <= 0 or colon >= len(stripped) - 1:
        return None
    key = _strip_emphasis_token(stripped[:colon])
    value = stripped[colon + 1 :].strip()
    if not key or not value:
        return None
    return key, value


def _parse_markdown_heading(line: str) -> tuple[int, str] | None:
    stripped = str(line or "").lstrip()
    if not stripped.startswith("#"):
        return None
    idx = 0
    while idx < len(stripped) and stripped[idx] == "#":
        idx += 1
    if idx < 1 or idx > 6:
        return None
    if idx >= len(stripped) or not stripped[idx].isspace():
        return None
    title = stripped[idx:].strip()
    if not title:
        return None
    return idx, title


def _parse_session_header(line: str, *, mode: str) -> tuple[int, str] | None:
    source = str(line or "")
    idx = 0
    indent = 0
    while idx < len(source) and source[idx] in {" ", "\t"}:
        indent += 1
        idx += 1
    if indent > 3:
        return None
    token = source[idx:]

    hash_count = 0
    while hash_count < len(token) and token[hash_count] == "#":
        hash_count += 1
    if hash_count:
        if mode == "template" and hash_count != 1:
            return None
        if mode == "verbose" and not (1 <= hash_count <= 6):
            return None
        token = token[hash_count:].lstrip()

    token_lower = token.lower()
    if not token_lower.startswith("session"):
        return None
    token = token[len("session") :].lstrip()
    if not token:
        return None

    idx = 0
    while idx < len(token) and token[idx].isdigit() and idx < 2:
        idx += 1
    if idx == 0:
        return None
    if idx < len(token) and token[idx].isdigit():
        return None
    session_num = int(token[:idx])
    token = token[idx:].lstrip()
    if not token:
        return None

    connectors = _SESSION_CONNECTORS_TEMPLATE if mode == "template" else _SESSION_CONNECTORS_VERBOSE
    if token[0] not in connectors:
        return None
    title = token[1:].strip()
    if not title:
        return None
    return session_num, title


def _extract_bullets(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        bullet = _extract_bullet_text(line) or _extract_numbered_text(line)
        if bullet:
            items.append(bullet)
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
            items.append(stripped)
    return items


def _normalize_meta_key(raw: str) -> str:
    token = _collapse_spaces(str(raw or "").strip().lower())
    token = token.replace("_", " ").replace("/", " ")
    token = _collapse_spaces(token).strip()
    if not token:
        return ""
    if token in META_KEY_ALIASES:
        return META_KEY_ALIASES[token]
    return token.replace("-", " ").replace(" ", "_")


def _read_docx_text_bytes(raw: bytes) -> str:
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        xml_data = archive.read("word/document.xml")
    root = ET.fromstring(xml_data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        texts = [node.text for node in para.findall(".//w:t", ns) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def _decode_markdown_bytes(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _read_text_blob(*, suffix: str, raw: bytes) -> str:
    if suffix == ".docx":
        try:
            return _read_docx_text_bytes(raw)
        except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
            raise SyllabusIngestError("Invalid DOCX source.") from exc
    return _decode_markdown_bytes(raw)


def _session_header_match(line: str, session_parse_mode: str):
    mode = (session_parse_mode or "auto").strip().lower()
    if mode == "template":
        return _parse_session_header(line, mode="template")
    if mode == "verbose":
        return _parse_session_header(line, mode="verbose")
    return _parse_session_header(line, mode="verbose") or _parse_session_header(line, mode="template")


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
        parsed = _parse_metadata_line(line)
        if not parsed:
            continue
        key, value = parsed
        key = _normalize_meta_key(key)
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
        heading = _parse_markdown_heading(line)
        if heading and heading[0] >= 2:
            title = heading[1].strip().lower()
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


def _extract_session_ui_level(body_lines: list[str]) -> str:
    for line in body_lines[:30]:
        parsed = _parse_metadata_line(line)
        if not parsed:
            continue
        key_raw, value = parsed
        key = _normalize_meta_key(key_raw)
        if key not in {"ui_level", "program_profile", "learner_level", "grade_band", "age_band"}:
            continue
        normalized = _normalize_ui_level(value)
        if normalized:
            return normalized
        inferred = _infer_ui_level_from_grade_band(value) or _infer_ui_level_from_age_band(value)
        if inferred:
            return inferred
    return ""


def _parse_sessions(raw: str, *, session_parse_mode: str = "auto") -> list[dict]:
    lines = raw.splitlines()
    indices = []
    headers: dict[int, tuple[int, str]] = {}
    for idx, line in enumerate(lines):
        parsed = _session_header_match(line, session_parse_mode)
        if parsed:
            indices.append(idx)
            headers[idx] = parsed
    sessions = []
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(lines)
        parsed = headers.get(start) or _session_header_match(lines[start], session_parse_mode)
        if not parsed:
            continue
        session_num, title = parsed
        body_lines = lines[start + 1 : end]
        ui_level_override = _extract_session_ui_level(body_lines)
        sessions.append(
            {
                "session": session_num,
                "title": title,
                "body_lines": body_lines,
                "ui_level_override": ui_level_override,
            }
        )
    return sessions


def _parse_overview(raw: str) -> dict[str, str]:
    info = _parse_inline_metadata(raw)
    title = _first_h1_title(raw)
    if title and "title" not in info:
        info["title"] = title
    return info


def _scan_number_before_units(text: str, units: tuple[str, ...]) -> int | None:
    source = str(text or "").lower()
    idx = 0
    while idx < len(source):
        if not source[idx].isdigit():
            idx += 1
            continue
        start = idx
        while idx < len(source) and source[idx].isdigit():
            idx += 1
        value = int(source[start:idx])
        probe = idx
        while probe < len(source) and source[probe].isspace():
            probe += 1
        for unit in units:
            if source.startswith(unit, probe):
                end = probe + len(unit)
                if end == len(source) or not source[end].isalpha():
                    return value
    return None


def _word_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for ch in str(text or "").lower():
        if ch.isalnum():
            current.append(ch)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _range_tokens(text: str) -> list[str]:
    normalized = str(text or "").lower().replace("–", "-").replace("—", "-")
    tokens: list[str] = []
    current: list[str] = []
    for ch in normalized:
        if ch.isalnum():
            current.append(ch)
            continue
        if current:
            tokens.append("".join(current))
            current = []
        if ch == "-":
            tokens.append("-")
    if current:
        tokens.append("".join(current))
    return tokens


def _extract_grade_range(raw: str) -> tuple[int, int] | None:
    tokens = _range_tokens(raw)
    if len(tokens) < 3:
        return None
    for idx in range(len(tokens) - 2):
        start = _grade_token_to_int(tokens[idx])
        if start is None:
            continue
        connector = tokens[idx + 1]
        if connector not in _GRADE_RANGE_CONNECTORS:
            continue
        end = _grade_token_to_int(tokens[idx + 2])
        if end is None:
            continue
        return start, end
    return None


def _extract_age_range(raw: str) -> tuple[int, int] | None:
    tokens = _range_tokens(raw)
    age_markers = [idx for idx, token in enumerate(tokens) if token in {"age", "ages"}]
    if not age_markers:
        return None
    for marker in age_markers:
        for idx in range(marker + 1, len(tokens) - 2):
            if not tokens[idx].isdigit():
                continue
            if tokens[idx + 1] not in _GRADE_RANGE_CONNECTORS:
                continue
            if not tokens[idx + 2].isdigit():
                continue
            return int(tokens[idx]), int(tokens[idx + 2])
    return None


def _extract_minutes(text: str) -> int | None:
    source = (text or "").lower()
    if not source:
        return None
    minutes = None
    hours = _scan_number_before_units(source, ("hour", "hours", "hr", "hrs"))
    if hours is not None:
        minutes = hours * 60
    mins = _scan_number_before_units(source, ("minute", "minutes", "min", "mins"))
    if mins is not None:
        minutes = mins
    return minutes


def _extract_session_count(text: str) -> int | None:
    tokens = _word_tokens(text)
    if not tokens:
        return None
    for idx in range(len(tokens) - 2):
        if tokens[idx] == "for" and tokens[idx + 1].isdigit() and tokens[idx + 2] in {"week", "weeks"}:
            return int(tokens[idx + 1])
    for idx in range(len(tokens) - 1):
        if tokens[idx].isdigit() and tokens[idx + 1] in _SESSION_COUNT_UNITS:
            return int(tokens[idx])
    return None


def _normalize_ui_level(raw: str) -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return ""
    token = token.replace("/", "_").replace("-", "_").replace(" ", "_")
    while "__" in token:
        token = token.replace("__", "_")
    token = token.strip("_")
    if token in UI_LEVEL_VALUES:
        return token
    return UI_LEVEL_ALIASES.get(token, "")


def _grade_token_to_int(raw: str) -> int | None:
    token = str(raw or "").strip().lower()
    if token == "k":
        return 0
    if token.isdigit():
        return int(token)
    if len(token) > 2 and token[:-2].isdigit() and token[-2:] in {"st", "nd", "rd", "th"}:
        return int(token[:-2])
    return None


def _infer_ui_level_from_grade_band(raw: str) -> str:
    grade_range = _extract_grade_range(raw)
    if not grade_range:
        return ""
    start, end = grade_range
    high = max(start, end)
    if high <= 5:
        return "elementary"
    if high <= 12:
        return "secondary"
    return "advanced"


def _infer_ui_level_from_age_band(raw: str) -> str:
    age_range = _extract_age_range(raw)
    if not age_range:
        return ""
    low, high = age_range
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


def _candidate_overview_score(path: str) -> int:
    token = path.lower()
    score = 0
    if "course_description" in token:
        score += 120
    if "overview" in token:
        score += 90
    if "syllabus" in token:
        score += 80
    if "catalog" in token:
        score += 70
    if "readme" in token:
        score += 35
    if "description" in token:
        score += 30
    if "session" in token:
        score -= 40
    return score


def _candidate_sessions_score(path: str) -> int:
    token = path.lower()
    score = 0
    if ZIP_SESSION_PATH_RE.search(token):
        score += 120
    if ZIP_SESSION_FILE_RE.search(Path(path).name):
        score += 100
    if "teacher-plan" in token or "teacher_plan" in token:
        score += 80
    if "sessions" in token:
        score += 60
    if "schedule" in token:
        score += 20
    if "readme" in token:
        score -= 40
    return score


def _session_from_filename(path: str, raw_text: str) -> dict | None:
    name = Path(path).name
    match = ZIP_SESSION_FILE_RE.search(name)
    if not match:
        return None
    session_num = int(match.group(1))
    token = Path(name).stem
    token = ZIP_SESSION_FILE_RE.sub("", token).strip("_- ")
    if not token:
        token = f"session-{session_num:02d}"
    title = re.sub(r"[_\s]+", " ", token).strip().title()
    lines = raw_text.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    return {
        "session": session_num,
        "title": title,
        "body_lines": lines,
        "ui_level_override": _extract_session_ui_level(lines),
    }


def _combine_doc_texts(docs: list[_ZipTextDoc]) -> str:
    chunks: list[str] = []
    for doc in docs:
        label = f"# Source: {doc.path}"
        chunks.append(f"{label}\n\n{doc.text.strip()}\n")
    return "\n".join(chunks).strip() + "\n"


def _parse_sessions_from_zip_docs(
    docs: list[_ZipTextDoc],
    *,
    session_parse_mode: str,
) -> tuple[list[dict], list[str], str]:
    ordered_docs = sorted(docs, key=lambda item: item.path.lower())
    session_docs = sorted(ordered_docs, key=lambda item: (-_candidate_sessions_score(item.path), item.path.lower()))
    sessions_by_num: dict[int, dict] = {}
    used_paths: list[str] = []
    metadata_source = ""

    for doc in session_docs:
        score = _candidate_sessions_score(doc.path)
        if score <= 0:
            continue
        parsed = _parse_sessions(doc.text, session_parse_mode=session_parse_mode)
        if not parsed:
            single = _session_from_filename(doc.path, doc.text)
            parsed = [single] if single else []
        if not parsed:
            continue
        if not metadata_source:
            metadata_source = doc.text
        used_paths.append(doc.path)
        for session in parsed:
            number = int(session.get("session") or 0)
            if number <= 0:
                continue
            sessions_by_num[number] = session

    if sessions_by_num:
        sessions = [sessions_by_num[idx] for idx in sorted(sessions_by_num.keys())]
        return sessions, used_paths, metadata_source

    if not ordered_docs:
        return [], [], ""
    primary_doc = max(ordered_docs, key=lambda item: (_candidate_sessions_score(item.path), item.size, item.path))
    parsed_primary = _parse_sessions(primary_doc.text, session_parse_mode=session_parse_mode)
    if parsed_primary:
        return parsed_primary, [primary_doc.path], primary_doc.text

    combined = _combine_doc_texts(ordered_docs)
    parsed_combined = _parse_sessions(combined, session_parse_mode=session_parse_mode)
    if parsed_combined:
        return parsed_combined, [doc.path for doc in ordered_docs], combined
    return [], [], ""


def _derive_duration_from_docs(docs: list[_ZipTextDoc]) -> int | None:
    for doc in sorted(docs, key=lambda item: (-_candidate_overview_score(item.path), -item.size, item.path.lower())):
        maybe = _extract_minutes(doc.text)
        if maybe:
            return maybe
    return None


def _safe_zip_path(path: str) -> bool:
    return bool(_normalize_zip_member_path(path))


def _normalize_zip_member_path(path: str) -> str:
    normalized = str(path or "").replace("\\", "/").strip()
    if not normalized:
        return ""
    if normalized.startswith("/"):
        return ""
    parts = PurePosixPath(normalized).parts
    if not parts:
        return ""
    if parts[0].endswith(":"):
        return ""
    clean_parts: list[str] = []
    for part in parts:
        token = str(part or "").strip()
        if not token or token in {".", ".."}:
            return ""
        if "\x00" in token:
            return ""
        clean_parts.append(token)
    return "/".join(clean_parts)


def _safe_child_path(base_dir: Path, child_name: str, *, error_message: str) -> Path:
    token = str(child_name or "").strip()
    if not token:
        raise SyllabusIngestError(error_message)
    if "/" in token or "\\" in token or "\x00" in token:
        raise SyllabusIngestError(error_message)
    try:
        joined = safe_join(str(base_dir), token)
    except Exception as exc:
        raise SyllabusIngestError(error_message) from exc
    candidate = Path(joined).resolve()
    if not candidate.is_relative_to(base_dir):
        raise SyllabusIngestError(error_message)
    return candidate


def _safe_lesson_filename(filename: str) -> str:
    token = str(filename or "").strip().lower()
    if not token.endswith(".md"):
        raise SyllabusIngestError("Generated lesson filename is unsafe.")
    stem = token[:-3]
    if not stem:
        raise SyllabusIngestError("Generated lesson filename is unsafe.")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    if any(ch not in allowed for ch in stem):
        raise SyllabusIngestError("Generated lesson filename is unsafe.")
    return token


def _safe_binary_extension(filename: str) -> str:
    suffix = Path(str(filename or "").strip()).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        raise SyllabusIngestError("Zip image extension is not supported.")
    return suffix


def _extract_prefixed_session_number(filename: str) -> int | None:
    token = str(filename or "").strip().lower()
    if not token:
        return None
    idx = 0
    while idx < len(token) and token[idx].isdigit() and idx < 2:
        idx += 1
    if idx == 0:
        return None
    if idx < len(token) and token[idx].isdigit():
        return None
    if idx >= len(token) or token[idx] not in {"-", "_", " "}:
        return None
    value = int(token[:idx])
    if value <= 0:
        return None
    return value


def _build_support_image_filename(
    *,
    session_num: int,
    source_name: str,
    seen: set[str],
) -> str:
    suffix = _safe_binary_extension(source_name)
    raw_stem = Path(str(source_name or "").strip()).stem
    stem_source = raw_stem
    parsed_session = _extract_prefixed_session_number(raw_stem)
    if parsed_session == session_num:
        idx = 0
        while idx < len(raw_stem) and raw_stem[idx].isdigit() and idx < 2:
            idx += 1
        if idx < len(raw_stem):
            stem_source = raw_stem[idx + 1 :].strip(" _-")
    stem = _slugify(stem_source or raw_stem)
    base = f"s{session_num:02d}-{stem or 'image'}"
    candidate = f"{base}{suffix}"
    counter = 2
    while candidate in seen:
        candidate = f"{base}-{counter}{suffix}"
        counter += 1
    seen.add(candidate)
    return candidate


def _zip_text_documents(source_bytes: bytes) -> list[_ZipTextDoc]:
    docs: list[_ZipTextDoc] = []
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > 500:
                raise SyllabusIngestError("Zip archive has too many files to ingest safely.")
            total_size = 0
            for info in infos:
                normalized_member_path = _normalize_zip_member_path(info.filename)
                if not normalized_member_path:
                    continue
                total_size += int(info.file_size or 0)
                if total_size > 30 * 1024 * 1024:
                    raise SyllabusIngestError("Zip archive is too large to ingest safely.")
                suffix = PurePosixPath(normalized_member_path).suffix.lower()
                if suffix not in TEXT_EXTENSIONS:
                    continue
                with archive.open(info, "r") as stream:
                    raw = stream.read()
                text = _read_text_blob(suffix=suffix, raw=raw)
                docs.append(
                    _ZipTextDoc(
                        path=normalized_member_path,
                        text=text,
                        size=int(info.file_size or len(raw)),
                        suffix=suffix,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SyllabusIngestError("Invalid ZIP source.") from exc
    return docs


def _zip_lesson_images(*, source_bytes: bytes, valid_session_numbers: set[int]) -> list[_ZipLessonImage]:
    if not valid_session_numbers:
        return []
    images: list[_ZipLessonImage] = []
    seen_output_names: set[str] = set()
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > 500:
                raise SyllabusIngestError("Zip archive has too many files to ingest safely.")
            total_size = 0
            for info in infos:
                normalized_member_path = _normalize_zip_member_path(info.filename)
                if not normalized_member_path:
                    continue
                total_size += int(info.file_size or 0)
                if total_size > 30 * 1024 * 1024:
                    raise SyllabusIngestError("Zip archive is too large to ingest safely.")
                filename = Path(normalized_member_path).name
                session_num = _extract_prefixed_session_number(filename)
                if session_num is None or session_num not in valid_session_numbers:
                    continue
                try:
                    output_filename = _build_support_image_filename(
                        session_num=session_num,
                        source_name=filename,
                        seen=seen_output_names,
                    )
                except SyllabusIngestError:
                    continue
                with archive.open(info, "r") as stream:
                    raw = stream.read()
                images.append(
                    _ZipLessonImage(
                        path=normalized_member_path,
                        session=session_num,
                        output_filename=output_filename,
                        raw=raw,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SyllabusIngestError("Invalid ZIP source.") from exc
    return images


def _parse_zip_source(
    *,
    source_bytes: bytes,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None, list[_ZipLessonImage]]:
    docs = _zip_text_documents(source_bytes)
    if not docs:
        raise SyllabusIngestError("Zip archive has no supported .md or .docx files.")

    sessions, session_paths, session_source = _parse_sessions_from_zip_docs(
        docs,
        session_parse_mode=session_parse_mode,
    )
    if not sessions:
        raise SyllabusIngestError("No session headings found in zip source.")

    metadata: dict[str, str] = {}
    if session_source:
        metadata.update(
            _parse_inline_metadata(
                session_source,
                stop_on_session_header=True,
                session_parse_mode=session_parse_mode,
            )
        )

    overview_doc = max(
        docs,
        key=lambda item: (_candidate_overview_score(item.path), item.size, item.path.lower()),
    )
    overview_meta = _parse_overview(overview_doc.text)
    metadata = {**overview_meta, **metadata}

    inferred_duration = _derive_duration_from_docs(docs)
    session_numbers = {int(row.get("session") or 0) for row in sessions if int(row.get("session") or 0) > 0}
    lesson_images = _zip_lesson_images(source_bytes=source_bytes, valid_session_numbers=session_numbers)
    source_files = sorted(set(session_paths + [overview_doc.path] + [row.path for row in lesson_images]))
    title_fallback = _first_h1_title(overview_doc.text) or _first_h1_title(session_source)
    return sessions, metadata, title_fallback, source_files, inferred_duration, lesson_images


def _parse_text_source(
    *,
    source_text: str,
    overview_text: str,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None, list[_ZipLessonImage]]:
    sessions = _parse_sessions(source_text, session_parse_mode=session_parse_mode)
    if not sessions:
        raise SyllabusIngestError("No sessions found. Expected headings like: Session 01: Title")

    sessions_preamble_info = _parse_inline_metadata(
        source_text,
        stop_on_session_header=True,
        session_parse_mode=session_parse_mode,
    )
    overview_info = _parse_overview(overview_text) if overview_text else {}
    metadata = {**overview_info, **sessions_preamble_info}
    title_fallback = _first_h1_title(overview_text) or _first_h1_title(source_text)
    inferred_duration = _extract_minutes(overview_text) if overview_text else None
    return sessions, metadata, title_fallback, [], inferred_duration, []


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


def ingest_uploaded_syllabus(
    *,
    source_name: str,
    source_bytes: bytes,
    course_slug: str = "",
    course_title: str = "",
    overview_name: str = "",
    overview_bytes: bytes | None = None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    if not source_name:
        raise SyllabusIngestError("Source file name is required.")
    if not source_bytes:
        raise SyllabusIngestError("Source file is empty.")

    source_suffix = Path(source_name).suffix.lower()
    if source_suffix not in SUPPORTED_EXTENSIONS:
        raise SyllabusIngestError("Unsupported source format. Use .md, .docx, or .zip.")

    overview_text = ""
    source_files = [Path(source_name).name]
    if overview_bytes is not None:
        overview_suffix = Path(overview_name or "").suffix.lower()
        if overview_suffix not in TEXT_EXTENSIONS:
            raise SyllabusIngestError("Overview file must be .md or .docx.")
        overview_text = _read_text_blob(suffix=overview_suffix, raw=overview_bytes)
        if overview_name:
            source_files.append(Path(overview_name).name)

    if source_suffix == ".zip":
        sessions, metadata, title_fallback, zip_source_files, inferred_duration, lesson_images = _parse_zip_source(
            source_bytes=source_bytes,
            session_parse_mode=session_parse_mode,
        )
        source_kind = "zip"
        if zip_source_files:
            source_files = zip_source_files
    else:
        source_text = _read_text_blob(suffix=source_suffix, raw=source_bytes)
        sessions, metadata, title_fallback, _unused, inferred_duration, lesson_images = _parse_text_source(
            source_text=source_text,
            overview_text=overview_text,
            session_parse_mode=session_parse_mode,
        )
        source_kind = source_suffix.lstrip(".")

    if not sessions:
        raise SyllabusIngestError("No sessions found in source.")

    normalized_default_ui = _normalize_ui_level(default_ui_level) or "secondary"
    ui_level = _resolve_ui_level(metadata, default_ui_level=normalized_default_ui)
    explicit_program_profile = _normalize_ui_level(_pick_first(metadata, "program_profile"))
    program_profile = explicit_program_profile or ui_level

    chosen_title = (course_title or "").strip()
    if not chosen_title:
        chosen_title = _pick_first(metadata, "title") or title_fallback
    if not chosen_title:
        raise SyllabusIngestError("Missing course title. Provide a title or include a top-level # heading.")

    chosen_slug = (course_slug or "").strip().lower()
    if not chosen_slug:
        chosen_slug = _slugify(chosen_title).replace("-", "_")
    if not COURSE_SLUG_RE.fullmatch(chosen_slug):
        raise SyllabusIngestError("Course slug can use lowercase letters, numbers, underscores, and dashes.")

    duration_candidates = [
        _pick_first(metadata, "meeting_time"),
        _pick_first(metadata, "session_length"),
        _pick_first(metadata, "duration"),
    ]
    derived_duration = next((m for m in (_extract_minutes(text) for text in duration_candidates) if m), None)
    duration = derived_duration or inferred_duration or 75

    derived_sessions = _extract_session_count(_pick_first(metadata, "duration", "meeting_time", "total_sessions"))
    if derived_sessions and len(sessions) > derived_sessions:
        sessions = sorted(sessions, key=lambda item: int(item.get("session") or 0))[:derived_sessions]
    else:
        sessions = sorted(sessions, key=lambda item: int(item.get("session") or 0))

    grade_band = _pick_first(metadata, "grade_band", "grade_level")
    age_band = _pick_first(metadata, "age_band", "ages")
    needs = []
    if overview_text:
        sections = _collect_sections(overview_text.splitlines())
        needs = _extract_bullets(_find_section(sections, "materials"))

    root = Path(courses_root or courses_dir())
    written_dir = _write_course(
        root_dir=root,
        slug=chosen_slug,
        title=chosen_title,
        sessions=sessions,
        duration=duration,
        grade_band=grade_band,
        age_band=age_band,
        needs=needs,
        ui_level=ui_level,
        program_profile=program_profile,
        overwrite=overwrite,
        lesson_images=lesson_images,
    )
    return SyllabusIngestResult(
        course_slug=chosen_slug,
        course_title=chosen_title,
        course_dir=written_dir,
        lesson_count=len(sessions),
        source_kind=source_kind,
        source_files=sorted(set(source_files)),
        ui_level=ui_level,
    )


def ingest_uploaded_syllabus_files(
    *,
    source_upload,
    course_slug: str = "",
    course_title: str = "",
    overview_upload=None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    source_name = str(getattr(source_upload, "name", "") or "").strip()
    source_bytes = source_upload.read()
    overview_name = ""
    overview_bytes = None
    if overview_upload is not None:
        overview_name = str(getattr(overview_upload, "name", "") or "").strip()
        overview_bytes = overview_upload.read()

    return ingest_uploaded_syllabus(
        source_name=source_name,
        source_bytes=source_bytes,
        course_slug=course_slug,
        course_title=course_title,
        overview_name=overview_name,
        overview_bytes=overview_bytes,
        default_ui_level=default_ui_level,
        session_parse_mode=session_parse_mode,
        overwrite=overwrite,
        courses_root=courses_root,
    )


def ingest_uploaded_syllabus_path(
    *,
    source_path: Path,
    course_slug: str = "",
    course_title: str = "",
    overview_path: Path | None = None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    source = Path(source_path)
    if not source.exists():
        raise SyllabusIngestError(f"Source file not found: {source}")
    source_name = source.name
    source_bytes = source.read_bytes()
    overview_name = ""
    overview_bytes = None
    if overview_path is not None:
        overview = Path(overview_path)
        if not overview.exists():
            raise SyllabusIngestError(f"Overview file not found: {overview}")
        overview_name = overview.name
        overview_bytes = overview.read_bytes()

    return ingest_uploaded_syllabus(
        source_name=source_name,
        source_bytes=source_bytes,
        course_slug=course_slug,
        course_title=course_title,
        overview_name=overview_name,
        overview_bytes=overview_bytes,
        default_ui_level=default_ui_level,
        session_parse_mode=session_parse_mode,
        overwrite=overwrite,
        courses_root=courses_root,
    )


__all__ = [
    "COURSE_SLUG_RE",
    "SUPPORTED_EXTENSIONS",
    "SyllabusIngestError",
    "SyllabusIngestResult",
    "ingest_uploaded_syllabus",
    "ingest_uploaded_syllabus_files",
    "ingest_uploaded_syllabus_path",
]
