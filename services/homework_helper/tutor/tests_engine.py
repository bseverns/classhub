import urllib.error

from django.test import SimpleTestCase

from .engine import backends


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

