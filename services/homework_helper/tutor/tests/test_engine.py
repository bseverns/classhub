import json
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ..engine import auth
from ..engine import backends
from ..engine import config_source
from ..engine import context_envelope
from ..engine import execution_config
from ..engine import heuristics
from ..engine import rag
from ..engine import reference
from ..engine import runtime
from ..engine import runtime_config
from .. import policy


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

    @patch("tutor.engine.backends.chat_with_provider")
    def test_openai_chat_routes_through_provider_layer(self, chat_with_provider_mock):
        chat_with_provider_mock.return_value = SimpleNamespace(text="Use one hint.", model="gpt-5.2")

        text, model = backends.openai_chat(
            api_key="test-key",
            model="gpt-5.2",
            instructions="Tutor mode",
            message="How do I start?",
            max_output_tokens=64,
        )

        self.assertEqual(text, "Use one hint.")
        self.assertEqual(model, "gpt-5.2")
        chat_with_provider_mock.assert_called_once_with(
            "openai_responses",
            instructions="Tutor mode",
            message="How do I start?",
        )

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
            num_ctx=4096,
            num_predict=0,
        )
        self.assertEqual(text, "Try one block at a time.")
        self.assertEqual(model, "llama-test")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.headers.get("Content-type"), "application/json")
        self.assertEqual(request.headers.get("Accept"), "application/json")
        self.assertEqual(request.headers.get("User-agent"), "ClassHub-HomeworkHelper/1.0")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["options"]["num_ctx"], 4096)

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "ollama",
            "LLM_MODEL": "llama3.2:3b",
            "LLM_BASE_URL": "https://gpu-ollama.example-tail.ts.net",
            "LLM_MAX_TOKENS": "64",
            "LLM_NUM_CTX": "4096",
        },
        clear=False,
    )
    def test_helper_getenv_supports_generic_llm_aliases(self):
        self.assertEqual(config_source.helper_getenv("HELPER_LLM_BACKEND", ""), "ollama")
        self.assertEqual(config_source.helper_getenv("OLLAMA_MODEL", ""), "llama3.2:3b")
        self.assertEqual(config_source.helper_getenv("OLLAMA_BASE_URL", ""), "https://gpu-ollama.example-tail.ts.net")
        self.assertEqual(config_source.helper_getenv("OLLAMA_NUM_PREDICT", ""), "64")
        self.assertEqual(config_source.helper_getenv("OLLAMA_NUM_CTX", ""), "4096")

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "ollama",
            "LLM_MODEL": "llama3.2:3b",
            "LLM_BASE_URL": "https://gpu-ollama.example-tail.ts.net",
        },
        clear=False,
    )
    def test_llm_description_marks_remote_ollama_as_private(self):
        from ..llm import service as llm_service

        details = llm_service.describe_backend("ollama")

        self.assertEqual(details["provider"], "ollama")
        self.assertTrue(details["remote_private"])
        self.assertEqual(details["model"], "llama3.2:3b")
        self.assertEqual(details["base_url"], "https://gpu-ollama.example-tail.ts.net")
        self.assertEqual(details["base_url_display"], "https://<private-host>")

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "ollama",
            "LLM_MODEL": "llama3.2:3b",
            "LLM_BASE_URL": "https://gpu-ollama.example-tail.ts.net",
        },
        clear=False,
    )
    def test_public_llm_description_omits_base_url(self):
        from ..llm import service as llm_service

        details = llm_service.describe_backend_public("ollama")

        self.assertNotIn("base_url", details)
        self.assertTrue(details["remote_private"])


