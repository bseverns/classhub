"""Telemetry-aware read selectors for student event/outcome streams."""

from __future__ import annotations

from django.conf import settings

from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent

from ..models import StudentEvent, StudentOutcomeEvent

_READ_MODE_CORE = "core"
_READ_MODE_TELEMETRY = "telemetry"


def telemetry_read_mode() -> str:
    value = str(getattr(settings, "CLASSHUB_TELEMETRY_READ_MODE", _READ_MODE_CORE) or _READ_MODE_CORE).strip().lower()
    if value not in {_READ_MODE_CORE, _READ_MODE_TELEMETRY}:
        return _READ_MODE_CORE
    return value


def _telemetry_db_configured() -> bool:
    databases = getattr(settings, "DATABASES", {}) or {}
    return "telemetry" in databases


def student_event_model():
    if telemetry_read_mode() == _READ_MODE_TELEMETRY and _telemetry_db_configured():
        return TelemetryStudentEvent
    return StudentEvent


def student_outcome_event_model():
    if telemetry_read_mode() == _READ_MODE_TELEMETRY and _telemetry_db_configured():
        return TelemetryStudentOutcomeEvent
    return StudentOutcomeEvent


def student_events_queryset():
    return student_event_model().objects.all()


def student_outcome_events_queryset():
    return student_outcome_event_model().objects.all()


__all__ = [
    "student_event_model",
    "student_events_queryset",
    "student_outcome_event_model",
    "student_outcome_events_queryset",
    "telemetry_read_mode",
]

