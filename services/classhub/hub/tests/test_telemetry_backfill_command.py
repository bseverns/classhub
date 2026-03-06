from io import StringIO
from unittest.mock import patch

from ._shared import *  # noqa: F401,F403


class _FakeTelemetryFiltered:
    def __init__(self, ids: set[int]):
        self._ids = ids

    def values_list(self, _field_name: str, flat: bool = False):
        if not flat:
            return [(item,) for item in sorted(self._ids)]
        return list(sorted(self._ids))


class _FakeTelemetryManager:
    def __init__(self, key_field: str):
        self._key_field = key_field
        self._inserted_ids: set[int] = set()

    def using(self, _alias: str):
        return self

    def filter(self, **kwargs):
        values = kwargs.get(f"{self._key_field}__in", [])
        query_ids = {int(value) for value in values}
        return _FakeTelemetryFiltered(self._inserted_ids.intersection(query_ids))

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        del batch_size
        del ignore_conflicts
        for obj in objs:
            value = getattr(obj, self._key_field, None)
            if value is not None:
                self._inserted_ids.add(int(value))
        return objs


class TelemetryBackfillCommandTests(TestCase):
    def _seed_core_rows(self):
        classroom = Class.objects.create(name="Backfill Class", join_code="BF123456")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Backfill Student")
        module = Module.objects.create(classroom=classroom, title="S1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={"mode": "new"},
        )
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            module=module,
            material=material,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={"result": "ok"},
        )

    @override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}})
    def test_command_requires_telemetry_database_alias(self):
        with self.assertRaises(CommandError):
            call_command("backfill_telemetry_events", dry_run=True)

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "telemetry": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
    )
    def test_dry_run_reports_pending_rows(self):
        self._seed_core_rows()
        fake_events = _FakeTelemetryManager("core_event_id")
        fake_outcomes = _FakeTelemetryManager("core_outcome_event_id")
        out = StringIO()

        with patch("hub.management.commands.backfill_telemetry_events.TelemetryStudentEvent.objects", fake_events):
            with patch(
                "hub.management.commands.backfill_telemetry_events.TelemetryStudentOutcomeEvent.objects",
                fake_outcomes,
            ):
                call_command(
                    "backfill_telemetry_events",
                    dry_run=True,
                    batch_size=1,
                    stdout=out,
                )

        output = out.getvalue()
        self.assertIn('"pending": 1', output)
        self.assertEqual(fake_events._inserted_ids, set())
        self.assertEqual(fake_outcomes._inserted_ids, set())

    @override_settings(
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            "telemetry": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
        }
    )
    def test_re_run_is_idempotent(self):
        self._seed_core_rows()
        fake_events = _FakeTelemetryManager("core_event_id")
        fake_outcomes = _FakeTelemetryManager("core_outcome_event_id")
        first = StringIO()
        second = StringIO()

        with patch("hub.management.commands.backfill_telemetry_events.TelemetryStudentEvent.objects", fake_events):
            with patch(
                "hub.management.commands.backfill_telemetry_events.TelemetryStudentOutcomeEvent.objects",
                fake_outcomes,
            ):
                call_command("backfill_telemetry_events", batch_size=10, stdout=first)
                call_command("backfill_telemetry_events", batch_size=10, stdout=second)

        self.assertIn("Inserted telemetry rows: 2", first.getvalue())
        self.assertIn("Inserted telemetry rows: 0", second.getvalue())
