"""ZIP/path helper utilities for syllabus ingest."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from django.utils._os import safe_join

from .syllabus_ingest_contracts import (
    IMAGE_EXTENSIONS,
    ZIP_SESSION_FILE_RE,
    ZIP_SESSION_PATH_RE,
    SyllabusIngestError,
)


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


__all__ = [
    "_candidate_overview_score",
    "_candidate_sessions_score",
    "_extract_prefixed_session_number",
    "_normalize_zip_member_path",
    "_safe_binary_extension",
    "_safe_child_path",
    "_safe_lesson_filename",
    "_safe_zip_path",
]
