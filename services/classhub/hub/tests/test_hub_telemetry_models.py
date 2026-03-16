from unittest.mock import patch

from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent

from ._shared import *  # noqa: F401,F403


class TelemetryAppendOnlyModelTests(SimpleTestCase):
    def test_student_event_save_rejects_updates(self):
        event = TelemetryStudentEvent(pk=1, event_type="class_join")

        with patch("django.db.models.Model.save") as save_mock:
            with self.assertRaisesMessage(ValueError, "append-only"):
                event.save()

        save_mock.assert_not_called()

    def test_student_outcome_event_save_rejects_updates(self):
        event = TelemetryStudentOutcomeEvent(pk=1, event_type="artifact_submitted")

        with patch("django.db.models.Model.save") as save_mock:
            with self.assertRaisesMessage(ValueError, "append-only"):
                event.save()

        save_mock.assert_not_called()

    def test_student_event_delete_requires_retention_context(self):
        event = TelemetryStudentEvent(event_type="class_join")

        with patch("django.db.models.Model.delete", return_value=(1, {})) as delete_mock:
            with self.assertRaisesMessage(ValueError, "restricted to retention workflows"):
                event.delete()

            with TelemetryStudentEvent.allow_retention_delete():
                event.delete()

        delete_mock.assert_called_once()

    def test_student_outcome_event_delete_requires_retention_context(self):
        event = TelemetryStudentOutcomeEvent(event_type="artifact_submitted")

        with patch("django.db.models.Model.delete", return_value=(1, {})) as delete_mock:
            with self.assertRaisesMessage(ValueError, "restricted to retention workflows"):
                event.delete()

            with TelemetryStudentOutcomeEvent.allow_retention_delete():
                event.delete()

        delete_mock.assert_called_once()

    def test_student_event_queryset_delete_requires_retention_context(self):
        with patch("django.db.models.query.QuerySet.delete", return_value=(1, {})) as delete_mock:
            with self.assertRaisesMessage(ValueError, "restricted to retention workflows"):
                TelemetryStudentEvent.objects.all().delete()

            with TelemetryStudentEvent.allow_retention_delete():
                TelemetryStudentEvent.objects.all().delete()

        delete_mock.assert_called_once()

    def test_student_outcome_event_queryset_delete_requires_retention_context(self):
        with patch("django.db.models.query.QuerySet.delete", return_value=(1, {})) as delete_mock:
            with self.assertRaisesMessage(ValueError, "restricted to retention workflows"):
                TelemetryStudentOutcomeEvent.objects.all().delete()

            with TelemetryStudentOutcomeEvent.allow_retention_delete():
                TelemetryStudentOutcomeEvent.objects.all().delete()

        delete_mock.assert_called_once()
