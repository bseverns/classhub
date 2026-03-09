from ._shared import *  # noqa: F401,F403

from hub.services.telemetry_reads import (
    student_event_model,
    student_events_queryset,
    student_outcome_event_model,
    student_outcome_events_queryset,
)
from hub.models import StudentEvent, StudentOutcomeEvent
from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent


_SQLITE_MEMORY_DB = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}


class TelemetryReadSelectorTests(SimpleTestCase):
    @override_settings(
        CLASSHUB_TELEMETRY_READ_MODE="core",
        DATABASES={"default": _SQLITE_MEMORY_DB},
    )
    def test_core_mode_uses_core_models(self):
        self.assertIs(student_event_model(), StudentEvent)
        self.assertIs(student_outcome_event_model(), StudentOutcomeEvent)
        self.assertIs(student_events_queryset().model, StudentEvent)
        self.assertIs(student_outcome_events_queryset().model, StudentOutcomeEvent)

    @override_settings(
        CLASSHUB_TELEMETRY_READ_MODE="telemetry",
        DATABASES={"default": _SQLITE_MEMORY_DB},
    )
    def test_telemetry_mode_without_configured_db_falls_back_to_core_models(self):
        self.assertIs(student_event_model(), StudentEvent)
        self.assertIs(student_outcome_event_model(), StudentOutcomeEvent)
        self.assertIs(student_events_queryset().model, StudentEvent)
        self.assertIs(student_outcome_events_queryset().model, StudentOutcomeEvent)

    @override_settings(
        CLASSHUB_TELEMETRY_READ_MODE="telemetry",
        DATABASES={"default": _SQLITE_MEMORY_DB, "telemetry": _SQLITE_MEMORY_DB},
    )
    def test_telemetry_mode_with_configured_db_uses_telemetry_models(self):
        self.assertIs(student_event_model(), TelemetryStudentEvent)
        self.assertIs(student_outcome_event_model(), TelemetryStudentOutcomeEvent)
        self.assertIs(student_events_queryset().model, TelemetryStudentEvent)
        self.assertIs(student_outcome_events_queryset().model, TelemetryStudentOutcomeEvent)

