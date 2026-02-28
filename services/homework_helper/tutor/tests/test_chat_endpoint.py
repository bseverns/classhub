import json
import os
import tempfile
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.utils import ProgrammingError
from django.test import TestCase, override_settings
from common.helper_scope import issue_scope_token

from .. import views


class HelperChatAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self._default_env_patch = patch.dict(
            "os.environ",
            {
                "HELPER_LLM_BACKEND": "mock",
                "HELPER_MOCK_RESPONSE_TEXT": "Hint",
                "HELPER_TOPIC_FILTER_MODE": "soft",
            },
            clear=False,
        )
        self._default_env_patch.start()
        self.addCleanup(self._default_env_patch.stop)

    def _scope_token(self) -> str:
        return issue_scope_token(
            context="Lesson scope: Session 1",
            topics=["scratch motion"],
            allowed_topics=["scratch motion", "sprites"],
            reference="piper_scratch",
        )

    def _post_chat(self, payload: dict, *, include_scope: bool = True):
        body = dict(payload)
        if include_scope and "scope_token" not in body:
            body["scope_token"] = self._scope_token()
        return self.client.post(
            "/helper/chat",
            data=json.dumps(body),
            content_type="application/json",
        )

    def _set_student_session(self, *, student_id: int = 101, class_id: int = 5):
        session = self.client.session
        session["student_id"] = student_id
        session["class_id"] = class_id
        session.save()

    def test_chat_requires_class_or_staff_session(self):
        resp = self._post_chat({"message": "help"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")

    def test_redact_masks_email_and_phone(self):
        raw = "Email me at student@example.org or call 612-555-0123 please."
        redacted = views._redact(raw)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
        self.assertNotIn("student@example.org", redacted)
        self.assertNotIn("612-555-0123", redacted)

    def test_chat_allows_student_session(self):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "no-store")
        self.assertEqual(resp["Pragma"], "no-cache")
        self.assertEqual(resp.json().get("text"), "Hint")
        self.assertTrue(resp.json().get("conversation_id"))

    def test_program_profile_elementary_defaults_helper_strictness_when_unset(self):
        self._set_student_session()
        previous_profile = os.environ.get("CLASSHUB_PROGRAM_PROFILE")
        previous_strictness = os.environ.get("HELPER_STRICTNESS")
        previous_filter_mode = os.environ.get("HELPER_TOPIC_FILTER_MODE")
        os.environ["CLASSHUB_PROGRAM_PROFILE"] = "elementary"
        os.environ.pop("HELPER_STRICTNESS", None)
        os.environ.pop("HELPER_TOPIC_FILTER_MODE", None)

        self.addCleanup(
            lambda: (
                os.environ.__setitem__("CLASSHUB_PROGRAM_PROFILE", previous_profile)
                if previous_profile is not None
                else os.environ.pop("CLASSHUB_PROGRAM_PROFILE", None)
            )
        )
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("HELPER_STRICTNESS", previous_strictness)
                if previous_strictness is not None
                else os.environ.pop("HELPER_STRICTNESS", None)
            )
        )
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("HELPER_TOPIC_FILTER_MODE", previous_filter_mode)
                if previous_filter_mode is not None
                else os.environ.pop("HELPER_TOPIC_FILTER_MODE", None)
            )
        )

        # Off-topic message should be redirected when elementary profile defaults topic filter to strict.
        resp = self._post_chat({"message": "Can we talk about weather today?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("strictness"), "strict")
        self.assertIn("Let's keep this focused on today's lesson topics", resp.json().get("text", ""))

    def test_explicit_helper_strictness_overrides_program_profile_default(self):
        self._set_student_session()
        with patch.dict(
            "os.environ",
            {"CLASSHUB_PROGRAM_PROFILE": "elementary", "HELPER_STRICTNESS": "light"},
            clear=False,
        ):
            resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("strictness"), "light")

    @patch("tutor.engine.backends.invoke_backend")
    def test_chat_reuses_recent_turns_when_conversation_id_is_reused(self, invoke_backend_mock):
        self._set_student_session()
        invoke_backend_mock.side_effect = [("First answer", "fake-model"), ("Second answer", "fake-model")]
        conversation_id = "123e4567-e89b-12d3-a456-426614174000"

        first = self._post_chat({"message": "First question", "conversation_id": conversation_id})
        self.assertEqual(first.status_code, 200)
        second = self._post_chat({"message": "Second question", "conversation_id": conversation_id})
        self.assertEqual(second.status_code, 200)

        second_backend_message = str(invoke_backend_mock.call_args_list[1].kwargs["message"])
        self.assertIn("Recent conversation:", second_backend_message)
        self.assertIn("First question", second_backend_message)
        self.assertIn("Tutor: First answer", second_backend_message)
        self.assertIn("Student (latest):", second_backend_message)
        self.assertIn("Second question", second_backend_message)

    @patch("tutor.engine.backends.invoke_backend")
    @patch.dict(
        "os.environ",
        {
            "HELPER_CONVERSATION_TTL_SECONDS": "1",
        },
        clear=False,
    )
    def test_chat_drops_conversation_history_after_ttl_expiry(self, invoke_backend_mock):
        self._set_student_session()
        invoke_backend_mock.side_effect = [("First answer", "fake-model"), ("After expiry", "fake-model")]
        conversation_id = "123e4567-e89b-12d3-a456-426614174002"

        first = self._post_chat({"message": "First question", "conversation_id": conversation_id})
        self.assertEqual(first.status_code, 200)

        time.sleep(1.2)

        second = self._post_chat({"message": "Second question", "conversation_id": conversation_id})
        self.assertEqual(second.status_code, 200)
        second_backend_message = str(invoke_backend_mock.call_args_list[1].kwargs["message"])
        self.assertNotIn("Recent conversation:", second_backend_message)
        self.assertNotIn("First question", second_backend_message)
        self.assertNotIn("First answer", second_backend_message)
        self.assertIn("Second question", second_backend_message)

    @patch("tutor.engine.backends.invoke_backend")
    def test_chat_reset_conversation_clears_cached_turns(self, invoke_backend_mock):
        self._set_student_session()
        invoke_backend_mock.side_effect = [
            ("Initial answer", "fake-model"),
            ("Reset answer", "fake-model"),
        ]
        conversation_id = "123e4567-e89b-12d3-a456-426614174001"

        first = self._post_chat({"message": "Initial question", "conversation_id": conversation_id})
        self.assertEqual(first.status_code, 200)
        reset = self._post_chat(
            {
                "message": "After reset",
                "conversation_id": conversation_id,
                "reset_conversation": True,
            }
        )
        self.assertEqual(reset.status_code, 200)

        second_backend_message = str(invoke_backend_mock.call_args_list[1].kwargs["message"])
        self.assertNotIn("Initial question", second_backend_message)
        self.assertNotIn("Initial answer", second_backend_message)

    @patch("tutor.engine.backends.invoke_backend")
    def test_chat_isolates_conversation_history_by_actor_and_scope(self, invoke_backend_mock):
        invoke_backend_mock.side_effect = [
            ("Scope A answer 1", "fake-model"),
            ("Scope A answer 2", "fake-model"),
            ("Scope B answer 1", "fake-model"),
            ("Actor B answer 1", "fake-model"),
        ]
        conversation_id = "123e4567-e89b-12d3-a456-4266141740aa"
        scope_a = issue_scope_token(
            context="Lesson scope: Session 1",
            topics=["scratch motion"],
            allowed_topics=["scratch motion", "sprites"],
            reference="piper_scratch",
        )
        scope_b = issue_scope_token(
            context="Lesson scope: Session 2",
            topics=["scratch loops"],
            allowed_topics=["scratch loops", "sprites"],
            reference="piper_scratch",
        )

        self._set_student_session(student_id=101, class_id=5)
        first = self._post_chat(
            {"message": "Scope A first question", "conversation_id": conversation_id, "scope_token": scope_a}
        )
        second = self._post_chat(
            {"message": "Scope A second question", "conversation_id": conversation_id, "scope_token": scope_a}
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        second_backend_message = str(invoke_backend_mock.call_args_list[1].kwargs["message"])
        self.assertIn("Recent conversation:", second_backend_message)
        self.assertIn("Scope A first question", second_backend_message)
        self.assertIn("Tutor: Scope A answer 1", second_backend_message)

        scope_switched = self._post_chat(
            {"message": "Scope B first question", "conversation_id": conversation_id, "scope_token": scope_b}
        )
        self.assertEqual(scope_switched.status_code, 200)
        scope_switched_backend_message = str(invoke_backend_mock.call_args_list[2].kwargs["message"])
        self.assertNotIn("Scope A first question", scope_switched_backend_message)
        self.assertNotIn("Scope A answer 1", scope_switched_backend_message)
        self.assertNotIn("Recent conversation:", scope_switched_backend_message)

        self._set_student_session(student_id=202, class_id=5)
        actor_switched = self._post_chat(
            {"message": "Actor B first question", "conversation_id": conversation_id, "scope_token": scope_a}
        )
        self.assertEqual(actor_switched.status_code, 200)
        actor_switched_backend_message = str(invoke_backend_mock.call_args_list[3].kwargs["message"])
        self.assertNotIn("Scope A first question", actor_switched_backend_message)
        self.assertNotIn("Scope A answer 1", actor_switched_backend_message)
        self.assertNotIn("Recent conversation:", actor_switched_backend_message)

    @patch("tutor.engine.backends.invoke_backend")
    @patch.dict(
        "os.environ",
        {
            "HELPER_CONVERSATION_MAX_MESSAGES": "2",
            "HELPER_CONVERSATION_SUMMARY_MAX_CHARS": "400",
        },
        clear=False,
    )
    def test_chat_compacts_history_into_summary_when_turn_budget_exceeded(self, invoke_backend_mock):
        self._set_student_session()
        invoke_backend_mock.side_effect = [
            ("Answer one", "fake-model"),
            ("Answer two", "fake-model"),
            ("Answer three", "fake-model"),
        ]
        conversation_id = "123e4567-e89b-12d3-a456-426614174101"

        self._post_chat({"message": "First question", "conversation_id": conversation_id})
        self._post_chat({"message": "Second question", "conversation_id": conversation_id})
        third = self._post_chat({"message": "Third question", "conversation_id": conversation_id})
        self.assertEqual(third.status_code, 200)

        third_backend_message = str(invoke_backend_mock.call_args_list[2].kwargs["message"])
        self.assertIn("Conversation summary:", third_backend_message)
        self.assertIn("First question", third_backend_message)
        self.assertIn("Recent conversation:", third_backend_message)
        self.assertIn("Second question", third_backend_message)
        self.assertIn("Student (latest):", third_backend_message)
        self.assertIn("Third question", third_backend_message)

    def test_chat_returns_intent_tag(self):
        self._set_student_session()
        resp = self._post_chat({"message": "My sprite is not working, what should I check first?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("intent"), "debug")

    def test_chat_returns_follow_up_suggestions(self):
        self._set_student_session()
        resp = self._post_chat({"message": "My sprite is not working, what should I check first?"})
        self.assertEqual(resp.status_code, 200)
        suggestions = resp.json().get("follow_up_suggestions")
        self.assertIsInstance(suggestions, list)
        self.assertGreaterEqual(len(suggestions), 1)
        self.assertLessEqual(len(suggestions), 3)
        self.assertTrue(any("try" in str(item).lower() for item in suggestions))

    def test_chat_follow_up_suggestions_change_with_intent(self):
        self._set_student_session()
        debug_resp = self._post_chat({"message": "It is not working and I am stuck."})
        concept_resp = self._post_chat({"message": "What is a sprite in Scratch?"})
        self.assertEqual(debug_resp.status_code, 200)
        self.assertEqual(concept_resp.status_code, 200)
        debug_suggestions = debug_resp.json().get("follow_up_suggestions") or []
        concept_suggestions = concept_resp.json().get("follow_up_suggestions") or []
        self.assertNotEqual(debug_suggestions, concept_suggestions)
        self.assertTrue(any("own words" in str(item).lower() for item in concept_suggestions))

    @override_settings(
        CLASSHUB_INTERNAL_EVENTS_URL="http://classhub_web:8000/internal/events/helper-chat-access",
        CLASSHUB_INTERNAL_EVENTS_TOKEN="token-123",
        CLASSHUB_INTERNAL_EVENTS_TIMEOUT_SECONDS=0.02,
    )
    def test_chat_stays_fast_when_event_forwarding_is_slow_or_unreachable(self):
        self._set_student_session()

        def _slow_unreachable(_req, timeout=None):
            time.sleep(float(timeout or 0))
            raise urllib.error.URLError("down")

        with patch("tutor.classhub_events.urllib.request.urlopen", side_effect=_slow_unreachable):
            started = time.monotonic()
            resp = self._post_chat({"message": "How do I move a sprite?"})
            elapsed = time.monotonic() - started

        self.assertEqual(resp.status_code, 200)
        self.assertLess(elapsed, 0.5)

    def test_chat_supports_mock_backend(self):
        self._set_student_session()

        with patch.dict(
            "os.environ",
            {"HELPER_MOCK_RESPONSE_TEXT": "Mock hint: start with one sprite and one motion block."},
            clear=False,
        ):
            resp = self._post_chat({"message": "How do I move a sprite?"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("text"), "Mock hint: start with one sprite and one motion block.")
            self.assertEqual(resp.json().get("model"), "mock-tutor-v1")

    @override_settings(HELPER_REMOTE_MODE_ACKNOWLEDGED=False)
    @patch.dict("os.environ", {"HELPER_LLM_BACKEND": "openai"}, clear=False)
    def test_chat_blocks_openai_until_remote_mode_is_acknowledged(self):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "remote_backend_not_acknowledged")

    @override_settings(HELPER_REMOTE_MODE_ACKNOWLEDGED=True)
    @patch("tutor.engine.backends.openai_chat", return_value=("Use one small step first.", "gpt-test"))
    @patch.dict("os.environ", {"HELPER_LLM_BACKEND": "openai"}, clear=False)
    def test_chat_allows_openai_when_remote_mode_is_acknowledged(self, _openai_mock):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Use one small step first.")
        self.assertEqual(resp.json().get("backend"), "openai")

    @patch("tutor.engine.backends.invoke_backend", return_value=("Try this step first.", "fake-model"))
    def test_chat_redacts_message_before_backend_call(self, invoke_backend_mock):
        self._set_student_session()

        resp = self._post_chat(
            {
                "message": (
                    "Need help with sprites. "
                    "Contact student@example.org or 612-555-0123."
                )
            }
        )
        self.assertEqual(resp.status_code, 200)
        backend_message = str(invoke_backend_mock.call_args.kwargs["message"])
        self.assertIn("[REDACTED_EMAIL]", backend_message)
        self.assertIn("[REDACTED_PHONE]", backend_message)
        self.assertNotIn("student@example.org", backend_message)
        self.assertNotIn("612-555-0123", backend_message)

    @patch.dict("os.environ", {"HELPER_REFERENCE_DIR": "/tmp/classhub-missing-reference"}, clear=False)
    def test_chat_uses_deterministic_piper_hardware_triage(self):
        self._set_student_session()

        resp = self._post_chat(
            {"message": "In StoryMode, my jump button in Cheeseteroid is not working after moving jumper wires."}
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("triage_mode"), "piper_hardware")
        self.assertEqual(body.get("attempts"), 0)
        self.assertTrue(body.get("follow_up_suggestions"))
        text = (body.get("text") or "").lower()
        self.assertIn("which storymode mission + step", text)
        self.assertIn("do this one check now", text)
        self.assertIn("retest only that same input", text)

    @patch.dict("os.environ", {"HELPER_PIPER_HARDWARE_TRIAGE_ENABLED": "0"}, clear=False)
    def test_chat_can_disable_piper_hardware_triage(self):
        self._set_student_session()

        resp = self._post_chat(
            {
                "message": "My StoryMode breadboard buttons are not responding.",
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Hint")
        self.assertIsNone(resp.json().get("triage_mode"))

    def test_chat_does_not_apply_piper_hardware_triage_outside_piper_context(self):
        self._set_student_session()

        token = issue_scope_token(
            context="Lesson scope: fractions",
            topics=["fractions"],
            allowed_topics=["fractions"],
            reference="fractions_reference",
        )
        resp = self._post_chat(
            {
                "message": "My breadboard button is not working.",
                "scope_token": token,
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Hint")
        self.assertIsNone(resp.json().get("triage_mode"))

    @patch("tutor.views.engine_auth.student_session_exists", return_value=False)
    def test_chat_rejects_stale_student_session(self, _exists_mock):
        self._set_student_session()

        resp = self._post_chat({"message": "help"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")

    def test_chat_requires_scope_token_for_student_sessions(self):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?"}, include_scope=False)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "missing_scope_token")

    def test_chat_rejects_invalid_scope_token(self):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?", "scope_token": "not-real-token"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invalid_scope_token")

    @patch("tutor.views.build_instructions", return_value="system instructions")
    def test_scope_token_overrides_tampered_client_scope(self, build_instructions_mock):
        self._set_student_session()

        token = issue_scope_token(
            context="Signed context",
            topics=["signed topic"],
            allowed_topics=["signed allowed"],
            reference="signed_reference",
        )
        resp = self._post_chat(
            {
                "message": "Help",
                "scope_token": token,
                "context": "tampered context",
                "topics": ["tampered topic"],
                "allowed_topics": ["tampered allowed"],
                "reference": "tampered_reference",
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("scope_verified"))
        build_kwargs = build_instructions_mock.call_args.kwargs
        self.assertEqual(build_kwargs["context"], "Signed context")
        self.assertEqual(build_kwargs["topics"], ["signed topic"])
        self.assertEqual(build_kwargs["allowed_topics"], ["signed allowed"])

    @patch("tutor.views.build_instructions", return_value="system instructions")
    def test_chat_includes_reference_citations_in_prompt_and_response(self, build_instructions_mock):
        self._set_student_session()

        with tempfile.TemporaryDirectory() as temp_dir:
            ref_path = Path(temp_dir) / "piper_scratch.md"
            ref_path.write_text(
                "\n".join(
                    [
                        "# Session 1",
                        "Check jumper seating before changing code.",
                        "",
                        "Use one-wire changes, then retest the same control.",
                        "",
                        "Shared ground must stay connected for controls to respond.",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"HELPER_REFERENCE_DIR": temp_dir},
                clear=False,
            ):
                resp = self._post_chat({"message": "My jump button does not respond in StoryMode."})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        citations = body.get("citations") or []
        self.assertTrue(citations)
        self.assertEqual(citations[0].get("id"), "L1")
        self.assertEqual(citations[0].get("source"), "piper_scratch")
        self.assertTrue(citations[0].get("text"))

        build_kwargs = build_instructions_mock.call_args.kwargs
        self.assertIn("Lesson excerpts:", build_kwargs.get("reference_citations", ""))

    def test_chat_handles_directory_reference_file_without_500(self):
        self._set_student_session()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                "os.environ",
                {"HELPER_REFERENCE_FILE": temp_dir},
                clear=False,
            ):
                resp = self._post_chat({"message": "How do I move a sprite?"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Hint")

    @patch("tutor.views.build_instructions", return_value="system instructions")
    def test_staff_unsigned_scope_fields_are_ignored(self, build_instructions_mock):
        staff = get_user_model().objects.create_user(
            username="teacher1",
            password="pw12345",
            is_staff=True,
        )
        self.client.force_login(staff)

        resp = self._post_chat(
            {
                "message": "Help",
                "context": "tampered context",
                "topics": ["tampered topic"],
                "allowed_topics": ["tampered allowed"],
                "reference": "tampered_reference",
            },
            include_scope=False,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("scope_verified"))
        build_kwargs = build_instructions_mock.call_args.kwargs
        self.assertEqual(build_kwargs["context"], "")
        self.assertEqual(build_kwargs["topics"], [])
        self.assertEqual(build_kwargs["allowed_topics"], [])


    @override_settings(HELPER_REQUIRE_SCOPE_TOKEN_FOR_STAFF=True)
    def test_staff_can_be_forced_to_require_scope_token(self):
        staff = get_user_model().objects.create_user(
            username="teacher2",
            password="pw12345",
            is_staff=True,
        )
        self.client.force_login(staff)

        resp = self._post_chat({"message": "Help"}, include_scope=False)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "missing_scope_token")

    @patch("tutor.views.emit_helper_chat_access_event")
    def test_chat_emits_helper_access_event_hook(self, event_mock):
        self._set_student_session()

        resp = self._post_chat({"message": "How do I move a sprite?"})
        self.assertEqual(resp.status_code, 200)
        event_mock.assert_called_once()
        details = event_mock.call_args.kwargs.get("details") or {}
        self.assertEqual(details.get("actor_type"), "student")
        self.assertEqual(details.get("backend"), "mock")
        self.assertEqual(details.get("intent"), "general")
        self.assertGreaterEqual(int(details.get("follow_up_suggestions_count") or 0), 1)
        self.assertFalse(details.get("conversation_compacted"))

    def test_student_session_exists_fails_open_when_classhub_table_unavailable(self):
        with patch("tutor.views.connection.cursor", side_effect=ProgrammingError("missing table")):
            self.assertTrue(views._student_session_exists(student_id=1, class_id=2))

    @override_settings(HELPER_REQUIRE_CLASSHUB_TABLE=True)
    def test_student_session_exists_fails_closed_when_classhub_table_required(self):
        with patch("tutor.views.connection.cursor", side_effect=ProgrammingError("missing table")):
            self.assertFalse(views._student_session_exists(student_id=1, class_id=2))

    @patch.dict(
        "os.environ",
        {
            "HELPER_RATE_LIMIT_PER_MINUTE": "1",
            "HELPER_RATE_LIMIT_PER_IP_PER_MINUTE": "10",
        },
        clear=False,
    )
    def test_chat_rate_limits_per_actor(self):
        self._set_student_session()

        first = self._post_chat({"message": "first"})
        second = self._post_chat({"message": "second"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json().get("error"), "rate_limited")

    @patch("tutor.views.time.sleep", return_value=None)
    @patch.dict(
        "os.environ",
        {
            "HELPER_LLM_BACKEND": "ollama",
            "HELPER_BACKEND_MAX_ATTEMPTS": "2",
            "HELPER_BACKOFF_SECONDS": "0",
        },
        clear=False,
    )
    def test_chat_retries_backend_then_succeeds(self, _sleep_mock):
        self._set_student_session()

        with patch(
            "tutor.engine.backends.ollama_chat",
            side_effect=[urllib.error.URLError("temp"), ("Recovered", "fake-model")],
        ) as chat_mock:
            resp = self._post_chat({"message": "retry please"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Recovered")
        self.assertEqual(resp.json().get("attempts"), 2)
        self.assertTrue(resp.json().get("request_id"))
        self.assertEqual(chat_mock.call_count, 2)

    @patch("tutor.views.time.sleep", return_value=None)
    @patch.dict(
        "os.environ",
        {
            "HELPER_LLM_BACKEND": "ollama",
            "HELPER_BACKEND_MAX_ATTEMPTS": "2",
            "HELPER_BACKOFF_SECONDS": "0",
        },
        clear=False,
    )
    def test_chat_returns_502_after_retry_exhausted(self, _sleep_mock):
        self._set_student_session()

        with patch(
            "tutor.engine.backends.ollama_chat",
            side_effect=urllib.error.URLError("still down"),
        ) as chat_mock:
            resp = self._post_chat({"message": "retry fail"})

        self.assertEqual(resp.status_code, 502)
        self.assertIn(resp.json().get("error"), {"ollama_error", "backend_error"})
        self.assertEqual(chat_mock.call_count, 2)

    @patch.dict("os.environ", {"HELPER_LLM_BACKEND": "ollama"}, clear=False)
    def test_chat_returns_503_when_backend_circuit_open(self):
        self._set_student_session()

        cache.set("helper:circuit_open:ollama", 1, timeout=30)
        with patch("tutor.engine.backends.ollama_chat") as chat_mock:
            resp = self._post_chat({"message": "hello"})

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "backend_unavailable")
        self.assertEqual(chat_mock.call_count, 0)

    def test_chat_fails_open_when_circuit_cache_read_errors(self):
        self._set_student_session()

        original_get = cache.get

        def flaky_get(key, *args, **kwargs):
            if key == "helper:circuit_open:ollama":
                raise RuntimeError("cache-down")
            return original_get(key, *args, **kwargs)

        with patch.object(cache, "get", side_effect=flaky_get):
            resp = self._post_chat({"message": "hello"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Hint")

    @patch("tutor.views.acquire_slot", side_effect=RuntimeError("cache-down"))
    def test_chat_fails_open_when_queue_backend_errors(self, _acquire_slot_mock):
        self._set_student_session()

        resp = self._post_chat({"message": "queue check"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("text"), "Hint")

    @patch.dict(
        "os.environ",
        {
            "HELPER_MOCK_RESPONSE_TEXT": "A" * 300,
            "HELPER_RESPONSE_MAX_CHARS": "220",
        },
        clear=False,
    )
    def test_chat_truncates_response_text(self):
        self._set_student_session()

        resp = self._post_chat({"message": "truncate"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("truncated"))
        self.assertEqual(len(resp.json().get("text") or ""), 220)
