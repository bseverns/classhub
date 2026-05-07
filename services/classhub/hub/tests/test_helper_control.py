import json
from io import BytesIO
from types import SimpleNamespace
import urllib.error
from unittest.mock import patch

from django.test import SimpleTestCase

from hub.services.helper_control import (
    fetch_rag_status,
    fetch_remote_compute_operator_snapshot,
    reset_class_conversations,
    set_remote_compute_state,
)


class HelperControlServiceTests(SimpleTestCase):
    @patch("hub.services.helper_control.urllib.request.urlopen")
    def test_reset_class_conversations_sends_request_id_header_and_reads_response_request_id(self, urlopen_mock):
        response = SimpleNamespace(status=200, headers={"X-Request-ID": "helper-req-1"})
        response.read = lambda: b'{"ok": true, "deleted_conversations": 2, "archived_conversations": 0}'
        urlopen_mock.return_value.__enter__.return_value = response

        result = reset_class_conversations(
            class_id=5,
            endpoint_url="http://helper_web:8000/helper/internal/reset-class-conversations",
            internal_token="token-123",
            timeout_seconds=2.0,
        )

        req = urlopen_mock.call_args.args[0]
        self.assertTrue(
            req.headers.get("X-request-id")
            or req.headers.get("X-Request-id")
            or req.headers.get("X-Request-ID")
        )
        self.assertEqual(result.request_id, "helper-req-1")

    @patch("hub.services.helper_control.urllib.request.urlopen")
    def test_fetch_rag_status_uses_response_body_request_id_when_header_missing(self, urlopen_mock):
        response = SimpleNamespace(status=200, headers={})
        response.read = lambda: b'{"ok": true, "request_id": "helper-rag-1", "rag_enabled": true, "index_ready": false}'
        urlopen_mock.return_value.__enter__.return_value = response

        result = fetch_rag_status(
            endpoint_url="http://helper_web:8000/helper/internal/rag-status",
            internal_token="token-123",
            timeout_seconds=1.0,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.request_id, "helper-rag-1")

    @patch("hub.services.helper_control.urllib.request.urlopen")
    def test_set_remote_compute_state_returns_helper_request_id_on_error(self, urlopen_mock):
        urlopen_mock.side_effect = urllib.error.HTTPError(
            url="http://helper_web:8000/helper/internal/remote-compute-control",
            code=403,
            msg="forbidden",
            hdrs={"X-Request-ID": "helper-remote-err"},
            fp=BytesIO(b'{"error": "forbidden"}'),
        )

        result = set_remote_compute_state(
            class_id=7,
            action="activate",
            requested_by="teacher1",
            endpoint_url="http://helper_web:8000/helper/internal/remote-compute-control",
            internal_token="token-123",
            timeout_seconds=2.0,
            duration_minutes=60,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.request_id, "helper-remote-err")

    @patch("hub.services.helper_control.urllib.request.urlopen")
    def test_set_remote_compute_state_sends_stop_reason_for_deactivate(self, urlopen_mock):
        response = SimpleNamespace(status=200, headers={"X-Request-ID": "helper-remote-stop-1"})
        response.read = lambda: b'{"ok": true, "action": "deactivate", "detail": "stopped", "lease": {"state": "off"}}'
        urlopen_mock.return_value.__enter__.return_value = response

        result = set_remote_compute_state(
            class_id=7,
            action="deactivate",
            requested_by="teacher1",
            endpoint_url="http://helper_web:8000/helper/internal/remote-compute-control",
            internal_token="token-123",
            timeout_seconds=2.0,
            stop_reason="manual_stop",
        )

        self.assertTrue(result.ok)
        req = urlopen_mock.call_args.args[0]
        self.assertTrue(req.data)
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["stop_reason"], "manual_stop")

    @patch("hub.services.helper_control.urllib.request.urlopen")
    def test_fetch_remote_compute_operator_snapshot_uses_response_body_request_id_when_header_missing(self, urlopen_mock):
        response = SimpleNamespace(status=200, headers={})
        response.read = lambda: (
            b'{"ok": true, "request_id": "helper-remote-ops-1", "summary": {"activation_count": 2}, "recent_classes": [{"class_id": 7}]}'
        )
        urlopen_mock.return_value.__enter__.return_value = response

        result = fetch_remote_compute_operator_snapshot(
            endpoint_url="http://helper_web:8000/helper/internal/remote-compute-operator-snapshot",
            internal_token="token-123",
            timeout_seconds=1.0,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.request_id, "helper-remote-ops-1")
        self.assertEqual(result.summary.get("activation_count"), 2)
        self.assertEqual(result.recent_classes[0]["class_id"], 7)