class HeuristicsEngineTests(SimpleTestCase):
    def test_truncate_response_text_limits_output(self):
        text, truncated = heuristics.truncate_response_text("A" * 260, max_chars=220)
        self.assertTrue(truncated)
        self.assertEqual(len(text), 220)

    def test_allowed_topic_overlap_requires_intersection(self):
        self.assertTrue(heuristics.allowed_topic_overlap("sprite motion blocks", ["sprite control", "events"]))
        self.assertFalse(heuristics.allowed_topic_overlap("database joins", ["scratch sprites", "motion blocks"]))

    def test_allowed_topic_overlap_accepts_broader_signed_scope_context(self):
        self.assertTrue(
            heuristics.allowed_topic_overlap(
                "How does the littlebits oscillator make noise?",
                ["choose an input", "control one output"],
                context="Inputs and Outputs with littleBits",
                topics=["Makes: A littleBits build that uses a student-chosen input to control light, sound, or motion."],
                reference_text="Pick one output that makes light, sound, or motion with littleBits.",
            )
        )

    def test_allowed_topic_overlap_keeps_generic_words_from_becoming_scope_match(self):
        self.assertFalse(
            heuristics.allowed_topic_overlap(
                "Can you help me understand this better today?",
                ["change one thing and retest", "record a short build video"],
            )
        )

    def test_is_context_dependent_follow_up_detects_short_replies(self):
        self.assertTrue(heuristics.is_context_dependent_follow_up("There isn't"))
        self.assertTrue(heuristics.is_context_dependent_follow_up("I don't know"))
        self.assertFalse(heuristics.is_context_dependent_follow_up("Can we talk about weather today instead?"))

    def test_build_instructions_mentions_follow_up_conversation(self):
        instructions = policy.build_instructions(
            "light",
            context="Inputs and outputs",
            topics=["littleBits"],
            scope_mode="soft",
        )
        lowered = instructions.lower()
        self.assertIn("ongoing tutoring conversation", lowered)
        self.assertIn("follow-up", lowered)
        self.assertIn("instead of restarting from scratch", lowered)
        self.assertIn("do not promise confidentiality", lowered)

    def test_safeguarding_disclosure_pauses_tutoring_without_collecting_pii(self):
        self.assertEqual(heuristics.safeguarding_risk("Someone is abusing me at home"), "disclosure")
        text = heuristics.build_safeguarding_response("disclosure").lower()
        self.assertIn("pausing tutoring", text)
        self.assertIn("trusted adult", text)
        self.assertIn("can't promise", text)
        self.assertIn("do not need to share names", text)

    def test_safeguarding_imminent_threat_directs_to_emergency_help(self):
        self.assertEqual(heuristics.safeguarding_risk("I am about to hurt myself right now"), "imminent")
        text = heuristics.build_safeguarding_response("imminent").lower()
        self.assertIn("emergency services now", text)

    def test_safeguarding_recognizes_common_direct_disclosures(self):
        cases = {
            "My dad hits me": "disclosure",
            "an adult touched me": "disclosure",
            "I do not feel safe at home": "disclosure",
            "I have a gun": "imminent",
            "someone raped me": "disclosure",
            "I want to kill myself": "disclosure",
            "I am going to hurt someone": "disclosure",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), expected)

    def test_safeguarding_recognizes_ordinary_first_person_disclosures_without_flagging_literary_quote(self):
        cases = {
            "I was punched by my stepdad": "disclosure",
            "I was forced to undress": "disclosure",
            "An adult makes me take my clothes off": "disclosure",
            "I do not want to be alive": "disclosure",
            "I have a knife in my backpack": "imminent",
            'In English class, the narrator says "I was punched by my stepdad" to show conflict.': "",
        }

        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), expected)

    def test_safeguarding_recognizes_audit_disclosures(self):
        cases = {
            "My dad punches me every night": "disclosure",
            "My teacher is touching me and I am scared": "disclosure",
            "I can't stay safe at home": "disclosure",
            "I have pills and plan to overdose tonight": "imminent",
            "Mi papá me pega en casa": "disclosure",
            "Mi maestro me está tocando": "disclosure",
            "Waxaan rabaa inaan is dilo": "disclosure",
        }

        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), expected)

    def test_safeguarding_recognizes_relationship_and_authority_perpetrators(self):
        cases = (
            "My uncle hits me",
            "My aunt hurt me",
            "My sibling beats me",
            "My teacher abuses me",
            "My coach hit me",
            "My babysitter hurts me",
            "My caregiver beats me",
            "An adult hit me",
            "My uncle touched me",
            "My aunt sexually assaulted me",
            "My sibling touched me",
            "My teacher touched me",
            "My coach sexually assaulted me",
            "My babysitter touched me",
            "My caregiver touched me",
            "An adult touched me",
        )
        for message in cases:
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), "disclosure")

    def test_safeguarding_ignores_obvious_game_violence(self):
        cases = (
            "How do I kill someone in my game?",
            "I have a gun in my game",
            "someone has a gun in my game",
        )
        for message in cases:
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), "")

    def test_game_context_does_not_hide_separate_real_world_danger(self):
        cases = (
            "I have a gun in my game, but someone has a gun at school",
            "I kill someone in my game and I am about to hurt someone right now",
        )
        for message in cases:
            with self.subTest(message=message):
                self.assertEqual(heuristics.safeguarding_risk(message), "imminent")

    def test_build_instructions_enforces_normalized_response_language(self):
        instructions = policy.build_instructions(
            "light",
            context="Inputs and outputs",
            topics=["littleBits"],
            scope_mode="soft",
            response_language_code="es-MX",
        )
        self.assertIn("Always respond in Spanish.", instructions)

    def test_build_instructions_supports_sgaw_karen_response_language(self):
        instructions = policy.build_instructions(
            "light",
            context="Inputs and outputs",
            topics=["littleBits"],
            scope_mode="soft",
            response_language_code="ksw-MM",
        )
        self.assertIn("Always respond in S'gaw Karen.", instructions)

    def test_build_piper_hardware_triage_text_includes_guided_steps(self):
        text = heuristics.build_piper_hardware_triage_text("StoryMode jump button is not working")
        lowered = text.lower()
        self.assertIn("which storymode mission + step", lowered)
        self.assertIn("do this one check now", lowered)
        self.assertIn("retest only that same input", lowered)

    def test_mouse_only_access_question_detection_and_guidance(self):
        self.assertTrue(heuristics.is_mouse_only_access_question("I only have a mouse right now, no keyboard. Can I still do this?"))
        text = heuristics.build_mouse_only_adaptation_text().lower()
        self.assertIn("yes, you can", text)
        self.assertIn("mouse", text)
        self.assertIn("storymode", text)
        self.assertIn("test again", text)

    def test_teamwork_decision_question_detection_and_guidance(self):
        self.assertTrue(heuristics.is_teamwork_decision_question("My partner and I disagree on whose code to keep."))
        text = heuristics.build_teamwork_decision_text().lower()
        self.assertIn("test", text)
        self.assertIn("together", text)
        self.assertIn("decide", text)

    def test_class_reentry_privacy_detection_and_guidance(self):
        self.assertTrue(
            heuristics.is_class_reentry_privacy_question(
                "I forgot my return code and name card. Can I get back into class without my full name?"
            )
        )
        text = heuristics.build_class_reentry_privacy_text().lower()
        self.assertIn("class code", text)
        self.assertIn("display name", text)
        self.assertIn("teacher", text)
        self.assertIn("piper", text)
        self.assertNotIn("full legal name", text)

    def test_publish_privacy_detection_and_guidance(self):
        self.assertTrue(heuristics.is_publish_privacy_question("Can I publish this without my full name shown?"))
        text = heuristics.build_publish_privacy_text().lower()
        self.assertIn("publish", text)
        self.assertIn("display name", text)
        self.assertIn("teacher", text)

    def test_score_condition_debug_detection_and_guidance(self):
        self.assertTrue(heuristics.is_score_condition_debug_question("Score goes up even when I hit the wrong object."))
        text = heuristics.build_score_condition_debug_text().lower()
        self.assertIn("if condition", text)
        self.assertIn("check", text)

    def test_wellbeing_reset_detection_and_guidance(self):
        self.assertTrue(heuristics.is_wellbeing_reset_question("Nothing works and I feel dumb. I want to quit."))
        text = heuristics.build_wellbeing_reset_text().lower()
        self.assertIn("not dumb", text)
        self.assertIn("small next step", text)

    def test_is_stem_technology_question_detects_tool_specific_prompt(self):
        self.assertTrue(
            heuristics.is_stem_technology_question(
                "Which Scratch block should I use to make this sprite loop?",
                context_value="Scratch game design",
                topics=["sprites", "loops"],
                reference_text="Technology-first troubleshooting for Scratch projects.",
            )
        )
        self.assertFalse(
            heuristics.is_stem_technology_question(
                "How should I reflect on what I learned today?",
                context_value="Class reflection",
                topics=["reflection"],
                reference_text="Use evidence from your project.",
            )
        )


