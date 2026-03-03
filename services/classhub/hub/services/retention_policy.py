"""Shared class retention preset helpers."""

from __future__ import annotations

from django.conf import settings

from ..models import Class


_SEMESTER_DAYS = 180


def _int_setting(name: str, default: int) -> int:
    raw = getattr(settings, name, default)
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    return max(value, 0)


def _fallback_submission_days() -> int:
    return _int_setting("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90)


def _fallback_event_days() -> int:
    return _int_setting("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180)


def _preset_days_map(preset: str) -> tuple[int, int]:
    normalized = str(preset or "").strip().lower()
    if normalized == Class.RETENTION_ERASE_7_DAYS:
        return 7, 7
    if normalized == Class.RETENTION_KEEP_SEMESTER:
        return _SEMESTER_DAYS, _SEMESTER_DAYS
    if normalized == Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES:
        return 0, 0
    return _fallback_submission_days(), _fallback_event_days()


def class_submission_retention_days(*, classroom: Class | None, fallback_days: int | None = None) -> int:
    if classroom is None:
        if fallback_days is None:
            return _fallback_submission_days()
        return max(int(fallback_days), 0)
    preset_submission_days, _event_days = _preset_days_map(getattr(classroom, "retention_preset", ""))
    return max(int(preset_submission_days), 0)


def class_event_retention_days(*, classroom: Class | None, fallback_days: int | None = None) -> int:
    if classroom is None:
        if fallback_days is None:
            return _fallback_event_days()
        return max(int(fallback_days), 0)
    _submission_days, preset_event_days = _preset_days_map(getattr(classroom, "retention_preset", ""))
    return max(int(preset_event_days), 0)


__all__ = [
    "class_submission_retention_days",
    "class_event_retention_days",
]
