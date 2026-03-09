from io import StringIO
from unittest.mock import patch

from ._shared import *  # noqa: F401,F403


class TelemetryParityCommandTests(SimpleTestCase):
    @override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
    def test_command_requires_telemetry_database_alias(self):
        with self.assertRaises(CommandError):
            call_command("check_telemetry_parity", window_days=7)

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "telemetry": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
    )
    def test_command_passes_when_no_deltas(self):
        out = StringIO()
        with patch(
            "hub.management.commands.check_telemetry_parity.Command._build_parity_report",
            return_value={
                "generated_at": "2026-03-06T00:00:00+00:00",
                "window_days": 7,
                "window_start": "2026-02-28T00:00:00+00:00",
                "section_summaries": [],
                "delta_count": 0,
                "deltas": [],
                "truncated_deltas": 0,
            },
        ):
            call_command("check_telemetry_parity", window_days=7, stdout=out)

        self.assertIn("Telemetry parity check passed", out.getvalue())

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "telemetry": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
    )
    def test_command_fails_on_drift_without_allow_drift(self):
        with patch(
            "hub.management.commands.check_telemetry_parity.Command._build_parity_report",
            return_value={
                "generated_at": "2026-03-06T00:00:00+00:00",
                "window_days": 7,
                "window_start": "2026-02-28T00:00:00+00:00",
                "section_summaries": [],
                "delta_count": 1,
                "deltas": [{"section": "sample", "key": "x", "core": 1, "telemetry": 0, "difference": -1}],
                "truncated_deltas": 0,
            },
        ):
            with self.assertRaises(CommandError):
                call_command("check_telemetry_parity", window_days=7)

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "telemetry": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
    )
    def test_command_reports_drift_with_allow_drift(self):
        out = StringIO()
        with patch(
            "hub.management.commands.check_telemetry_parity.Command._build_parity_report",
            return_value={
                "generated_at": "2026-03-06T00:00:00+00:00",
                "window_days": 7,
                "window_start": "2026-02-28T00:00:00+00:00",
                "section_summaries": [],
                "delta_count": 2,
                "deltas": [{"section": "sample", "key": "x", "core": 1, "telemetry": 0, "difference": -1}],
                "truncated_deltas": 0,
            },
        ):
            call_command("check_telemetry_parity", window_days=7, allow_drift=True, stdout=out)

        self.assertIn("Parity drift detected", out.getvalue())
