"""UI density/complexity mode helpers.

Maps learner level signals (program profile + optional course metadata) to
coarse UI modes:
- compact: lower density, fewer simultaneous controls
- standard: default layout
- expanded: denser layout for advanced cohorts
"""

from collections import Counter
import re

from .content_links import parse_course_lesson_url
from .markdown_content import load_course_manifest

_GRADE_RANGE_RE = re.compile(r"\b(k|\d{1,2})\s*(?:-|to|through)\s*(\d{1,2})\b", re.IGNORECASE)
_LEVEL_TEXT_RE = re.compile(r"\b(grades?|grade|ages?)\b", re.IGNORECASE)

_LEVEL_ALIASES = {
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

_UI_DENSITY_BY_LEVEL = {
    "elementary": "compact",
    "secondary": "standard",
    "advanced": "expanded",
}


def _normalize_level_token(raw: str) -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return ""
    token = token.replace(" ", "_").replace("-", "_")
    return _LEVEL_ALIASES.get(token, "")


def _grade_token_to_int(raw: str) -> int | None:
    token = str(raw or "").strip().lower()
    if token == "k":
        return 0
    if token.isdigit():
        return int(token)
    return None


def _infer_level_from_text(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""

    if not _LEVEL_TEXT_RE.search(text):
        return ""

    match = _GRADE_RANGE_RE.search(text.lower().replace("–", "-").replace("—", "-"))
    if not match:
        return ""

    start_grade = _grade_token_to_int(match.group(1))
    end_grade = _grade_token_to_int(match.group(2))
    if start_grade is None or end_grade is None:
        return ""

    high = max(start_grade, end_grade)
    if high <= 5:
        return "elementary"
    if high <= 12:
        return "secondary"
    return "advanced"


def _extract_level_from_mapping(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""

    for key in ("ui_level", "program_profile", "learner_level", "age_band", "grade_band"):
        level = _normalize_level_token(payload.get(key))
        if level:
            return level

    title = str(payload.get("title") or "").strip()
    inferred = _infer_level_from_text(title)
    if inferred:
        return inferred

    return ""


def _density_for_level(level: str) -> str:
    normalized = _normalize_level_token(level) or "secondary"
    return _UI_DENSITY_BY_LEVEL.get(normalized, "standard")


def default_ui_density_mode(program_profile: str) -> str:
    return _density_for_level(program_profile)


def resolve_ui_density_mode(
    *,
    program_profile: str,
    course_manifest: dict | None = None,
    lesson_front_matter: dict | None = None,
) -> str:
    lesson_level = _extract_level_from_mapping(lesson_front_matter or {})
    if lesson_level:
        return _density_for_level(lesson_level)

    course_level = _extract_level_from_mapping(course_manifest or {})
    if course_level:
        return _density_for_level(course_level)

    return default_ui_density_mode(program_profile)


def resolve_ui_density_mode_for_modules(*, modules: list, program_profile: str) -> str:
    level_counts: Counter[str] = Counter()

    for module in modules:
        for material in module.materials.all():
            if getattr(material, "type", "") != "link":
                continue
            parsed = parse_course_lesson_url(getattr(material, "url", ""))
            if not parsed:
                continue
            course_slug, _lesson_slug = parsed
            manifest = load_course_manifest(course_slug)
            level = _extract_level_from_mapping(manifest)
            if level:
                level_counts[level] += 1

    if level_counts:
        return _density_for_level(level_counts.most_common(1)[0][0])

    return default_ui_density_mode(program_profile)


__all__ = [
    "default_ui_density_mode",
    "resolve_ui_density_mode",
    "resolve_ui_density_mode_for_modules",
]
