"""Text and document parsing helpers for syllabus ingestion."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path

import defusedxml.ElementTree as ET

from .syllabus_ingest_contracts import (
    META_KEY_ALIASES,
    SECTION_NAMES,
    TEXT_EXTENSIONS,
    ZIP_SESSION_FILE_RE,
    SyllabusIngestError,
    _SESSION_CONNECTORS_TEMPLATE,
    _SESSION_CONNECTORS_VERBOSE,
    _ZipTextDoc,
)
from .syllabus_ingest_metadata_infer import (
    _extract_minutes,
    _infer_ui_level_from_age_band,
    _infer_ui_level_from_grade_band,
    _normalize_ui_level,
)
from .syllabus_ingest_zip_helpers import _candidate_overview_score, _candidate_sessions_score


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "session"


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
    matched_keyword = ""
    if token_lower.startswith("session"):
        matched_keyword = "session"
    elif token_lower.startswith("topic"):
        matched_keyword = "topic"
    else:
        return None
    token = token[len(matched_keyword) :].lstrip()
    if not token:
        return None

    idx = 0
    while idx < len(token) and token[idx].isdigit() and idx < 2:
        idx += 1
    
    session_num = 0
    if idx > 0:
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
    session_counter = 1
    headers: dict[int, tuple[int, str]] = {}
    for idx, line in enumerate(lines):
        parsed = _session_header_match(line, session_parse_mode)
        if parsed:
            indices.append(idx)
            header_num, title = parsed
            if header_num == 0:
                header_num = session_counter
            headers[idx] = (header_num, title)
            if header_num >= session_counter:
                session_counter = header_num + 1

    sessions = []
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(lines)
        parsed = headers.get(start)
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


__all__ = [
    "TEXT_EXTENSIONS",
    "_collect_sections",
    "_derive_duration_from_docs",
    "_extract_bullets",
    "_find_section",
    "_first_h1_title",
    "_normalize_meta_key",
    "_parse_inline_metadata",
    "_parse_overview",
    "_parse_sessions",
    "_parse_sessions_from_zip_docs",
    "_read_text_blob",
    "_slugify",
]
