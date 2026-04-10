import json
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings


class HelperInternalRemoteComputeTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(HELPER_INTERNAL_API_TOKEN="")
    def test_remote_compute_status_requires_configured_token(self):
        resp = self.client.get(
            "/helper/internal/remote-compute-status",
            HTTP_AUTHORIZATION="Bearer test-token",
        )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "internal_token_not_configured")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_remote_compute_control_rejects_invalid_token(self):
        with self.assertLogs("tutor.internal_audit", level="WARNING") as captured:
            resp = self.client.post(
                "/helper/internal/remote-compute-control",
                data=json.dumps({"action": "activate", "class_id": 5, "requested_by": "teacher1"}),
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer wrong-token",
            )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")
        self.assertIn("internal_remote_compute_control_unauthorized", captured.records[0].getMessage())

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch.dict("os.environ", {"HELPER_INTERNAL_ALLOWED_CIDRS": "10.0.0.0/8"}, clear=False)
    def test_remote_compute_status_rejects_non_internal_ip(self):
        resp = self.client.get(
            "/helper/internal/remote-compute-status?class_id=7",
            HTTP_AUTHORIZATION="Bearer token-123",
            REMOTE_ADDR="198.51.100.8",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "forbidden")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED": "1",
            "CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED": "1",
            "REMOTE_LLM_BASE_URL": "https://llm-gpu.tail.creatempls.org",
            "REMOTE_LLM_API_KEY": "remote-api-key-1234567890",
            "REMOTE_LLM_MODEL": "llama3.2:3b",
            "HELPER_REMOTE_COMPUTE_PROVIDER_ADAPTER": "thunder_webhook",
            "HELPER_REMOTE_COMPUTE_ACTIVATE_URL": "https://ops.example.org/activate",
            "HELPER_REMOTE_COMPUTE_DEACTIVATE_URL": "https://ops.example.org/deactivate",
            "HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL": "https://ops.example.org/health",
        },
        clear=False,
    )
    @patch("tutor.remote_compute_provider.urllib.request.urlopen")
    @patch("tutor.remote_compute_control._remote_backend_ready_probe", return_value=(True, "", "Remote helper warm probe succeeded in 0.2 second(s)."))
    def test_remote_compute_control_activates_and_deactivates_lease(self, _ready_probe_mock, urlopen_mock):
        activate_response = MagicMock()
        activate_response.__enter__.return_value = activate_response
        activate_response.status = 200
        activate_response.read.return_value = b'{"ok": true, "state": "ready", "request_id": "req-1", "detail": "warming"}'

        health_response = MagicMock()
        health_response.__enter__.return_value = health_response
        health_response.status = 200
        health_response.read.return_value = b'{"ok": true, "state": "ready", "detail": "warm"}'

        deactivate_response = MagicMock()
        deactivate_response.__enter__.return_value = deactivate_response
        deactivate_response.status = 200
        deactivate_response.read.return_value = b'{"ok": true, "state": "off", "detail": "stopped"}'
        urlopen_mock.side_effect = [activate_response, health_response, deactivate_response]

        with self.assertLogs("tutor.internal_audit", level="INFO") as captured:
            activate_resp = self.client.post(
                "/helper/internal/remote-compute-control",
                data=json.dumps(
                    {
                        "action": "activate",
                        "class_id": 7,
                        "requested_by": "teacher1",
                        "duration_minutes": 60,
                    }
                ),
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer token-123",
            )
        self.assertEqual(activate_resp.status_code, 200)
        activate_body = activate_resp.json()
        self.assertTrue(activate_body.get("ok"))
        self.assertEqual(activate_body.get("action"), "activate")
        self.assertTrue(activate_body.get("lease", {}).get("active"))
        self.assertTrue(activate_body.get("lease", {}).get("active_for_class"))
        self.assertEqual(activate_body.get("lease", {}).get("state"), "ready")
        self.assertTrue(activate_body.get("lease", {}).get("use_remote_backend"))
        self.assertIn("internal_remote_compute_control_completed", captured.records[0].getMessage())
        self.assertIn('"class_id": 7', captured.records[0].getMessage())

        with self.assertLogs("tutor.internal_audit", level="INFO") as status_logs:
            status_resp = self.client.get(
                "/helper/internal/remote-compute-status?class_id=7",
                HTTP_AUTHORIZATION="Bearer token-123",
            )
        self.assertEqual(status_resp.status_code, 200)
        status_body = status_resp.json()
        self.assertTrue(status_body.get("active"))
        self.assertTrue(status_body.get("active_for_class"))
        self.assertEqual(status_body.get("state"), "ready")
        self.assertTrue(status_body.get("paid_usage_acknowledged"))
        self.assertEqual(status_body.get("provider_adapter"), "thunder_webhook")
        self.assertEqual(status_body.get("activation_count"), 1)
        self.assertEqual(status_body.get("ready_transition_count"), 1)
        self.assertEqual(status_body.get("remote_route_count"), 0)
        self.assertEqual(status_body.get("fallback_local_count"), 0)
        self.assertEqual(status_body.get("requested_duration_minutes_total"), 60)
        self.assertEqual(status_body.get("leased_minutes_total"), 0)
        self.assertIn("internal_remote_compute_status_read", status_logs.records[0].getMessage())
        self.assertIn('"class_id": 7', status_logs.records[0].getMessage())

        evidence_resp = self.client.get(
            "/helper/internal/remote-compute-evidence?class_id=7",
            HTTP_AUTHORIZATION="Bearer token-123",
        )
        self.assertEqual(evidence_resp.status_code, 200)
        evidence_body = evidence_resp.json()
        self.assertTrue(evidence_body.get("ok"))
        self.assertEqual(evidence_body.get("summary", {}).get("activation_count"), 1)
        self.assertEqual(evidence_body.get("summary", {}).get("requested_duration_minutes_total"), 60)
        self.assertEqual(len(evidence_body.get("recent_sessions") or []), 1)
        self.assertTrue(any(row.get("event_type") == "activation_requested" for row in (evidence_body.get("recent_events") or [])))

        deactivate_resp = self.client.post(
            "/helper/internal/remote-compute-control",
            data=json.dumps({"action": "deactivate", "class_id": 7, "requested_by": "teacher1"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
        )
        self.assertEqual(deactivate_resp.status_code, 200)
        self.assertFalse(deactivate_resp.json().get("lease", {}).get("active"))