class ReferenceEngineTests(SimpleTestCase):
    def test_build_reference_citations_prefers_stem_tech_chunk_for_tool_question(self):
        citations = reference.build_reference_citations(
            message="My Scratch sprite is not moving in a loop.",
            context="Scratch game design",
            topics=["sprites", "loops"],
            reference_chunks=(
                "Lesson summary Title Game design goals and class workflow.",
                "Technology-first troubleshooting Scratch sprite loop motion blocks and variables to check first.",
                "Submission and workflow Turn in one screenshot after class.",
            ),
            source_label="s05-scratch-motion-loops",
            max_items=2,
            prefer_stem_technology=True,
        )
        self.assertEqual(len(citations), 2)
        self.assertIn("Technology-first troubleshooting", citations[0]["text"])

    def test_build_reference_citations_prefers_stem_tech_fallback_when_no_overlap(self):
        citations = reference.build_reference_citations(
            message="I need help with the setup.",
            context="",
            topics=[],
            reference_chunks=(
                "Lesson summary Title Game design goals and class workflow.",
                "STEM technologies in scope Piper computer kit Scratch web app breadboard and button inputs.",
                "Submission and workflow Turn in one screenshot after class.",
            ),
            source_label="piper_scratch",
            max_items=1,
            prefer_stem_technology=True,
        )
        self.assertEqual(len(citations), 1)
        self.assertIn("STEM technologies in scope", citations[0]["text"])


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


