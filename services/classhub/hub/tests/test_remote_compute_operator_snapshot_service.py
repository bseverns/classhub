from unittest.mock import patch

from django.test import TestCase

from ..models import Class
from ..services.helper_control import HelperRemoteComputeOperatorSnapshotResult
from ..services.remote_compute_operator_snapshot import build_remote_compute_operator_snapshot


class RemoteComputeOperatorSnapshotServiceTests(TestCase):
    @patch("hub.services.remote_compute_operator_snapshot.fetch_remote_compute_operator_snapshot")
    def test_build_snapshot_adds_class_names_and_signals(self, fetch_mock):
        classroom = Class.objects.create(name="Ops Class", join_code="OPS12345")
        fetch_mock.return_value = HelperRemoteComputeOperatorSnapshotResult(
            ok=True,
            active_lease={
                "active": True,
                "class_id": classroom.id,
                "state": "ready",
                "remaining_minutes": 25,
            },
            summary={
                "class_count_with_activity": 1,
                "activation_count": 4,
                "avg_ready_seconds": 12,
                "remote_route_count": 5,
                "fallback_local_count": 0,
                "leased_minutes_total": 60,
                "approximate_cost_usd_total": "8.50",
            },
            recent_classes=[
                {
                    "class_id": classroom.id,
                    "activation_count": 4,
                    "avg_ready_seconds": 12,
                    "remote_route_count": 5,
                    "fallback_local_count": 0,
                }
            ],
        )

        snapshot = build_remote_compute_operator_snapshot(
            endpoint_url="http://helper_web:8000/helper/internal/remote-compute-operator-snapshot",
            internal_token="secret-token",
            timeout_seconds=2.0,
        )

        self.assertEqual(snapshot["status"], "ok")
        self.assertEqual(snapshot["active_lease"]["class_name"], "Ops Class")
        self.assertEqual(snapshot["aggregate_signal"]["level"], "calm")
        self.assertEqual(snapshot["recent_classes"][0]["class_name"], "Ops Class")
        self.assertEqual(snapshot["recent_classes"][0]["signal"]["level"], "calm")
