import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase


class HelperChatAuthTests(TestCase):
    def setUp(self):
        cache.clear()

    def _post_chat(self, payload: dict):
        return self.client.post(
            "/helper/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_chat_requires_class_or_staff_session(self):
        resp = self._post_chat({"message": "help"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")

    @patch("tutor.views._ollama_chat", return_value=("Try this step first.", "fake-model"))
    @patch.dict("os.environ", {"HELPER_LLM_BACKEND": "ollama"}, clear=False)
    def test_chat_allows_student_session(self, _chat_mock):
        session = self.client.session
        session["student_id"] = 101
        session["class_id"] = 5
        session.save()

        resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Try this step first.")

    @patch("tutor.views._ollama_chat", return_value=("Hint", "fake-model"))
    @patch.dict(
        "os.environ",
        {
            "HELPER_LLM_BACKEND": "ollama",
            "HELPER_RATE_LIMIT_PER_MINUTE": "1",
            "HELPER_RATE_LIMIT_PER_IP_PER_MINUTE": "10",
        },
        clear=False,
    )
    def test_chat_rate_limits_per_actor(self, _chat_mock):
        session = self.client.session
        session["student_id"] = 101
        session["class_id"] = 5
        session.save()

        first = self._post_chat({"message": "first"})
        second = self._post_chat({"message": "second"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json().get("error"), "rate_limited")
