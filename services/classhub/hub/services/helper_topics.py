"""Helper topic parsing and defaults shared by views/services."""

from __future__ import annotations


def build_lesson_topics(front_matter: dict) -> list[str]:
    if not isinstance(front_matter, dict):
        return []

    topics = []
    makes = front_matter.get("makes")
    if makes:
        topics.append(f"Makes: {makes}")

    needs = front_matter.get("needs") or []
    if needs:
        joined = ", ".join(str(item).strip() for item in needs if item)
        if joined:
            topics.append(f"Needs: {joined}")

    videos = front_matter.get("videos") or []
    if videos:
        labels = []
        for video in videos:
            if isinstance(video, dict):
                label = video.get("id") or video.get("title")
                if label:
                    labels.append(label)
        if labels:
            topics.append("Videos: " + ", ".join(labels))

    session = front_matter.get("session")
    if session:
        topics.append(f"Session: {session}")

    helper_notes = front_matter.get("helper_notes") or []
    if helper_notes:
        notes = ", ".join(str(item).strip() for item in helper_notes if item)
        if notes:
            topics.append("Notes: " + notes)

    return topics


def build_allowed_topics(front_matter: dict) -> list[str]:
    if not isinstance(front_matter, dict):
        return []
    allowed = front_matter.get("helper_allowed_topics") or front_matter.get("allowed_topics") or []
    if isinstance(allowed, str):
        return [part.strip() for part in allowed.split("|") if part.strip()]
    if isinstance(allowed, list):
        return [str(part).strip() for part in allowed if str(part).strip()]
    return []


def split_helper_topics_text(raw: str) -> list[str]:
    parts: list[str] = []
    normalized = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.split("\n"):
        for segment in line.split("|"):
            token = segment.strip()
            if token:
                parts.append(token)
    return parts

