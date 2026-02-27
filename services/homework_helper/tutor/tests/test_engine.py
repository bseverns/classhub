import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ..engine import auth
from ..engine import backends
from ..engine import context_envelope
from ..engine import execution_config
from ..engine import heuristics
from ..engine import runtime
from ..engine import runtime_config


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


class RuntimeConfigEngineTests(SimpleTestCase):
    def test_resolve_program_profile_defaults_to_secondary(self):
        self.assertEqual(runtime_config.resolve_program_profile(getenv=lambda _k, d="": d), "secondary")
        self.assertEqual(
            runtime_config.resolve_program_profile(getenv=lambda _k, _d="": "unknown-profile"),
            "secondary",
        )

    def test_resolve_policy_bundle_uses_elementary_defaults(self):
        env = {
            "CLASSHUB_PROGRAM_PROFILE": "elementary",
        }
        bundle = runtime_config.resolve_policy_bundle(getenv=lambda k, d="": env.get(k, d))
        self.assertEqual(bundle.program_profile, "elementary")
        self.assertEqual(bundle.strictness, "strict")
        self.assertEqual(bundle.scope_mode, "strict")
        self.assertEqual(bundle.topic_filter_mode, "strict")

    def test_resolve_policy_bundle_honors_explicit_overrides(self):
        env = {
            "CLASSHUB_PROGRAM_PROFILE": "elementary",
            "HELPER_STRICTNESS": "light",
            "HELPER_SCOPE_MODE": "soft",
            "HELPER_TOPIC_FILTER_MODE": "soft",
        }
        bundle = runtime_config.resolve_policy_bundle(getenv=lambda k, d="": env.get(k, d))
        self.assertEqual(bundle.program_profile, "elementary")
        self.assertEqual(bundle.strictness, "light")
        self.assertEqual(bundle.scope_mode, "soft")
        self.assertEqual(bundle.topic_filter_mode, "soft")


class ExecutionConfigEngineTests(SimpleTestCase):
    def test_resolve_execution_config_applies_bounds_and_defaults(self):
        env_values = {
            "HELPER_LLM_BACKEND": "mock",
            "HELPER_REFERENCE_DIR": " /tmp/ref ",
            "HELPER_REFERENCE_MAP": '{"r":"r.md"}',
            "HELPER_REFERENCE_FILE": " /tmp/ref/r.md ",
        }

        def _env_int(name: str, default: int) -> int:
            values = {
                "HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS": 10,  # clamps up to 60
                "HELPER_CONVERSATION_MAX_MESSAGES": -5,  # clamps up to 0
                "HELPER_CONVERSATION_TTL_SECONDS": 3,  # clamps up to 60
                "HELPER_CONVERSATION_TURN_MAX_CHARS": 20,  # clamps up to 80
                "HELPER_CONVERSATION_HISTORY_MAX_CHARS": 22,  # clamps up to 300
                "HELPER_CONVERSATION_SUMMARY_MAX_CHARS": 11,  # clamps up to 200
                "HELPER_FOLLOW_UP_SUGGESTIONS_MAX": 0,  # clamps up to 1
                "HELPER_REFERENCE_MAX_CITATIONS": 0,  # clamps up to 1
                "HELPER_MAX_CONCURRENCY": 7,
                "HELPER_QUEUE_SLOT_TTL_SECONDS": 121,
            }
            return values.get(name, default)

        def _env_float(name: str, default: float) -> float:
            values = {
                "HELPER_QUEUE_MAX_WAIT_SECONDS": 9.5,
                "HELPER_QUEUE_POLL_SECONDS": 0.3,
            }
            return values.get(name, default)

        def _env_bool(name: str, default: bool) -> bool:
            values = {
                "HELPER_CONVERSATION_ENABLED": False,
                "HELPER_PIPER_HARDWARE_TRIAGE_ENABLED": False,
            }
            return values.get(name, default)

        cfg = execution_config.resolve_execution_config(
            env_int=_env_int,
            env_float=_env_float,
            env_bool=_env_bool,
            parse_csv_list=lambda _raw: [],
            default_text_language_keywords=["scratch", "sprites"],
            getenv=lambda k, d="": env_values.get(k, d),
        )
        self.assertEqual(cfg.backend, "mock")
        self.assertEqual(cfg.scope_token_max_age_seconds, 60)
        self.assertFalse(cfg.conversation_enabled)
        self.assertEqual(cfg.conversation_max_messages, 0)
        self.assertEqual(cfg.conversation_ttl_seconds, 60)
        self.assertEqual(cfg.conversation_turn_max_chars, 80)
        self.assertEqual(cfg.conversation_history_max_chars, 300)
        self.assertEqual(cfg.conversation_summary_max_chars, 200)
        self.assertEqual(cfg.follow_up_suggestions_max, 1)
        self.assertEqual(cfg.reference_dir, "/tmp/ref")
        self.assertEqual(cfg.reference_map_raw, '{"r":"r.md"}')
        self.assertEqual(cfg.default_reference_file, "/tmp/ref/r.md")
        self.assertEqual(cfg.reference_max_citations, 1)
        self.assertEqual(cfg.text_language_keywords, ["scratch", "sprites"])
        self.assertFalse(cfg.piper_hardware_triage_enabled)
        self.assertEqual(cfg.queue_max_concurrency, 7)
        self.assertEqual(cfg.queue_max_wait_seconds, 9.5)
        self.assertEqual(cfg.queue_poll_seconds, 0.3)
        self.assertEqual(cfg.queue_slot_ttl_seconds, 121)

    def test_resolve_execution_config_prefers_env_text_keywords(self):
        cfg = execution_config.resolve_execution_config(
            env_int=lambda _name, default: default,
            env_float=lambda _name, default: default,
            env_bool=lambda _name, default: default,
            parse_csv_list=lambda raw: [part.strip() for part in raw.split(",") if part.strip()],
            default_text_language_keywords=["fallback"],
            getenv=lambda key, default="": {
                "HELPER_TEXT_LANGUAGE_KEYWORDS": "rust, zig",
            }.get(key, default),
        )
        self.assertEqual(cfg.text_language_keywords, ["rust", "zig"])


