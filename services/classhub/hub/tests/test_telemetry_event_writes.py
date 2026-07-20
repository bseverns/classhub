from contextlib import nullcontext
from unittest.mock import patch

from ._shared import *  # noqa: F401,F403

from hub.services.telemetry_events import delete_student_event_history, write_student_event, write_student_outcome_event
from hub.services.telemetry_split import dual_write_counters, reset_dual_write_counters


class TelemetryEventWriteModeTests(TestCase):
    def setUp(self):
        reset_dual_write_counters()
        self.classroom = Class.objects.create(name="Telemetry Event Class", join_code="TEL12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.material = Material.objects.create(
            module=self.module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )

    def tearDown(self):
        reset_dual_write_counters()

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="off")
    def test_off_mode_writes_core_event_only(self):
        write_student_event(
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="unit_test",
            details={"join_mode": "new"},
            classroom=self.classroom,
            student=self.student,
            write_source="test_off_mode",
        )

        self.assertEqual(StudentEvent.objects.filter(event_type=StudentEvent.EVENT_CLASS_JOIN).count(), 1)
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 1, "successes": 1, "failures": 0},
        )
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 0, "successes": 0, "failures": 0},
        )

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="dual")
    def test_dual_mode_telemetry_failure_does_not_break_core_write(self):
        with patch(
            "hub.services.telemetry_events.TelemetryStudentEvent.objects.create",
            side_effect=RuntimeError("telemetry down"),
        ) as telemetry_create:
            write_student_event(
                event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
                source="unit_test",
                details={"request_id": "req-1"},
                classroom=self.classroom,
                student=self.student,
                write_source="test_dual_mode",
            )

        self.assertEqual(StudentEvent.objects.filter(event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS).count(), 1)
        telemetry_create.assert_called_once()
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 1, "successes": 1, "failures": 0},
        )
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 1, "successes": 0, "failures": 1},
        )

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="telemetry_only")
    def test_telemetry_only_mode_skips_core_event_write(self):
        with patch("hub.services.telemetry_events.StudentEvent.objects.create") as core_create:
            with patch("hub.services.telemetry_events.TelemetryStudentEvent.objects.create") as telemetry_create:
                write_student_event(
                    event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
                    source="unit_test",
                    details={"submission_id": 1},
                    classroom=self.classroom,
                    student=self.student,
                    write_source="test_telemetry_only_mode",
                )

        core_create.assert_not_called()
        telemetry_create.assert_called_once()
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 0, "successes": 0, "failures": 0},
        )
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 1, "successes": 1, "failures": 0},
        )

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="dual")
    def test_dual_mode_outcome_telemetry_failure_does_not_break_core_write(self):
        with patch(
            "hub.services.telemetry_events.TelemetryStudentOutcomeEvent.objects.create",
            side_effect=RuntimeError("telemetry down"),
        ) as telemetry_create:
            write_student_outcome_event(
                event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
                source="unit_test",
                details={"trigger": "upload"},
                classroom=self.classroom,
                student=self.student,
                module=self.module,
                material=self.material,
                write_source="test_dual_outcome_mode",
            )

        self.assertEqual(
            StudentOutcomeEvent.objects.filter(event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED).count(),
            1,
        )
        telemetry_create.assert_called_once()
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 1, "successes": 1, "failures": 0},
        )
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 1, "successes": 0, "failures": 1},
        )


class TelemetryEventDeleteTests(SimpleTestCase):
    @patch("hub.services.telemetry_events.transaction.atomic", side_effect=lambda **_kwargs: nullcontext())
    @patch("hub.services.telemetry_events._telemetry_db_configured", return_value=True)
    @patch("hub.services.telemetry_events.StudentOutcomeEvent.objects.filter")
    @patch("hub.services.telemetry_events.StudentEvent.objects.filter")
    @patch("hub.services.telemetry_events.TelemetryStudentOutcomeEvent.objects.using")
    @patch("hub.services.telemetry_events.TelemetryStudentEvent.objects.using")
    def test_delete_removes_split_rows_and_core_rows(
        self,
        telemetry_events_using,
        telemetry_outcomes_using,
        core_events_filter,
        core_outcomes_filter,
        _configured,
        _atomic,
    ):
        telemetry_events_using.return_value.filter.return_value.delete.return_value = (2, {})
        telemetry_outcomes_using.return_value.filter.return_value.delete.return_value = (3, {})
        core_events_filter.return_value.delete.return_value = (2, {})
        core_outcomes_filter.return_value.delete.return_value = (3, {})

        result = delete_student_event_history(classroom_id=7, student_id=11)

        self.assertTrue(result.ok)
        self.assertEqual(result.total_deleted, 10)
        telemetry_events_using.return_value.filter.assert_called_once_with(classroom_id=7, student_id=11)
        telemetry_outcomes_using.return_value.filter.assert_called_once_with(classroom_id=7, student_id=11)
        core_events_filter.assert_called_once_with(classroom_id=7, student_id=11)
        core_outcomes_filter.assert_called_once_with(classroom_id=7, student_id=11)

    @patch("hub.services.telemetry_events.transaction.atomic", side_effect=lambda **_kwargs: nullcontext())
    @patch("hub.services.telemetry_events._telemetry_db_configured", return_value=True)
    @patch("hub.services.telemetry_events.StudentEvent.objects.filter")
    @patch("hub.services.telemetry_events.TelemetryStudentEvent.objects.using")
    def test_delete_fails_closed_when_split_store_is_unavailable(
        self,
        telemetry_events_using,
        core_events_filter,
        _configured,
        _atomic,
    ):
        telemetry_events_using.return_value.filter.return_value.delete.side_effect = RuntimeError("telemetry down")

        result = delete_student_event_history(classroom_id=7, student_id=11)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "telemetry_delete_failed")
        core_events_filter.assert_not_called()
