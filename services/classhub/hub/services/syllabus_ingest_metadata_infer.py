"""Metadata inference helpers for syllabus ingestion."""

from __future__ import annotations

from .syllabus_ingest_contracts import (
    UI_LEVEL_ALIASES,
    UI_LEVEL_VALUES,
    _GRADE_RANGE_CONNECTORS,
    _SESSION_COUNT_UNITS,
)


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


def _grade_token_to_int(raw: str) -> int | None:
    token = str(raw or "").strip().lower()
    if token == "k":
        return 0
    if token.isdigit():
        return int(token)
    if len(token) > 2 and token[:-2].isdigit() and token[-2:] in {"st", "nd", "rd", "th"}:
        return int(token[:-2])
    return None


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


__all__ = [
    "_extract_minutes",
    "_extract_session_count",
    "_infer_ui_level_from_age_band",
    "_infer_ui_level_from_grade_band",
    "_normalize_ui_level",
    "_pick_first",
    "_resolve_ui_level",
]
