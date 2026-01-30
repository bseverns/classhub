from django import template

register = template.Library()


@register.filter
def get_item(d: dict, key):
    if not d:
        return None
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def lesson_topics(front_matter: dict) -> str:
    if not isinstance(front_matter, dict):
        return ""

    parts = []
    makes = front_matter.get("makes")
    if makes:
        parts.append(f"Makes: {makes}")

    needs = front_matter.get("needs") or []
    if needs:
        joined = ", ".join(str(item).strip() for item in needs if item)
        if joined:
            parts.append(f"Needs: {joined}")

    videos = front_matter.get("videos") or []
    if videos:
        vids = []
        for video in videos:
            if isinstance(video, dict):
                label = video.get("id") or video.get("title")
                if label:
                    vids.append(label)
        if vids:
            parts.append(f"Videos: {', '.join(vids)}")

    session = front_matter.get("session")
    if session:
        parts.append(f"Session: {session}")

    return " | ".join(parts)
