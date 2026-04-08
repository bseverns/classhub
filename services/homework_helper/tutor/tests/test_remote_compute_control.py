from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase

from ..remote_compute_control import (
    activate_remote_compute,
    active_remote_compute_overrides_for_class,
    current_remote_compute_lease,
    mark_remote_compute_degraded,
)


class RemoteComputeControlTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

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
    def test_activate_starts_then_healthcheck_promotes_remote_compute_to_ready(self, urlopen_mock):
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
        self.assertEqual(refreshed.status_detail, "warm")

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
