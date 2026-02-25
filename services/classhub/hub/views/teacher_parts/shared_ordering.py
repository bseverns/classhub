"""Teacher content ordering and naming helper functions."""

import re
from pathlib import Path

from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from ...models import LessonVideo


def _title_from_video_filename(filename: str) -> str:
    stem = Path(filename or "").stem
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:200] or "Untitled video"


def _next_lesson_video_order(course_slug: str, lesson_slug: str) -> int:
    try:
        max_idx = (
            LessonVideo.objects.filter(course_slug=course_slug, lesson_slug=lesson_slug)
            .aggregate(models.Max("order_index"))
            .get("order_index__max")
        )
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonvideo" in str(exc).lower():
            return 0
        raise
    return int(max_idx) + 1 if max_idx is not None else 0


def _normalize_order(qs, field: str = "order_index"):
    """Normalize order_index values to 0..N-1 in current QS order."""
    for i, obj in enumerate(qs):
        if getattr(obj, field) != i:
            setattr(obj, field, i)
            obj.save(update_fields=[field])


__all__ = [name for name in globals() if not name.startswith("__")]
