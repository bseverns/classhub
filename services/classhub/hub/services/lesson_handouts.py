"""Lesson belonging-layer and offline handout helpers."""

from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode

import qrcode
from qrcode.image.svg import SvgPathImage

from .peer_feedback import resolve_peer_feedback_starters

READING_LEVEL_STANDARD = "standard"
READING_LEVEL_SIMPLE = "simple"
READING_LEVEL_CHOICES = (READING_LEVEL_SIMPLE, READING_LEVEL_STANDARD)


def resolve_reading_level(raw_value: str) -> str:
    value = str(raw_value or "").strip().lower()
    if value == READING_LEVEL_SIMPLE:
        return READING_LEVEL_SIMPLE
    return READING_LEVEL_STANDARD


def _clean_text(value, *, max_length: int = 240) -> str:
    return " ".join(str(value or "").split())[:max_length]


def _clean_list(raw_value, *, max_items: int = 6, max_length: int = 160) -> list[str]:
    if isinstance(raw_value, str):
        candidates = [raw_value]
    elif isinstance(raw_value, (list, tuple)):
        candidates = list(raw_value)
    else:
        return []

    values: list[str] = []
    for candidate in candidates:
        text = _clean_text(candidate, max_length=max_length)
        if not text or text in values:
            continue
        values.append(text)
        if len(values) >= max_items:
            break
    return values


def _clean_glossary(raw_value) -> list[dict]:
    rows: list[dict] = []
    seen_terms: set[str] = set()

    if isinstance(raw_value, dict):
        items = [{"term": key, "definition": value} for key, value in raw_value.items()]
    elif isinstance(raw_value, (list, tuple)):
        items = list(raw_value)
    else:
        items = []

    for item in items:
        if isinstance(item, dict):
            term = _clean_text(item.get("term") or item.get("word") or "", max_length=60)
            definition = _clean_text(item.get("definition") or item.get("meaning") or "", max_length=180)
        else:
            term = ""
            definition = _clean_text(item, max_length=180)
        if not term or not definition:
            continue
        key = term.lower()
        if key in seen_terms:
            continue
        seen_terms.add(key)
        rows.append({"term": term, "definition": definition})
        if len(rows) >= 8:
            break
    return rows


def _handout_section_list(*, offline_handout: dict, reading_level: str, key: str, fallback: list[str]) -> list[str]:
    reading_levels = offline_handout.get("reading_levels")
    if isinstance(reading_levels, dict):
        selected = reading_levels.get(reading_level)
        if isinstance(selected, dict):
            values = _clean_list(selected.get(key))
            if values:
                return values
        standard = reading_levels.get(READING_LEVEL_STANDARD)
        if reading_level != READING_LEVEL_STANDARD and isinstance(standard, dict):
            values = _clean_list(standard.get(key))
            if values:
                return values
    values = _clean_list(offline_handout.get(key))
    if values:
        return values
    return list(fallback)


def _handout_goal(*, offline_handout: dict, reading_level: str, front_matter: dict) -> str:
    reading_levels = offline_handout.get("reading_levels")
    if isinstance(reading_levels, dict):
        selected = reading_levels.get(reading_level)
        if isinstance(selected, dict):
            goal = _clean_text(selected.get("goal"))
            if goal:
                return goal
    goal = _clean_text(offline_handout.get("goal"))
    if goal:
        return goal
    return _clean_text(front_matter.get("makes"))


def resolve_local_anchors(*, front_matter: dict) -> list[str]:
    raw = front_matter.get("local_anchors")
    if isinstance(raw, dict):
        ordered = [
            raw.get("neighborhood"),
            raw.get("real_life"),
            raw.get("home_version"),
        ]
        return _clean_list(ordered, max_items=3)
    return _clean_list(raw, max_items=4)


def resolve_example_variants(*, course_manifest: dict, front_matter: dict) -> list[str]:
    lesson_values = _clean_list(front_matter.get("example_variants"), max_items=6)
    if lesson_values:
        return lesson_values
    return _clean_list(course_manifest.get("example_packs") or course_manifest.get("context_pack"), max_items=6)