class ConfigSourceEngineTests(SimpleTestCase):
    def tearDown(self):
        config_source.clear_helper_config_cache()
        super().tearDown()

    def test_helper_getenv_reads_yaml_when_env_missing(self):
        with TemporaryDirectory() as temp_dir:
            cfg_path = Path(temp_dir) / "helper.yaml"
            cfg_path.write_text(
                (
                    "policy:\n"
                    "  strictness: strict\n"
                    "rate_limits:\n"
                    "  actor_per_minute: 17\n"
                    "references:\n"
                    "  map:\n"
                    "    piper_scratch: piper_scratch.md\n"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"HELPER_CONFIG_FILE": str(cfg_path)},
                clear=True,
            ):
                config_source.clear_helper_config_cache()
                self.assertEqual(config_source.helper_getenv("HELPER_STRICTNESS", "light"), "strict")
                self.assertEqual(config_source.helper_getenv("HELPER_RATE_LIMIT_PER_MINUTE", "30"), "17")
                self.assertEqual(
                    config_source.helper_getenv("HELPER_REFERENCE_MAP", ""),
                    '{"piper_scratch":"piper_scratch.md"}',
                )

    def test_helper_getenv_prefers_explicit_env_over_yaml(self):
        with TemporaryDirectory() as temp_dir:
            cfg_path = Path(temp_dir) / "helper.yaml"
            cfg_path.write_text("policy:\n  strictness: strict\n", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {
                    "HELPER_CONFIG_FILE": str(cfg_path),
                    "HELPER_STRICTNESS": "light",
                },
                clear=True,
            ):
                config_source.clear_helper_config_cache()
                self.assertEqual(config_source.helper_getenv("HELPER_STRICTNESS", "strict"), "light")


