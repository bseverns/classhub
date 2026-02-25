"""Teacher content ordering and naming helper functions."""

import re
from pathlib import Path

from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from ...models import Class, LessonVideo, gen_class_code


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


def _next_unique_class_join_code(*, exclude_class_id: int | None = None) -> str:
    join_code = gen_class_code()
    for _ in range(10):
        qs = Class.objects.filter(join_code=join_code)
        if exclude_class_id is not None:
            qs = qs.exclude(id=exclude_class_id)
        if not qs.exists():
            break
        join_code = gen_class_code()
    return join_code


def _apply_directional_reorder(items: list, *, target_id: int, direction: str, order_field: str = "order_index") -> bool:
    idx = next((i for i, item in enumerate(items) if item.id == target_id), None)
    if idx is None:
        return False

    if direction == "up" and idx > 0:
        items[idx - 1], items[idx] = items[idx], items[idx - 1]
    elif direction == "down" and idx < len(items) - 1:
        items[idx + 1], items[idx] = items[idx], items[idx + 1]

    for i, item in enumerate(items):
        if getattr(item, order_field) != i:
            setattr(item, order_field, i)
            item.save(update_fields=[order_field])
    return True


__all__ = [name for name in globals() if not name.startswith("__")]