def resolve_community_glossary(*, course_manifest: dict, front_matter: dict) -> list[dict]:
    rows = _clean_glossary(course_manifest.get("community_glossary"))
    lesson_rows = _clean_glossary(front_matter.get("community_glossary"))
    seen = {row["term"].lower() for row in rows}
    for row in lesson_rows:
        key = row["term"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= 8:
            break
    return rows


def build_handout_context(
    *,
    course_slug: str,
    lesson_slug: str,
    course_manifest: dict,
    front_matter: dict,
    request,
    reading_level: str,
    online_path: str,
    language_code: str,
) -> dict:
    offline_handout = front_matter.get("offline_handout") if isinstance(front_matter.get("offline_handout"), dict) else {}
    local_anchors = resolve_local_anchors(front_matter=front_matter)
    example_variants = resolve_example_variants(course_manifest=course_manifest, front_matter=front_matter)
    community_glossary = resolve_community_glossary(course_manifest=course_manifest, front_matter=front_matter)
    peer_feedback = resolve_peer_feedback_starters(language_code=language_code, course_manifest=course_manifest)

    accepted = []
    submission = front_matter.get("submission")
    if isinstance(submission, dict):
        accepted = _clean_list(submission.get("accepted"), max_items=4, max_length=40)
        naming = _clean_text(submission.get("naming"), max_length=120)
    else:
        naming = ""
    if accepted or naming:
        submit_fallback = []
        if accepted:
            submit_fallback.append(f"Submit one file: {', '.join(accepted)}.")
        if naming:
            submit_fallback.append(f"Suggested file name: {naming}.")
    else:
        submit_fallback = ["Submit one artifact before you leave this session."]

    safety_fallback = _clean_list(front_matter.get("privacy"), max_items=4)
    if not safety_fallback:
        safety_fallback = [
            "Keep names, faces, and private details out of shared files unless your teacher says it is okay.",
            "If something feels unsafe to share, keep it private and tell your teacher.",
        ]

    do_now_fallback = [
        "Start the main build or practice task for this session.",
        "Save a version you can come back to.",
        "Record one thing you changed or tested.",
    ]

    handout = {
        "course_slug": course_slug,
        "lesson_slug": lesson_slug,
        "title": _clean_text(offline_handout.get("title") or front_matter.get("title") or lesson_slug, max_length=120),
        "subtitle": _clean_text(offline_handout.get("subtitle") or course_manifest.get("title") or course_slug, max_length=140),
        "goal": _handout_goal(offline_handout=offline_handout, reading_level=reading_level, front_matter=front_matter),
        "do_now": _handout_section_list(
            offline_handout=offline_handout,
            reading_level=reading_level,
            key="do_now",
            fallback=do_now_fallback,
        ),
        "submit": _handout_section_list(
            offline_handout=offline_handout,
            reading_level=reading_level,
            key="submit",
            fallback=submit_fallback,
        ),
        "safety": _handout_section_list(
            offline_handout=offline_handout,
            reading_level=reading_level,
            key="safety",
            fallback=safety_fallback,
        ),
        "comment": _handout_section_list(
            offline_handout=offline_handout,
            reading_level=reading_level,
            key="comment",
            fallback=peer_feedback,
        ),
        "needs": _clean_list(front_matter.get("needs"), max_items=5),
        "local_anchors": local_anchors[:3],
        "example_variants": example_variants[:3],
        "community_glossary": community_glossary[:4],
        "reading_level": reading_level,
        "online_url": request.build_absolute_uri(online_path),
        "print_url": f"{online_path}/handout?{urlencode({'reading_level': reading_level})}",
        "pdf_url": f"{online_path}/handout.pdf?{urlencode({'reading_level': reading_level})}",
    }
    return handout


def build_handout_qr_svg(url: str) -> str:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    stream = BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def _pdf_escape(value: str) -> str:
    ascii_value = (value or "").encode("latin-1", "replace").decode("latin-1")
    return ascii_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(value: str, *, width: int = 88) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return [""]
    return [raw[idx : idx + width] for idx in range(0, len(raw), width)]


def _handout_lines(handout: dict) -> list[str]:
    lines = [
        handout.get("title") or "Lesson handout",
        handout.get("subtitle") or "",
        "",
        f"Reading level: {handout.get('reading_level', READING_LEVEL_STANDARD).title()}",
    ]
    goal = _clean_text(handout.get("goal"), max_length=180)
    if goal:
        lines.extend(["", f"Goal: {goal}"])

    for label, values in (
        ("Do this now", handout.get("do_now") or []),
        ("What to submit", handout.get("submit") or []),
        ("Safety", handout.get("safety") or []),
        ("Peer feedback", handout.get("comment") or []),
        ("Local anchors", handout.get("local_anchors") or []),
        ("Example variants", handout.get("example_variants") or []),
    ):
        if not values:
            continue
        lines.extend(["", f"{label}:"])
        for value in values:
            wrapped = _wrap_text(f"- {value}")
            lines.extend(wrapped)

    glossary = handout.get("community_glossary") or []
    if glossary:
        lines.extend(["", "Community glossary:"])
        for row in glossary:
            wrapped = _wrap_text(f"- {row['term']}: {row['definition']}")
            lines.extend(wrapped)

    lines.extend(["", "Open online:", *(_wrap_text(handout.get("online_url") or ""))])
    return lines


def _pdf_text_stream(lines: list[str]) -> bytes:
    stream_lines = ["BT", "/F1 11 Tf", "14 TL", "54 760 Td"]
    for line in lines:
        stream_lines.append(f"({_pdf_escape(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    return ("\n".join(stream_lines) + "\n").encode("latin-1", "replace")


def _pdf_document_from_stream(stream: bytes) -> bytes:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
    pdf.extend(f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def build_handout_pdf_bytes(handout: dict) -> bytes:
    return _pdf_document_from_stream(_pdf_text_stream(_handout_lines(handout)))


__all__ = [
    "READING_LEVEL_CHOICES",
    "READING_LEVEL_SIMPLE",
    "READING_LEVEL_STANDARD",
    "build_handout_context",
    "build_handout_pdf_bytes",
    "build_handout_qr_svg",
    "resolve_community_glossary",
    "resolve_example_variants",
    "resolve_local_anchors",
    "resolve_reading_level",
]