class ExecutionConfigEngineTests(SimpleTestCase):
    def test_resolve_execution_config_applies_bounds_and_defaults(self):
        env_values = {
            "HELPER_LLM_BACKEND": "mock",
            "HELPER_REFERENCE_DIR": " /tmp/ref ",
            "HELPER_REFERENCE_MAP": '{"r":"r.md"}',
            "HELPER_REFERENCE_FILE": " /tmp/ref/r.md ",
            "HELPER_RAG_EMBED_BASE_URL": " http://ollama:11434 ",
            "HELPER_RAG_EMBED_MODEL": "nomic-embed-text",
        }

        def _env_int(name: str, default: int) -> int:
            values = {
                "HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS": 10,  # clamps up to 60
                "HELPER_CONVERSATION_MAX_MESSAGES": -5,  # clamps up to 0
                "HELPER_CONVERSATION_TTL_SECONDS": 0,  # clamps up to 1
                "HELPER_CONVERSATION_TURN_MAX_CHARS": 20,  # clamps up to 80
                "HELPER_CONVERSATION_HISTORY_MAX_CHARS": 22,  # clamps up to 300
                "HELPER_CONVERSATION_SUMMARY_MAX_CHARS": 11,  # clamps up to 200
                "HELPER_FOLLOW_UP_SUGGESTIONS_MAX": 0,  # clamps up to 1
                "HELPER_REFERENCE_MAX_CITATIONS": 0,  # clamps up to 1
                "HELPER_RAG_EMBED_TIMEOUT_SECONDS": 0,  # clamps up to 1
                "HELPER_RAG_EMBED_DIMENSIONS": 0,  # clamps up to 1
                "HELPER_MAX_CONCURRENCY": 7,
                "HELPER_QUEUE_SLOT_TTL_SECONDS": 121,
            }
            return values.get(name, default)

        def _env_float(name: str, default: float) -> float:
            values = {
                "HELPER_QUEUE_MAX_WAIT_SECONDS": 9.5,
                "HELPER_QUEUE_POLL_SECONDS": 0.3,
                "HELPER_RAG_MAX_COSINE_DISTANCE": 0.35,
            }
            return values.get(name, default)

        def _env_bool(name: str, default: bool) -> bool:
            values = {
                "HELPER_CONVERSATION_ENABLED": False,
                "HELPER_PIPER_HARDWARE_TRIAGE_ENABLED": False,
                "HELPER_RAG_ENABLED": True,
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
        self.assertEqual(cfg.conversation_ttl_seconds, 1)
        self.assertEqual(cfg.conversation_turn_max_chars, 80)
        self.assertEqual(cfg.conversation_history_max_chars, 300)
        self.assertEqual(cfg.conversation_summary_max_chars, 200)
        self.assertEqual(cfg.follow_up_suggestions_max, 1)
        self.assertEqual(cfg.reference_dir, "/tmp/ref")
        self.assertEqual(cfg.reference_map_raw, '{"r":"r.md"}')
        self.assertEqual(cfg.default_reference_file, "/tmp/ref/r.md")
        self.assertEqual(cfg.reference_max_citations, 1)
        self.assertTrue(cfg.rag_enabled)
        self.assertEqual(cfg.rag_embedding_base_url, "http://ollama:11434")
        self.assertEqual(cfg.rag_embedding_model, "nomic-embed-text")
        self.assertEqual(cfg.rag_embedding_timeout_seconds, 1)
        self.assertEqual(cfg.rag_embedding_dimensions, 1)
        self.assertEqual(cfg.rag_max_cosine_distance, 0.35)
        self.assertEqual(cfg.text_language_keywords, ["scratch", "sprites"])
        self.assertFalse(cfg.piper_hardware_triage_enabled)
        self.assertEqual(cfg.queue_max_concurrency, 7)
        self.assertEqual(cfg.queue_max_wait_seconds, 9.5)
        self.assertEqual(cfg.queue_poll_seconds, 0.3)
        self.assertEqual(cfg.queue_slot_ttl_seconds, 121)

    def test_resolve_execution_config_uses_conversation_friendly_defaults(self):
        cfg = execution_config.resolve_execution_config(
            env_int=lambda _name, default: default,
            env_float=lambda _name, default: default,
            env_bool=lambda _name, default: default,
            parse_csv_list=lambda _raw: [],
            default_text_language_keywords=["scratch"],
            getenv=lambda _key, default="": default,
        )
        self.assertEqual(cfg.conversation_max_messages, 12)
        self.assertEqual(cfg.conversation_ttl_seconds, 7200)
        self.assertEqual(cfg.conversation_turn_max_chars, 1000)
        self.assertEqual(cfg.conversation_history_max_chars, 4000)
        self.assertEqual(cfg.conversation_summary_max_chars, 1400)

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
        self.assertFalse(cfg.rag_enabled)


class RAGEngineTests(SimpleTestCase):
    def test_build_reference_inventory_rejects_outside_paths(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "safe.md").write_text("Safe curriculum", encoding="utf-8")
            outside = root.parent / "outside.md"
            outside.write_text("Outside", encoding="utf-8")
            try:
                inventory = rag.build_reference_inventory(
                    str(root),
                    '{"safe":"safe.md","escape":"../outside.md"}',
                )
            finally:
                outside.unlink(missing_ok=True)

        self.assertIn("safe", inventory)
        self.assertNotIn("escape", inventory)

    def test_retrieve_curriculum_citations_returns_empty_on_non_postgres(self):
        sqlite_connection = SimpleNamespace(vendor="sqlite")
        citations = rag.retrieve_curriculum_citations(
            connection=sqlite_connection,
            logger=MagicMock(),
            query_text="How do I debug a sprite?",
            reference_key="piper_scratch",
            max_items=3,
            max_cosine_distance=0.4,
            embedding_dimensions=768,
            embed_text_fn=lambda _text: [0.1, 0.2],
        )
        self.assertEqual(citations, [])

    def test_retrieve_curriculum_citations_reranks_toward_stem_tech_when_distances_are_close(self):
        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, _query, _params):
                return None

            def fetchall(self):
                return [
                    ("Submission workflow upload one screenshot before the bell.", "piper_scratch", 0.100),
                    (
                        "Technology-first troubleshooting Scratch sprite loop blocks and button wiring to check first.",
                        "piper_scratch",
                        0.112,
                    ),
                ]

        connection = SimpleNamespace(vendor="postgresql", cursor=lambda: FakeCursor())
        with patch("tutor.engine.rag._table_exists", return_value=True):
            citations = rag.retrieve_curriculum_citations(
                connection=connection,
                logger=MagicMock(),
                query_text="Which Scratch block should I use when my sprite loop is broken?",
                reference_key="piper_scratch",
                max_items=2,
                max_cosine_distance=0.4,
                embedding_dimensions=2,
                embed_text_fn=lambda _text: [0.1, 0.2],
                prefer_stem_technology=True,
            )
        self.assertEqual(len(citations), 2)
        self.assertIn("Technology-first troubleshooting", citations[0]["text"])

    def test_relation_identifier_parts_support_schema_qualified_table_name(self):
        parts = rag._relation_identifier_parts("public.tutor_curriculum_rag_chunks")
        self.assertEqual(parts, ("public", "tutor_curriculum_rag_chunks"))

    def test_relation_identifier_parts_rejects_invalid_table_names(self):
        for raw in ("", "public..table", "public.table;drop", "public.\"Table\"", "a.b.c"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    rag._relation_identifier_parts(raw)
    def test_ensure_pgvector_schema_rejects_invalid_table_name(self):
        connection = SimpleNamespace(
            vendor="postgresql",
            ops=SimpleNamespace(quote_name=lambda name: f'"{name}"'),
            cursor=lambda: (_ for _ in ()).throw(AssertionError("cursor should not be called")),
        )
        with self.assertRaisesMessage(ValueError, "invalid_rag_table_name"):
            rag.ensure_pgvector_schema(
                connection=connection,
                logger=MagicMock(),
                embedding_dimensions=768,
                table_name="rag_chunks; DROP TABLE users; --",
            )

    def test_clear_reference_rows_rejects_invalid_table_name(self):
        connection = SimpleNamespace(
            vendor="postgresql",
            ops=SimpleNamespace(quote_name=lambda name: f'"{name}"'),
            cursor=lambda: (_ for _ in ()).throw(AssertionError("cursor should not be called")),
        )
        with self.assertRaisesMessage(ValueError, "invalid_rag_table_name"):
            rag.clear_reference_rows(
                connection=connection,
                reference_key="piper_scratch",
                table_name="rag_chunks; DROP TABLE users; --",
            )

    def test_upsert_reference_embeddings_rejects_invalid_table_name(self):
        connection = SimpleNamespace(
            vendor="postgresql",
            ops=SimpleNamespace(quote_name=lambda name: f'"{name}"'),
            cursor=lambda: (_ for _ in ()).throw(AssertionError("cursor should not be called")),
        )
        with self.assertRaisesMessage(ValueError, "invalid_rag_table_name"):
            rag.upsert_reference_embeddings(
                connection=connection,
                reference_key="piper_scratch",
                source_label="Piper Scratch",
                chunks=("chunk 1",),
                embedding_dimensions=2,
                embed_text_fn=lambda _text: [0.1, 0.2],
                logger=MagicMock(),
                table_name="rag_chunks; DROP TABLE users; --",
            )

    def test_retrieve_curriculum_citations_rejects_invalid_table_name(self):
        connection = SimpleNamespace(
            vendor="postgresql",
            ops=SimpleNamespace(quote_name=lambda name: f'"{name}"'),
            cursor=lambda: (_ for _ in ()).throw(AssertionError("cursor should not be called")),
        )
        with self.assertRaisesMessage(ValueError, "invalid_rag_table_name"):
            rag.retrieve_curriculum_citations(
                connection=connection,
                logger=MagicMock(),
                query_text="How do I debug a sprite?",
                reference_key="piper_scratch",
                max_items=3,
                max_cosine_distance=0.4,
                embedding_dimensions=768,
                embed_text_fn=lambda _text: [0.1] * 768,
                table_name="rag_chunks; DROP TABLE users; --",
            )


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
