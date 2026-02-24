import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .engine import auth
from .engine import backends
from .engine import heuristics
from .engine import runtime


class BackendEngineTests(SimpleTestCase):
    def test_invoke_backend_dispatches_to_registry_interface(self):
        registry = {
            "mock": backends.CallableBackend(chat_fn=lambda instructions, message: (f"{instructions}|{message}", "m1"))
        }
        text, model = backends.invoke_backend(
            "mock",
            instructions="system",
            message="hello",
            registry=registry,
        )
        self.assertEqual(text, "system|hello")
        self.assertEqual(model, "m1")

    def test_invoke_backend_rejects_unknown_backend(self):
        with self.assertRaises(RuntimeError) as exc:
            backends.invoke_backend(
                "missing",
                instructions="system",
                message="hello",
                registry={},
            )
        self.assertEqual(str(exc.exception), "unknown_backend")

    def test_call_backend_with_retries_retries_then_succeeds(self):
        sleeps: list[float] = []
        calls = {"count": 0}

        def invoke_backend_fn(_backend: str, _instructions: str, _message: str):
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.URLError("temporary")
            return "ok", "model-1"

        text, model, attempts = backends.call_backend_with_retries(
            "ollama",
            instructions="system",
            message="hello",
            invoke_backend_fn=invoke_backend_fn,
            max_attempts=2,
            base_backoff=0.5,
            sleeper=lambda seconds: sleeps.append(seconds),
        )
        self.assertEqual(text, "ok")
        self.assertEqual(model, "model-1")
        self.assertEqual(attempts, 2)
        self.assertEqual(calls["count"], 2)
        self.assertEqual(sleeps, [0.5])

    def test_call_backend_with_retries_does_not_retry_non_retryable(self):
        calls = {"count": 0}

        def invoke_backend_fn(_backend: str, _instructions: str, _message: str):
            calls["count"] += 1
            raise RuntimeError("unknown_backend")

        with self.assertRaises(RuntimeError) as exc:
            backends.call_backend_with_retries(
                "unknown",
                instructions="system",
                message="hello",
                invoke_backend_fn=invoke_backend_fn,
                max_attempts=3,
                base_backoff=0.5,
            )
        self.assertEqual(str(exc.exception), "unknown_backend")
        self.assertEqual(calls["count"], 1)

    def test_mock_chat_uses_default_text_when_empty(self):
        text, model = backends.mock_chat(text="")
        self.assertIn("step by step", text.lower())
        self.assertEqual(model, "mock-tutor-v1")

    @patch("tutor.engine.backends.urllib.request.urlopen")
    def test_ollama_chat_parses_response_payload(self, urlopen_mock):
        ctx = MagicMock()
        ctx.__enter__.return_value.read.return_value = (
            b'{"message":{"content":"Try one block at a time."},"model":"llama-test"}'
        )
        urlopen_mock.return_value = ctx

        text, model = backends.ollama_chat(
            base_url="http://ollama:11434",
            model="llama3.2:1b",
            instructions="Tutor mode",
            message="How do I move a sprite?",
            timeout_seconds=30,
            temperature=0.2,
            top_p=0.9,
            num_predict=0,
        )
        self.assertEqual(text, "Try one block at a time.")
        self.assertEqual(model, "llama-test")


class HeuristicsEngineTests(SimpleTestCase):
    def test_truncate_response_text_limits_output(self):
        text, truncated = heuristics.truncate_response_text("A" * 260, max_chars=220)
        self.assertTrue(truncated)
        self.assertEqual(len(text), 220)

    def test_allowed_topic_overlap_requires_intersection(self):
        self.assertTrue(heuristics.allowed_topic_overlap("sprite motion blocks", ["sprite control", "events"]))
        self.assertFalse(heuristics.allowed_topic_overlap("database joins", ["scratch sprites", "motion blocks"]))

    def test_build_piper_hardware_triage_text_includes_guided_steps(self):
        text = heuristics.build_piper_hardware_triage_text("StoryMode jump button is not working")
        lowered = text.lower()
        self.assertIn("which storymode mission + step", lowered)
        self.assertIn("do this one check now", lowered)
        self.assertIn("retest only that same input", lowered)


class RuntimeEngineTests(SimpleTestCase):
    def test_redact_masks_email_and_phone(self):
        raw = "Email student@example.org or call 612-555-0123."
        redacted = runtime.redact(raw)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
        self.assertNotIn("student@example.org", redacted)
        self.assertNotIn("612-555-0123", redacted)

    def test_env_bool_parsing_uses_defaults_and_truthy_values(self):
        env = {
            "A": "true",
            "B": "0",
            "C": "",
        }
        self.assertTrue(runtime.env_bool("A", False, getenv=lambda k, d="": env.get(k, d)))
        self.assertFalse(runtime.env_bool("B", True, getenv=lambda k, d="": env.get(k, d)))
        self.assertTrue(runtime.env_bool("C", True, getenv=lambda k, d="": env.get(k, d)))


class AuthEngineTests(SimpleTestCase):
    def test_student_session_exists_respects_require_table_when_missing(self):
        fake_settings = SimpleNamespace(HELPER_REQUIRE_CLASSHUB_TABLE=False)
        allowed = auth.student_session_exists(
            connection=SimpleNamespace(),
            transaction_module=SimpleNamespace(),
            settings=fake_settings,
            student_id=1,
            class_id=2,
            table_exists_fn=lambda _table_name: False,
        )
        self.assertTrue(allowed)

        fake_settings_fail_closed = SimpleNamespace(HELPER_REQUIRE_CLASSHUB_TABLE=True)
        blocked = auth.student_session_exists(
            connection=SimpleNamespace(),
            transaction_module=SimpleNamespace(),
            settings=fake_settings_fail_closed,
            student_id=1,
            class_id=2,
            table_exists_fn=lambda _table_name: False,
        )
        self.assertFalse(blocked)

    def test_actor_key_blocks_student_when_session_invalid(self):
        request = SimpleNamespace(session={"student_id": 1, "class_id": 2})
        key = auth.actor_key(
            request=request,
            build_actor_key_fn=lambda _request: "student:1",
            student_session_exists_fn=lambda _student_id, _class_id: False,
        )
        self.assertEqual(key, "")
