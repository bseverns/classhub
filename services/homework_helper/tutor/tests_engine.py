import urllib.error

from django.test import SimpleTestCase

from .engine import backends
from .engine import heuristics


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
