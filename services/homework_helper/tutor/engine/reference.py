"""Reference resolution, parsing, and citation helpers."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

SAFE_REF_KEY_RE = re.compile(r"^[a-z0-9_-]+$")


def resolve_reference_file(reference_key: str | None, reference_dir: str, reference_map_raw: str) -> str:
    if not reference_key:
        return ""
    # Prefer explicit allowlist map when provided.
    if reference_map_raw:
        try:
            reference_map = json.loads(reference_map_raw)
            rel = reference_map.get(reference_key)
            if rel:
                return str(Path(reference_dir) / rel)
        except Exception:
            pass
    # Safe fallback: allow direct lookup by slug in reference_dir.
    if SAFE_REF_KEY_RE.match(reference_key):
        candidate = Path(reference_dir) / f"{reference_key}.md"
        if candidate.exists():
            return str(candidate)
    return ""


def _tokenize(text: str) -> set[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    return {p for p in parts if len(p) >= 4}


def clean_reference_line(line: str) -> str:
    value = (line or "").strip()
    if not value:
        return ""
    value = re.sub(r"^#{1,6}\s*", "", value)
    value = re.sub(r"^[-*]\s+", "", value)
    value = re.sub(r"^\d+\.\s+", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=4)
def load_reference_chunks(path_str: str, *, logger) -> tuple[str, ...]:
    if not path_str:
        return tuple()
    path = Path(path_str)
    if not path.exists():
        return tuple()
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning(
            "reference_chunks_load_failed path=%s error=%s",
            path_str,
            exc.__class__.__name__,
        )
        return tuple()
    if not text.strip():
        return tuple()

    blocks: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        cleaned = clean_reference_line(raw)
        if not cleaned:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        current.append(cleaned)
    if current:
        blocks.append(" ".join(current))

    chunks: list[str] = []
    for block in blocks:
        part = re.sub(r"\s+", " ", block).strip()
        if len(part) < 24:
            continue
        while len(part) > 420:
            split_at = part.rfind(". ", 80, 420)
            if split_at < 0:
                split_at = 420
            chunk = part[: split_at + 1].strip()
            if chunk:
                chunks.append(chunk)
            part = part[split_at + 1 :].strip()
        if part:
            chunks.append(part)
    return tuple(chunks)


def build_reference_citations(
    *,
    message: str,
    context: str,
    topics: list[str],
    reference_chunks: tuple[str, ...],
    source_label: str,
    max_items: int = 3,
) -> list[dict]:
    if not reference_chunks:
        return []
    query_tokens = _tokenize(" ".join([message, context, " ".join(topics)]))
    ranked: list[tuple[int, int, str]] = []
    for idx, chunk in enumerate(reference_chunks):
        chunk_tokens = _tokenize(chunk)
        overlap = len(query_tokens & chunk_tokens) if query_tokens else 0
        if overlap <= 0:
            continue
        score = overlap * 100 - min(idx, 40)
        ranked.append((score, idx, chunk))

    if not ranked:
        selected = list(reference_chunks[:max_items])
    else:
        ranked.sort(key=lambda row: (-row[0], row[1]))
        selected = [row[2] for row in ranked[:max_items]]

    citations: list[dict] = []
    for idx, chunk in enumerate(selected, start=1):
        citations.append(
            {
                "id": f"L{idx}",
                "source": source_label,
                "text": chunk,
            }
        )
    return citations


def format_reference_citations_for_prompt(citations: list[dict]) -> str:
    if not citations:
        return ""
    lines = []
    for citation in citations:
        lines.append(f"[{citation['id']}] {citation['text']}")
    return "Lesson excerpts:\n" + "\n".join(lines)


@lru_cache(maxsize=4)
def load_reference_text(path_str: str, *, logger) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning(
            "reference_text_load_failed path=%s error=%s",
            path_str,
            exc.__class__.__name__,
        )
        return ""
    if not text:
        return ""
    # Keep it compact for the system prompt.
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return " ".join(lines)

