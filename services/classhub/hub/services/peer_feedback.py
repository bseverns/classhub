"""Peer feedback sentence starter helpers."""

from __future__ import annotations

_DEFAULT_STARTERS_BY_LANGUAGE = {
    "en": [
        "I noticed...",
        "I wonder...",
        "What if...",
    ],
    "es": [
        "Noté que...",
        "Me pregunto...",
        "¿Qué pasaría si...?",
    ],
}


def _normalize_language_code(language_code: str) -> str:
    raw = str(language_code or "").strip().lower()
    if not raw:
        return "en"
    return raw.split("-", 1)[0]


def _clean_starters(raw_value) -> list[str]:
    if isinstance(raw_value, str):
        candidates = [raw_value]
    elif isinstance(raw_value, (list, tuple)):
        candidates = list(raw_value)
    else:
        return []

    starters: list[str] = []
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        if text in starters:
            continue
        starters.append(text[:120])
        if len(starters) >= 6:
            break
    return starters


def resolve_peer_feedback_starters(*, language_code: str, course_manifest: dict | None = None) -> list[str]:
    """Return peer feedback sentence starters for the active language.

    Optional course-manifest override format:

    peer_feedback_sentence_starters:
      default: ["I noticed...", "I wonder...", "What if..."]
      en: ["I noticed...", "I wonder...", "What if..."]
      es: ["Noté que...", "Me pregunto...", "¿Qué pasaría si...?"]
    """
    normalized = _normalize_language_code(language_code)
    manifest = course_manifest if isinstance(course_manifest, dict) else {}
    override = manifest.get("peer_feedback_sentence_starters")

    if isinstance(override, dict):
        for key in (normalized, str(language_code or "").strip().lower(), "default", "en"):
            starters = _clean_starters(override.get(key))
            if starters:
                return starters
    else:
        starters = _clean_starters(override)
        if starters:
            return starters

    defaults = _DEFAULT_STARTERS_BY_LANGUAGE.get(normalized) or _DEFAULT_STARTERS_BY_LANGUAGE["en"]
    return list(defaults)


__all__ = [
    "resolve_peer_feedback_starters",
]
