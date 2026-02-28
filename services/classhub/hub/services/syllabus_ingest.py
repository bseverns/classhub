"""Teacher-facing syllabus ingestion helpers (.md/.docx/.zip)."""

from __future__ import annotations

import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from .content_links import courses_dir

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

SUPPORTED_EXTENSIONS = {".md", ".docx", ".zip"}
TEXT_EXTENSIONS = {".md", ".docx"}
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
    normalized = path.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        return False
    if normalized.startswith("../") or "/../" in normalized:
        return False
    return True


def _zip_text_documents(source_bytes: bytes) -> list[_ZipTextDoc]:
    docs: list[_ZipTextDoc] = []
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > 500:
                raise SyllabusIngestError("Zip archive has too many files to ingest safely.")
            total_size = 0
            for info in infos:
                if not _safe_zip_path(info.filename):
                    continue
                total_size += int(info.file_size or 0)
                if total_size > 30 * 1024 * 1024:
                    raise SyllabusIngestError("Zip archive is too large to ingest safely.")
                suffix = Path(info.filename).suffix.lower()
                if suffix not in TEXT_EXTENSIONS:
                    continue
                raw = archive.read(info.filename)
                text = _read_text_blob(suffix=suffix, raw=raw)
                docs.append(
                    _ZipTextDoc(
                        path=info.filename.replace("\\", "/"),
                        text=text,
                        size=int(info.file_size or len(raw)),
                        suffix=suffix,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SyllabusIngestError("Invalid ZIP source.") from exc
    return docs


def _parse_zip_source(
    *,
    source_bytes: bytes,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None]:
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
    source_files = sorted(set(session_paths + [overview_doc.path]))
    title_fallback = _first_h1_title(overview_doc.text) or _first_h1_title(session_source)
    return sessions, metadata, title_fallback, source_files, inferred_duration


def _parse_text_source(
    *,
    source_text: str,
    overview_text: str,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None]:
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
    return sessions, metadata, title_fallback, [], inferred_duration


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
) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    destination = (root_dir / slug).resolve()
    root_resolved = root_dir.resolve()
    if not destination.is_relative_to(root_resolved):
        raise SyllabusIngestError("Resolved course path escapes configured courses root.")

    if destination.exists():
        if not overwrite:
            raise SyllabusIngestError(f"Course '{slug}' already exists. Enable overwrite to replace it.")
        shutil.rmtree(destination)

    tmp_dir = (root_dir / f".{slug}.tmp-{uuid.uuid4().hex}").resolve()
    if not tmp_dir.is_relative_to(root_resolved):
        raise SyllabusIngestError("Temporary write path is unsafe.")
    lessons_dir = tmp_dir / "lessons"
    tmp_dir.mkdir(parents=True, exist_ok=False)
    lessons_dir.mkdir(parents=True, exist_ok=False)

    try:
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
        sessions, metadata, title_fallback, zip_source_files, inferred_duration = _parse_zip_source(
            source_bytes=source_bytes,
            session_parse_mode=session_parse_mode,
        )
        source_kind = "zip"
        if zip_source_files:
            source_files = zip_source_files
    else:
        source_text = _read_text_blob(suffix=source_suffix, raw=source_bytes)
        sessions, metadata, title_fallback, _unused, inferred_duration = _parse_text_source(
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
