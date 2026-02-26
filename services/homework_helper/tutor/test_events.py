import urllib.error
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from tutor import classhub_events

class ClassHubEventForwardingTests(TestCase):
    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="http://classhub_web:8000/internal/events/helper-chat-access",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="token-123",
        CLASSHUB_INTERNAL_EVENTS_TIMEOUT_SECONDS=0.35,
    )
    def test_emit_helper_chat_access_event_uses_short_default_timeout(self):
        with patch("tutor.classhub_events.urllib.request.urlopen") as urlopen_mock:
            response = SimpleNamespace(status=200)
            urlopen_mock.return_value.__enter__.return_value = response
            classhub_events.emit_helper_chat_access_event(
                classroom_id=5,
                student_id=101,
                ip_address="127.0.0.1",
                details={"request_id": "req-1"},
            )

        self.assertEqual(urlopen_mock.call_args.kwargs.get("timeout"), 0.35)

    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="http://classhub_web:8000/internal/events/helper-chat-access",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="token-123",
        CLASSHUB_INTERNAL_EVENTS_TIMEOUT_SECONDS=3,
    )
    def test_emit_helper_chat_access_event_posts_to_internal_endpoint(self):
        with patch("tutor.classhub_events.urllib.request.urlopen") as urlopen_mock:
            response = SimpleNamespace(status=200)
            urlopen_mock.return_value.__enter__.return_value = response
            classhub_events.emit_helper_chat_access_event(
                classroom_id=5,
                student_id=101,
                ip_address="127.0.0.1",
                details={"request_id": "req-1"},
            )

        req = urlopen_mock.call_args.args[0]
        self.assertEqual(req.full_url, "http://classhub_web:8000/internal/events/helper-chat-access")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers.get("Content-type"), "application/json")
        self.assertEqual(req.headers.get("X-classhub-internal-token"), "token-123")
        self.assertEqual(urlopen_mock.call_args.kwargs.get("timeout"), 3)

    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="",
    )
    def test_emit_helper_chat_access_event_skips_when_config_missing(self):
        with patch("tutor.classhub_events.urllib.request.urlopen") as urlopen_mock:
            classhub_events.emit_helper_chat_access_event(
                classroom_id=5,
                student_id=101,
                ip_address="127.0.0.1",
                details={"request_id": "req-1"},
            )
        self.assertFalse(urlopen_mock.called)

    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="http://classhub_web:8000/internal/events/helper-chat-access",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="token-123",
    )
    def test_emit_helper_chat_access_event_swallows_http_errors(self):
        with patch(
            "tutor.classhub_events.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                url="http://classhub_web:8000/internal/events/helper-chat-access",
                code=403,
                msg="forbidden",
                hdrs=None,
                fp=None,
            ),
        ) as urlopen_mock:
            classhub_events.emit_helper_chat_access_event(
                classroom_id=5,
                student_id=101,
                ip_address="127.0.0.1",
                details={"request_id": "req-1"},
            )
        self.assertTrue(urlopen_mock.called)

    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="http://classhub_web:8000/internal/events/helper-chat-access",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="token-123",
        CLASSHUB_INTERNAL_EVENTS_TIMEOUT_SECONDS=0.35,
    )
    def test_emit_helper_chat_access_event_logs_request_id_without_payload(self):
        with (
            patch("tutor.classhub_events.urllib.request.urlopen", side_effect=urllib.error.URLError("down")),
            self.assertLogs("tutor.classhub_events", level="WARNING") as logs,
        ):
            classhub_events.emit_helper_chat_access_event(
                classroom_id=5,
                student_id=101,
                ip_address="127.0.0.1",
                details={
                    "request_id": "req-safe-1",
                    "display_name": "Ada",
                    "class_code": "JOIN1234",
                    "prompt": "my name is Ada",
                },
            )

        output = " ".join(logs.output)
        self.assertIn("req-safe-1", output)
        self.assertNotIn("display_name", output)
        self.assertNotIn("class_code", output)
        self.assertNotIn("my name is Ada", output)


