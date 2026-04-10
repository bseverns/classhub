import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from ..models import (
    RemoteComputeClassMetric,
    RemoteComputeLeaseEvent,
    RemoteComputeLeaseRecord,
    RemoteComputeLeaseSession,
)
from ..remote_compute_control import (
    activate_remote_compute,
    active_remote_compute_overrides_for_class,
    current_remote_compute_lease,
    deactivate_remote_compute,
    mark_remote_compute_degraded,
    mark_remote_compute_routed,
)


class RemoteComputeControlTests(TestCase):
    def setUp(self):
        cache.clear()
        RemoteComputeLeaseEvent.objects.all().delete()
        RemoteComputeLeaseSession.objects.all().delete()
        RemoteComputeLeaseRecord.objects.all().delete()
        RemoteComputeClassMetric.objects.all().delete()

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
            "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL": "https://ops.example.org/deactivate",
            "HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL": "https://ops.example.org/health",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch("tutor.remote_compute_control._remote_backend_ready_probe", return_value=(True, "", "Remote helper warm probe succeeded in 0.2 second(s)."))
    def test_activate_starts_then_healthcheck_promotes_remote_compute_to_ready(
        self,
        _ready_probe_mock,
        urlopen_mock,
    ):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "starting", "request_id": "req-1", "detail": "booting"}'

        health_response = MagicMock()
        health_response.__enter__.return_value = health_response
        health_response.status = 200
        health_response.read.return_value = b'{"ok": true, "state": "ready", "detail": "warm"}'
        urlopen_mock.side_effect = [activate_response, health_response]

        result = activate_remote_compute(class_id=7, requested_by="teacher1", duration_minutes=60)
        self.assertTrue(result.ok)
        self.assertEqual(result.lease.state, "starting")
        self.assertFalse(result.lease.use_remote_backend)

        refreshed = current_remote_compute_lease(class_id=7, refresh=True)
        self.assertEqual(refreshed.state, "ready")
        self.assertTrue(refreshed.use_remote_backend)
        self.assertEqual(
            refreshed.status_detail,
            "Remote helper warm probe succeeded in 0.2 second(s).",
        )
        self.assertEqual(refreshed.activation_count, 1)
        self.assertEqual(refreshed.ready_transition_count, 1)
        self.assertGreaterEqual(refreshed.avg_ready_seconds, 0)
        self.assertTrue(refreshed.last_activation_at)
        self.assertTrue(refreshed.last_ready_at)

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch("tutor.remote_compute_control._remote_backend_ready_probe", return_value=(True, "", "Remote helper warm probe succeeded in 0.2 second(s)."))
    def test_active_lease_and_metrics_survive_cache_clear(self, _ready_probe_mock, urlopen_mock):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "ready", "request_id": "req-2", "detail": "warm"}'
        urlopen_mock.return_value = activate_response

        result = activate_remote_compute(class_id=7, requested_by="teacher1", duration_minutes=60)
        self.assertTrue(result.ok)
        self.assertEqual(RemoteComputeLeaseRecord.objects.count(), 1)
        self.assertEqual(RemoteComputeClassMetric.objects.filter(class_id=7).count(), 1)

        cache.clear()

        lease = current_remote_compute_lease(class_id=7)
        self.assertEqual(lease.state, "ready")
        self.assertTrue(lease.use_remote_backend)
        self.assertEqual(lease.activation_count, 1)

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch(
        "tutor.remote_compute_control._remote_backend_ready_probe",
        return_value=(False, "LLMTimeoutError", "Remote helper warm probe failed before ready verification."),
    )
    def test_activate_keeps_state_starting_when_warm_probe_fails(self, _ready_probe_mock, urlopen_mock):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "ready", "request_id": "req-3", "detail": "warm"}'
        urlopen_mock.return_value = activate_response

        result = activate_remote_compute(class_id=7, requested_by="teacher1", duration_minutes=60)

        self.assertTrue(result.ok)
        self.assertEqual(result.lease.state, "starting")
        self.assertFalse(result.lease.use_remote_backend)
        self.assertEqual(result.lease.last_error_code, "LLMTimeoutError")

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch("tutor.remote_compute_control._remote_backend_ready_probe", return_value=(True, "", "Remote helper warm probe succeeded in 0.2 second(s)."))
    def test_activate_passes_control_request_id_and_idempotency_key_to_provider(self, _ready_probe_mock, urlopen_mock):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "ready", "request_id": "req-control-1", "detail": "warm"}'
        urlopen_mock.return_value = activate_response

        result = activate_remote_compute(
            class_id=7,
            requested_by="teacher1",
            duration_minutes=60,
            control_request_id="control-req-1",
        )

        self.assertTrue(result.ok)
        req = urlopen_mock.call_args.args[0]
        self.assertEqual(req.headers.get("X-control-request-id"), "control-req-1")
        self.assertEqual(req.headers.get("X-idempotency-key"), "remote-compute:activate:7:control-req-1")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["control_request_id"], "control-req-1")
        self.assertEqual(payload["idempotency_key"], "remote-compute:activate:7:control-req-1")

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch("tutor.remote_compute_control._remote_backend_ready_probe", return_value=(True, "", "Remote helper warm probe succeeded in 0.2 second(s)."))
    def test_duplicate_activate_for_same_class_reuses_existing_lease(self, _ready_probe_mock, urlopen_mock):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "ready", "request_id": "req-dup-1", "detail": "warm"}'
        urlopen_mock.return_value = activate_response

        first = activate_remote_compute(class_id=7, requested_by="teacher1", duration_minutes=60)
        second = activate_remote_compute(class_id=7, requested_by="teacher1", duration_minutes=60)

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(second.lease.state, "ready")
        self.assertEqual(urlopen_mock.call_count, 1)
        session = RemoteComputeLeaseSession.objects.order_by("-id").first()
        self.assertIsNotNone(session)
        self.assertTrue(
            RemoteComputeLeaseEvent.objects.filter(
                lease_session=session,
                event_type="activation_duplicate_ignored",
                reason_code="already_active_same_class",
            ).exists()
        )

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
        },
        clear=False,
    )
    def test_remote_overrides_require_ready_state(self):
        cache.set(
            "helper:remote_compute:lease",
            {
                "state": "starting",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": "2026-04-08T12:00:00+00:00",
                "expires_at": "2099-04-08T13:30:00+00:00",
            },
            timeout=3600,
        )

        overrides = active_remote_compute_overrides_for_class(class_id=22)
        self.assertEqual(overrides, {})

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
        },
        clear=False,
    )
    def test_mark_remote_compute_degraded_moves_state_out_of_ready(self):
        cache.set(
            "helper:remote_compute:lease",
            {
                "state": "ready",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": "2026-04-08T12:00:00+00:00",
                "expires_at": "2099-04-08T13:30:00+00:00",
            },
            timeout=3600,
        )

        mark_remote_compute_degraded(class_id=22, error_code="LLMUpstreamUnavailableError")
        lease = current_remote_compute_lease(class_id=22)
        self.assertEqual(lease.state, "degraded")
        self.assertFalse(lease.use_remote_backend)
        self.assertEqual(lease.last_error_code, "LLMUpstreamUnavailableError")
        self.assertEqual(lease.degraded_transition_count, 1)

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
        },
        clear=False,
    )
    def test_mark_remote_compute_routed_increments_route_count(self):
        cache.set(
            "helper:remote_compute:lease",
            {
                "state": "ready",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": "2026-04-08T12:00:00+00:00",
                "expires_at": "2099-04-08T13:30:00+00:00",
            },
            timeout=3600,
        )

        mark_remote_compute_routed(class_id=22)
        lease = current_remote_compute_lease(class_id=22)
        self.assertEqual(lease.remote_route_count, 1)
        self.assertTrue(lease.last_routed_at)

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL": "https://ops.example.org/deactivate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    def test_deactivate_counts_unused_activation_when_no_remote_route_occurred(self, urlopen_mock):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b'{"ok": true, "state": "off", "detail": "stopped"}'
        urlopen_mock.return_value = response
        cache.set(
            "helper:remote_compute:lease",
            {
                "state": "ready",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": "2026-04-08T12:00:00+00:00",
                "expires_at": "2099-04-08T13:30:00+00:00",
                "last_routed_at": "",
            },
            timeout=3600,
        )

        result = deactivate_remote_compute(class_id=22, requested_by="teacher1")
        self.assertTrue(result.ok)
        lease = current_remote_compute_lease(class_id=22)
        self.assertEqual(lease.state, "off")
        self.assertEqual(lease.unused_activation_count, 1)

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL": "https://ops.example.org/deactivate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_control.build_remote_compute_provider")
    def test_deactivate_is_noop_when_lease_is_already_off(self, provider_factory_mock):
        result = deactivate_remote_compute(
            class_id=22,
            requested_by="teacher1",
            control_request_id="control-stop-1",
            stop_reason="manual_stop",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.lease.state, "off")
        self.assertEqual(result.detail, "Remote helper compute is already off for this class.")
        provider_factory_mock.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL": "https://ops.example.org/health",
        },
        clear=False,
    )
    @patch(
        "tutor.remote_compute_control._remote_backend_ready_probe",
        return_value=(False, "remote_compute_probe_slow", "Remote helper warm probe exceeded 12 second(s)."),
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    def test_refresh_keeps_requested_lease_out_of_ready_when_warm_probe_is_slow(
        self,
        urlopen_mock,
        _ready_probe_mock,
    ):
        health_response = MagicMock()
        health_response.__enter__.return_value = health_response
        health_response.status = 200
        health_response.read.return_value = b'{"ok": true, "state": "ready", "detail": "warm"}'
        urlopen_mock.return_value = health_response
        RemoteComputeLeaseRecord.objects.update_or_create(
            slot="active",
            defaults={
                "state": "starting",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": "2026-04-08T12:00:00+00:00",
                "expires_at": "2099-04-08T13:30:00+00:00",
            },
        )

        lease = current_remote_compute_lease(class_id=22, refresh=True)

        self.assertEqual(lease.state, "starting")
        self.assertFalse(lease.use_remote_backend)
        self.assertEqual(lease.last_error_code, "remote_compute_probe_slow")

    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL": "https://ops.example.org/deactivate",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_control.build_remote_compute_provider")
    def test_expired_lease_auto_stops_and_records_auto_stop_evidence(self, provider_factory_mock):
        now = timezone.now()
        session = RemoteComputeLeaseSession.objects.create(
            class_id=22,
            requested_by="teacher1",
            requested_at=now - timedelta(minutes=91),
            requested_duration_minutes=90,
            expires_at=now - timedelta(minutes=1),
            provider_label="thunder-orchestration",
            provider_adapter="thunder_webhook",
            provider_request_id="req-expired-1",
            active=True,
            current_state="ready",
            last_transition_at=now - timedelta(minutes=89),
            status_detail="Warm probe passed.",
        )
        RemoteComputeLeaseRecord.objects.update_or_create(
            slot="active",
            defaults={
                "state": "ready",
                "class_id": 22,
                "requested_by": "teacher1",
                "requested_at": now - timedelta(minutes=91),
                "expires_at": now - timedelta(minutes=1),
                "requested_duration_minutes": 90,
                "provider_request_id": "req-expired-1",
                "lease_session_id": session.id,
                "status_detail": "Warm probe passed.",
                "last_transition_at": now - timedelta(minutes=89),
            },
        )
        provider_factory_mock.return_value.deactivate.return_value = MagicMock(
            ok=True,
            state="off",
            detail="stopped",
            error_code="",
            status_code=200,
            provider_request_id="req-expired-1",
        )

        lease = current_remote_compute_lease(class_id=22)

        self.assertEqual(lease.state, "off")
        self.assertFalse(lease.active)
        session.refresh_from_db()
        self.assertFalse(session.active)
        self.assertEqual(session.current_state, "off")
        self.assertEqual(session.auto_stop_count, 1)
        self.assertIsNotNone(session.ended_at)
        self.assertTrue(
            RemoteComputeLeaseEvent.objects.filter(
                lease_session=session,
                event_type="lease_expired_auto_stop",
                reason_code="lease_expired",
            ).exists()
        )