class ContextEnvelopeEngineTests(SimpleTestCase):
    def test_resolve_context_envelope_loads_signed_scope(self):
        envelope = context_envelope.resolve_context_envelope(
            payload={"scope_token": "signed-token"},
            actor_type="student",
            require_scope_for_staff=True,
            max_scope_token_age_seconds=7200,
            load_scope_from_token=lambda _token, max_age_seconds: {
                "context": "Lesson scope",
                "topics": ["scratch"],
                "allowed_topics": ["scratch", "sprites"],
                "reference": "piper_scratch",
                "max_age": max_age_seconds,
            },
            signature_expired_exc=RuntimeError,
            bad_signature_exc=ValueError,
        )
        self.assertEqual(envelope.scope_token, "signed-token")
        self.assertEqual(envelope.context, "Lesson scope")
        self.assertEqual(envelope.topics, ["scratch"])
        self.assertEqual(envelope.allowed_topics, ["scratch", "sprites"])
        self.assertEqual(envelope.reference_key, "piper_scratch")
        self.assertTrue(envelope.scope_verified)

    def test_resolve_context_envelope_requires_scope_for_student(self):
        with self.assertRaises(context_envelope.ScopeResolutionError) as exc:
            context_envelope.resolve_context_envelope(
                payload={},
                actor_type="student",
                require_scope_for_staff=False,
                max_scope_token_age_seconds=7200,
                load_scope_from_token=lambda *_args, **_kwargs: {},
                signature_expired_exc=RuntimeError,
                bad_signature_exc=ValueError,
            )
        self.assertEqual(exc.exception.response_error, "missing_scope_token")
        self.assertEqual(exc.exception.log_event, "scope_token_missing")

    def test_resolve_context_envelope_marks_unsigned_scope_fields_as_ignored(self):
        envelope = context_envelope.resolve_context_envelope(
            payload={"context": "unsigned lesson hint"},
            actor_type="staff",
            require_scope_for_staff=False,
            max_scope_token_age_seconds=7200,
            load_scope_from_token=lambda *_args, **_kwargs: {},
            signature_expired_exc=RuntimeError,
            bad_signature_exc=ValueError,
        )
        self.assertFalse(envelope.scope_verified)
        self.assertTrue(envelope.ignored_unsigned_scope_fields)

    def test_resolve_context_envelope_invalid_signature_raises_scope_error(self):
        class BadSignature(Exception):
            pass

        with self.assertRaises(context_envelope.ScopeResolutionError) as exc:
            context_envelope.resolve_context_envelope(
                payload={"scope_token": "bad"},
                actor_type="student",
                require_scope_for_staff=True,
                max_scope_token_age_seconds=7200,
                load_scope_from_token=lambda *_args, **_kwargs: (_ for _ in ()).throw(BadSignature("bad")),
                signature_expired_exc=RuntimeError,
                bad_signature_exc=BadSignature,
            )
        self.assertEqual(exc.exception.response_error, "invalid_scope_token")
        self.assertEqual(exc.exception.log_event, "scope_token_invalid")


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
