import urllib.error
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from .. import views_chat_request
from .. import views_chat_runtime


class HelperChatRequestModuleTests(TestCase):
    def test_resolve_actor_and_client_uses_actor_and_proxy_settings(self):
        request = object()
        settings_obj = SimpleNamespace(
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=True,
            REQUEST_SAFETY_XFF_INDEX=2,
        )
        ip_kwargs = {}

        def actor_key_fn(incoming_request):
            self.assertIs(incoming_request, request)
            return "student:101:5"

        def client_ip_from_request_fn(incoming_request, *, trust_proxy_headers, xff_index):
            self.assertIs(incoming_request, request)
            ip_kwargs["trust_proxy_headers"] = trust_proxy_headers
            ip_kwargs["xff_index"] = xff_index
            return "203.0.113.9"

        actor, actor_type, client_ip = views_chat_request.resolve_actor_and_client(
            request=request,
            actor_key_fn=actor_key_fn,
            settings=settings_obj,
            client_ip_from_request_fn=client_ip_from_request_fn,
        )

        self.assertEqual(actor, "student:101:5")
        self.assertEqual(actor_type, "student")
        self.assertEqual(client_ip, "203.0.113.9")
        self.assertEqual(ip_kwargs, {"trust_proxy_headers": True, "xff_index": 2})

    def test_load_session_ids_handles_invalid_values(self):
        request = SimpleNamespace(session={"class_id": "oops", "student_id": "202"})
        classroom_id, student_id = views_chat_request.load_session_ids(request)
        self.assertEqual(classroom_id, 0)
        self.assertEqual(student_id, 202)

    def test_enforce_rate_limits_blocks_actor_before_ip_check(self):
        calls = []
        events = []

        def fixed_window_allow_fn(key, **kwargs):
            calls.append((key, kwargs))
            return False

        def log_chat_event_fn(level, event, **fields):
            events.append((level, event, fields))

        def json_response_fn(payload, *, status, request_id):
            return {"payload": payload, "status": status, "request_id": request_id}

        response = views_chat_request.enforce_rate_limits(
            actor="student:101:5",
            actor_type="student",
            client_ip="203.0.113.9",
            request_id="req-1",
            actor_limit=30,
            ip_limit=90,
            fixed_window_allow_fn=fixed_window_allow_fn,
            cache_backend=object(),
            log_chat_event_fn=log_chat_event_fn,
            json_response_fn=json_response_fn,
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0].startswith("rl:actor:"))
        self.assertEqual(response["status"], 429)
        self.assertEqual(response["payload"], {"error": "rate_limited"})
        self.assertEqual(events[0][1], "rate_limited_actor")

    def test_enforce_rate_limits_blocks_ip_after_actor_passes(self):
        call_results = iter([True, False])
        events = []

        def fixed_window_allow_fn(*_args, **_kwargs):
            return next(call_results)

        def log_chat_event_fn(level, event, **fields):
            events.append((level, event, fields))

        def json_response_fn(payload, *, status, request_id):
            return {"payload": payload, "status": status, "request_id": request_id}

        response = views_chat_request.enforce_rate_limits(
            actor="student:101:5",
            actor_type="student",
            client_ip="203.0.113.9",
            request_id="req-2",
            actor_limit=30,
            ip_limit=90,
            fixed_window_allow_fn=fixed_window_allow_fn,
            cache_backend=object(),
            log_chat_event_fn=log_chat_event_fn,
            json_response_fn=json_response_fn,
        )

        self.assertEqual(response["status"], 429)
        self.assertEqual(events[0][1], "rate_limited_ip")

    def test_enforce_rate_limits_allows_request_when_both_windows_pass(self):
        response = views_chat_request.enforce_rate_limits(
            actor="student:101:5",
            actor_type="student",
            client_ip="203.0.113.9",
            request_id="req-3",
            actor_limit=30,
            ip_limit=90,
            fixed_window_allow_fn=lambda *_args, **_kwargs: True,
            cache_backend=object(),
            log_chat_event_fn=lambda *_args, **_kwargs: None,
            json_response_fn=lambda *_args, **_kwargs: None,
        )
        self.assertIsNone(response)

    def test_parse_chat_payload_rejects_bad_json(self):
        events = []

        def log_chat_event_fn(level, event, **fields):
            events.append((level, event, fields))

        def json_response_fn(payload, *, status, request_id):
            return {"payload": payload, "status": status, "request_id": request_id}

        payload, response = views_chat_request.parse_chat_payload(
            request_body=b"{",
            request_id="req-bad-json",
            actor_type="student",
            client_ip="203.0.113.9",
            log_chat_event_fn=log_chat_event_fn,
            json_response_fn=json_response_fn,
        )

        self.assertIsNone(payload)
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"], {"error": "bad_json"})
        self.assertEqual(events[0][1], "bad_json")

    def test_parse_chat_payload_rejects_non_object(self):
        payload, response = views_chat_request.parse_chat_payload(
            request_body=b'["not", "an", "object"]',
            request_id="req-bad-type",
            actor_type="student",
            client_ip="203.0.113.9",
            log_chat_event_fn=lambda *_args, **_kwargs: None,
            json_response_fn=lambda payload, *, status, request_id: {
                "payload": payload,
                "status": status,
                "request_id": request_id,
            },
        )

        self.assertIsNone(payload)
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["payload"], {"error": "bad_json"})

    def test_parse_chat_payload_accepts_dict(self):
        payload, response = views_chat_request.parse_chat_payload(
            request_body=b'{"message":"hello"}',
            request_id="req-good",
            actor_type="student",
            client_ip="203.0.113.9",
            log_chat_event_fn=lambda *_args, **_kwargs: None,
            json_response_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(payload, {"message": "hello"})
        self.assertIsNone(response)


class HelperChatRuntimeModuleTests(TestCase):
    def test_backend_circuit_is_open_delegates_to_engine_module(self):
        cache_backend = object()
        logger_obj = object()
        with patch(
            "tutor.views_chat_runtime.engine_circuit.backend_circuit_is_open",
            return_value=True,
        ) as backend_circuit_is_open_mock:
            result = views_chat_runtime.backend_circuit_is_open(
                cache_backend=cache_backend,
                backend="ollama",
                logger=logger_obj,
            )

        self.assertTrue(result)
        backend_circuit_is_open_mock.assert_called_once_with(
            cache_backend=cache_backend,
            backend="ollama",
            logger=logger_obj,
        )

    def test_record_backend_failure_delegates_to_engine_module(self):
        cache_backend = object()
        logger_obj = object()
        with patch("tutor.views_chat_runtime.engine_circuit.record_backend_failure") as record_backend_failure_mock:
            views_chat_runtime.record_backend_failure(
                cache_backend=cache_backend,
                backend="ollama",
                threshold=5,
                ttl=30,
                logger=logger_obj,
            )

        record_backend_failure_mock.assert_called_once_with(
            cache_backend=cache_backend,
            backend="ollama",
            threshold=5,
            ttl=30,
            logger=logger_obj,
        )

    @patch.dict(
        "os.environ",
        {
            "OLLAMA_BASE_URL": "http://ollama:11434",
            "OLLAMA_MODEL": "llama3.2:1b",
        },
        clear=False,
    )
    def test_invoke_backend_uses_ollama_registry_entry(self):
        captured = {}

        def ollama_chat_fn(base_url, model, instructions, message):
            captured["base_url"] = base_url
            captured["model"] = model
            captured["instructions"] = instructions
            captured["message"] = message
            return "ollama-answer", "ollama-model-used"

        text, model = views_chat_runtime.invoke_backend(
            backend="ollama",
            instructions="system",
            message="student question",
            ollama_chat_fn=ollama_chat_fn,
            openai_chat_fn=lambda *_args, **_kwargs: ("nope", "nope"),
            mock_chat_fn=lambda: ("nope", "nope"),
        )

        self.assertEqual(text, "ollama-answer")
        self.assertEqual(model, "ollama-model-used")
        self.assertEqual(
            captured,
            {
                "base_url": "http://ollama:11434",
                "model": "llama3.2:1b",
                "instructions": "system",
                "message": "student question",
            },
        )

    @patch.dict("os.environ", {"OPENAI_MODEL": "gpt-5.2"}, clear=False)
    def test_invoke_backend_uses_openai_registry_entry(self):
        captured = {}

        def openai_chat_fn(model, instructions, message):
            captured["model"] = model
            captured["instructions"] = instructions
            captured["message"] = message
            return "openai-answer", "openai-model-used"

        text, model = views_chat_runtime.invoke_backend(
            backend="openai",
            instructions="system",
            message="student question",
            ollama_chat_fn=lambda *_args, **_kwargs: ("nope", "nope"),
            openai_chat_fn=openai_chat_fn,
            mock_chat_fn=lambda: ("nope", "nope"),
        )

        self.assertEqual(text, "openai-answer")
        self.assertEqual(model, "openai-model-used")
        self.assertEqual(
            captured,
            {
                "model": "gpt-5.2",
                "instructions": "system",
                "message": "student question",
            },
        )

    def test_invoke_backend_uses_mock_registry_entry(self):
        text, model = views_chat_runtime.invoke_backend(
            backend="mock",
            instructions="system",
            message="student question",
            ollama_chat_fn=lambda *_args, **_kwargs: ("nope", "nope"),
            openai_chat_fn=lambda *_args, **_kwargs: ("nope", "nope"),
            mock_chat_fn=lambda: ("mock-answer", "mock-model-used"),
        )

        self.assertEqual(text, "mock-answer")
        self.assertEqual(model, "mock-model-used")

    def test_call_backend_with_retries_retries_then_succeeds(self):
        call_count = {"count": 0}
        sleeps = []

        def invoke_backend_fn(backend, instructions, message):
            del backend, instructions, message
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise urllib.error.URLError("temporary")
            return "recovered", "test-model"

        text, model, attempts = views_chat_runtime.call_backend_with_retries(
            backend="ollama",
            instructions="system",
            message="student question",
            invoke_backend_fn=invoke_backend_fn,
            max_attempts=3,
            base_backoff=0.5,
            sleeper=sleeps.append,
        )

        self.assertEqual(text, "recovered")
        self.assertEqual(model, "test-model")
        self.assertEqual(attempts, 2)
        self.assertEqual(sleeps, [0.5])

    def test_call_backend_with_retries_does_not_retry_non_retryable_errors(self):
        sleeps = []

        def invoke_backend_fn(_backend, _instructions, _message):
            raise RuntimeError("unknown_backend")

        with self.assertRaises(RuntimeError) as exc_info:
            views_chat_runtime.call_backend_with_retries(
                backend="invalid",
                instructions="system",
                message="student question",
                invoke_backend_fn=invoke_backend_fn,
                max_attempts=3,
                base_backoff=0.5,
                sleeper=sleeps.append,
            )

        self.assertEqual(str(exc_info.exception), "unknown_backend")
        self.assertEqual(sleeps, [])
