from django.test import TestCase, override_settings

from hub.services.telemetry_split import (
    dual_write_counters,
    record_dual_write_attempt,
    record_dual_write_failure,
    record_dual_write_success,
    reset_dual_write_counters,
)


class TelemetrySplitInstrumentationTests(TestCase):
    def setUp(self):
        reset_dual_write_counters()

    def tearDown(self):
        reset_dual_write_counters()

    def test_counters_default_to_zero(self):
        self.assertEqual(dual_write_counters(), {"attempts": 0, "successes": 0, "failures": 0})
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 0, "successes": 0, "failures": 0},
        )
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 0, "successes": 0, "failures": 0},
        )

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="dual", CLASSHUB_TELEMETRY_READ_MODE="core")
    def test_attempt_success_failure_increment_total_and_target(self):
        record_dual_write_attempt(source="unit_test", target="telemetry")
        record_dual_write_success(source="unit_test", target="telemetry")
        record_dual_write_failure(source="unit_test", target="telemetry", error="IntegrityError")

        self.assertEqual(dual_write_counters(), {"attempts": 1, "successes": 1, "failures": 1})
        self.assertEqual(
            dual_write_counters(target="telemetry"),
            {"attempts": 1, "successes": 1, "failures": 1},
        )
        self.assertEqual(
            dual_write_counters(target="core"),
            {"attempts": 0, "successes": 0, "failures": 0},
        )

    @override_settings(CLASSHUB_TELEMETRY_WRITE_MODE="off", CLASSHUB_TELEMETRY_READ_MODE="core")
    def test_failure_log_has_mode_and_status_fields(self):
        with self.assertLogs("hub.services.telemetry_split", level="WARNING") as captured:
            record_dual_write_failure(source="internal_helper_chat_access", target="core", error="DatabaseError")
        self.assertTrue(any("telemetry_split_write" in line for line in captured.output))
        self.assertTrue(any("status=failure" in line for line in captured.output))
        self.assertTrue(any("write_mode=off" in line for line in captured.output))
        self.assertTrue(any("read_mode=core" in line for line in captured.output))
