import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class RemoteComputeOperatorSnapshotCommandTests(SimpleTestCase):
    @patch(
        "hub.management.commands.export_remote_compute_operator_snapshot.build_remote_compute_operator_snapshot"
    )
    def test_command_prints_snapshot_json(self, snapshot_mock):
        snapshot_mock.return_value = {
            "status": "ok",
            "summary": {"activation_count": 2},
            "aggregate_signal": {"level": "calm", "summary": "Trend signals are calm"},
        }

        out = StringIO()
        call_command("export_remote_compute_operator_snapshot", stdout=out)

        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["summary"]["activation_count"], 2)
        self.assertEqual(payload["aggregate_signal"]["level"], "calm")
