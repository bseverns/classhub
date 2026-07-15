import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from tutor.engine import memory as engine_memory


class _ScriptedCacheBackend:
    def __init__(self):
        self.values = {}
        self.timeouts = {}
        self.get_error_keys = set()
        self.delete_error_keys = set()
        self.delete_false_keys = set()
        self.set_error_keys = set()
        self.deleted_keys = []
        self.set_values = []
        self.after_set = None
        self.after_delete = None

    def get(self, key):
        if key in self.get_error_keys:
            raise RuntimeError("cache read failed")
        return self.values.get(key)

    def delete(self, key):
        self.deleted_keys.append(key)
        if key in self.delete_error_keys:
            raise RuntimeError("cache delete failed")
        if key in self.delete_false_keys:
            result = False
        else:
            result = key in self.values
            self.values.pop(key, None)
        if self.after_delete is not None:
            self.after_delete(key)
        return result

    def set(self, key, value, timeout=None):
        if key in self.set_error_keys:
            raise RuntimeError("cache write failed")
        self.set_values.append((key, value, timeout))
        self.values[key] = value
        self.timeouts[key] = timeout
        if self.after_set is not None:
            self.after_set(key)
        return True


class HelperInternalResetTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(HELPER_INTERNAL_API_TOKEN="")
    def test_internal_reset_requires_configured_token(self):
        resp = self.client.post(
            "/helper/internal/reset-class-conversations",
            data=json.dumps({"class_id": 5}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-token",
        )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "internal_token_not_configured")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_internal_reset_rejects_invalid_token(self):
        with self.assertLogs("tutor.internal_audit", level="WARNING") as captured:
            resp = self.client.post(
                "/helper/internal/reset-class-conversations",
                data=json.dumps({"class_id": 5}),
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer wrong-token",
            )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")
        self.assertIn("internal_reset_unauthorized", captured.records[0].getMessage())

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch.dict("os.environ", {"HELPER_INTERNAL_ALLOWED_CIDRS": "10.0.0.0/8"}, clear=False)
    def test_internal_reset_rejects_non_internal_ip(self):
        resp = self.client.post(
            "/helper/internal/reset-class-conversations",
            data=json.dumps({"class_id": 5}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
            REMOTE_ADDR="198.51.100.8",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "forbidden")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_internal_reset_clears_class_conversation_keys(self):
        actor_key = "student:55:9001"
        key = engine_memory.conversation_cache_key(
            actor_key=actor_key,
            scope_fp="noscope",
            conversation_id="class-reset-test",
        )
        engine_memory.save_state(
            cache_backend=cache,
            key=key,
            turns=[{"role": "student", "content": "Need help", "intent": "debug"}],
            summary="",
            ttl_seconds=300,
            actor_key=actor_key,
        )
        self.assertIsNotNone(cache.get(key))

        with self.assertLogs("tutor.internal_audit", level="INFO") as captured:
            resp = self.client.post(
                "/helper/internal/reset-class-conversations",
                data=json.dumps({"class_id": 55}),
                content_type="application/json",
                HTTP_AUTHORIZATION="Bearer token-123",
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("class_id"), 55)
        self.assertGreaterEqual(int(body.get("deleted_conversations") or 0), 1)
        self.assertIsNone(cache.get(key))
        self.assertIn("internal_reset_completed", captured.records[0].getMessage())
        self.assertIn('"class_id": 55', captured.records[0].getMessage())

        # Class reset can leave a stale actor index; actor clearing must confirm
        # the conversation is already absent and remove that index successfully.
        actor_result = engine_memory.clear_actor_conversations(
            cache_backend=cache,
            actor_key=actor_key,
            retry_ttl_seconds=300,
        )
        self.assertTrue(actor_result.ok)
        self.assertEqual(actor_result.deleted_conversations, 0)
        self.assertIsNone(cache.get(engine_memory.conversation_actor_index_key(actor_key=actor_key)))

    def test_class_reset_preserves_index_when_payload_delete_is_unconfirmed(self):
        class_id = 55
        class_index_key = engine_memory.conversation_class_index_key(class_id=class_id)
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"

        for failure_mode in ("false", "raise"):
            with self.subTest(failure_mode=failure_mode):
                backend = _ScriptedCacheBackend()
                backend.values[class_index_key] = [conversation_key]
                backend.values[conversation_key] = {"turns": []}
                if failure_mode == "false":
                    backend.delete_false_keys.add(conversation_key)
                else:
                    backend.delete_error_keys.add(conversation_key)

                result = engine_memory.clear_class_conversations(
                    cache_backend=backend,
                    class_id=class_id,
                )

                self.assertFalse(result.ok)
                self.assertEqual(result.error_code, "conversation_delete_failed")
                self.assertEqual(backend.get(class_index_key), [conversation_key])

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch("tutor.views_reset.engine_memory.clear_class_conversations")
    def test_internal_class_reset_surfaces_unconfirmed_delete(self, clear_mock):
        clear_mock.return_value = engine_memory.ConversationClearResult(
            ok=False,
            deleted_conversations=1,
            error_code="conversation_delete_failed",
        )

        resp = self.client.post(
            "/helper/internal/reset-class-conversations",
            data=json.dumps({"class_id": 55}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
        )

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["error"], "class_reset_unconfirmed")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_internal_actor_clear_uses_actor_index_only(self):
        target_key = engine_memory.conversation_cache_key(
            actor_key="student:55:9001", scope_fp="noscope", conversation_id="target"
        )
        other_key = engine_memory.conversation_cache_key(
            actor_key="student:55:9002", scope_fp="noscope", conversation_id="other"
        )
        for key, actor in ((target_key, "student:55:9001"), (other_key, "student:55:9002")):
            engine_memory.save_state(
                cache_backend=cache,
                key=key,
                turns=[{"role": "student", "content": "Need help"}],
                summary="",
                ttl_seconds=300,
                actor_key=actor,
            )
        resp = self.client.post(
            "/helper/internal/clear-actor-conversations",
            data=json.dumps({"class_id": 55, "student_id": 9001}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["deleted_conversations"], 1)
        self.assertIsNone(cache.get(target_key))
        self.assertIsNotNone(cache.get(other_key))

    def test_actor_clear_reports_index_get_exception(self):
        actor_key = "student:55:9001"
        backend = _ScriptedCacheBackend()
        backend.get_error_keys.add(engine_memory.conversation_actor_index_key(actor_key=actor_key))
        result = engine_memory.clear_actor_conversations(
            cache_backend=backend,
            actor_key=actor_key,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "actor_index_read_failed")
        self.assertEqual(result.deleted_conversations, 0)

    def test_actor_clear_keeps_index_when_conversation_delete_raises(self):
        actor_key = "student:55:9001"
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.values[index_key] = [conversation_key]
        backend.values[conversation_key] = {"turns": []}
        backend.delete_error_keys.add(conversation_key)
        result = engine_memory.clear_actor_conversations(
            cache_backend=backend,
            actor_key=actor_key,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.deleted_conversations, 0)
        self.assertIn(conversation_key, backend.deleted_keys)
        self.assertEqual(backend.values[index_key], [conversation_key])

    def test_actor_clear_treats_stale_missing_conversation_as_cleared(self):
        actor_key = "student:55:9001"
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.values[index_key] = [conversation_key]
        result = engine_memory.clear_actor_conversations(
            cache_backend=backend,
            actor_key=actor_key,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.deleted_conversations, 0)
        self.assertIsNone(backend.get(index_key))
        self.assertIsNotNone(
            backend.get(engine_memory.conversation_actor_clearing_key(actor_key=actor_key))
        )

    def test_actor_clear_does_not_accept_false_delete_when_absence_read_fails(self):
        actor_key = "student:55:9001"
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.values[index_key] = [conversation_key]
        backend.values[conversation_key] = {"turns": []}
        backend.delete_false_keys.add(conversation_key)
        backend.get_error_keys.add(conversation_key)

        result = engine_memory.clear_actor_conversations(cache_backend=backend, actor_key=actor_key)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "conversation_delete_failed")
        self.assertEqual(backend.values[index_key], [conversation_key])

    def test_actor_clear_reports_marker_set_exception_without_touching_index(self):
        actor_key = "student:55:9001"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        marker_key = engine_memory.conversation_actor_clearing_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.values[index_key] = ["conversation-key"]
        backend.set_error_keys.add(marker_key)

        result = engine_memory.clear_actor_conversations(cache_backend=backend, actor_key=actor_key)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "clearing_marker_set_failed")
        self.assertEqual(backend.values[index_key], ["conversation-key"])
        self.assertEqual(backend.deleted_keys, [])

    def test_actor_clear_reports_marker_confirmation_get_exception(self):
        actor_key = "student:55:9001"
        marker_key = engine_memory.conversation_actor_clearing_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.get_error_keys.add(marker_key)

        result = engine_memory.clear_actor_conversations(cache_backend=backend, actor_key=actor_key)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "clearing_marker_read_failed")

    def test_save_during_actor_clear_cleans_state_after_clear_succeeds(self):
        actor_key = "student:55:9001"
        conversation_key = engine_memory.conversation_cache_key(
            actor_key=actor_key, scope_fp="noscope", conversation_id="racing-save"
        )
        backend = _ScriptedCacheBackend()
        clear_results = []

        def clear_after_conversation_write(key):
            if key != conversation_key:
                return
            backend.after_set = None
            clear_results.append(
                engine_memory.clear_actor_conversations(
                    cache_backend=backend,
                    actor_key=actor_key,
                    retry_ttl_seconds=900,
                )
            )

        backend.after_set = clear_after_conversation_write
        engine_memory.save_state(
            cache_backend=backend,
            key=conversation_key,
            turns=[{"role": "student", "content": "Need help"}],
            summary="",
            ttl_seconds=300,
            actor_key=actor_key,
        )

        self.assertEqual(len(clear_results), 1)
        self.assertTrue(clear_results[0].ok)
        self.assertIsNone(backend.get(conversation_key))
        self.assertEqual(
            backend.timeouts[engine_memory.conversation_actor_clearing_key(actor_key=actor_key)],
            900,
        )

    def test_save_is_suppressed_while_actor_marker_exists(self):
        actor_key = "student:55:9001"
        conversation_key = "conversation-key"
        marker_key = engine_memory.conversation_actor_clearing_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.values[marker_key] = "active-clear"

        engine_memory.save_state(
            cache_backend=backend,
            key=conversation_key,
            turns=[{"role": "student", "content": "private prompt"}],
            summary="",
            ttl_seconds=300,
            actor_key=actor_key,
        )

        self.assertIsNone(backend.get(conversation_key))
        self.assertNotIn(engine_memory.conversation_actor_index_key(actor_key=actor_key), backend.values)

    def test_save_cleans_conversation_when_actor_index_set_raises(self):
        actor_key = "student:55:9001"
        conversation_key = "conversation-key"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        backend = _ScriptedCacheBackend()
        backend.set_error_keys.add(index_key)

        engine_memory.save_state(
            cache_backend=backend,
            key=conversation_key,
            turns=[{"role": "student", "content": "private prompt"}],
            summary="",
            ttl_seconds=300,
            actor_key=actor_key,
        )

        self.assertIsNone(backend.get(conversation_key))

    def test_actor_clear_rechecks_and_removes_late_index_registration(self):
        actor_key = "student:55:9001"
        index_key = engine_memory.conversation_actor_index_key(actor_key=actor_key)
        first_key = "conversation-one"
        late_key = "conversation-two"
        backend = _ScriptedCacheBackend()
        backend.values[index_key] = [first_key]
        backend.values[first_key] = {"turns": []}

        def register_late_key(deleted_key):
            if deleted_key != index_key:
                return
            backend.after_delete = None
            backend.values[late_key] = {"turns": []}
            backend.values[index_key] = [late_key]

        backend.after_delete = register_late_key
        result = engine_memory.clear_actor_conversations(cache_backend=backend, actor_key=actor_key)

        self.assertTrue(result.ok)
        self.assertEqual(result.deleted_conversations, 2)
        self.assertIsNone(backend.get(first_key))
        self.assertIsNone(backend.get(late_key))
        self.assertIsNone(backend.get(index_key))

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch("tutor.views_reset.engine_memory.clear_actor_conversations")
    def test_internal_actor_clear_propagates_cache_failure(self, clear_mock):
        clear_mock.return_value = engine_memory.ConversationClearResult(
            ok=False,
            error_code="conversation_delete_failed",
        )
        resp = self.client.post(
            "/helper/internal/clear-actor-conversations",
            data=json.dumps({"class_id": 55, "student_id": 9001}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
        )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["error"], "actor_clear_unconfirmed")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch.dict(
        "os.environ",
        {
            "HELPER_CONVERSATION_TTL_SECONDS": "300",
            "HELPER_SCOPE_TOKEN_MAX_AGE_SECONDS": "900",
        },
        clear=False,
    )
    @patch("tutor.views_reset.engine_memory.clear_actor_conversations")
    def test_internal_actor_clear_uses_longer_scope_ttl_and_returns_success(self, clear_mock):
        clear_mock.return_value = engine_memory.ConversationClearResult(
            ok=True,
            deleted_conversations=2,
        )

        resp = self.client.post(
            "/helper/internal/clear-actor-conversations",
            data=json.dumps({"class_id": 55, "student_id": 9001}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-123",
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["class_id"], 55)
        self.assertEqual(body["student_id"], 9001)
        self.assertEqual(body["deleted_conversations"], 2)
        self.assertTrue(body["request_id"])
        self.assertEqual(clear_mock.call_args.kwargs["retry_ttl_seconds"], 900)

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    @patch.dict(
        "os.environ",
        {
            "HELPER_CLASS_RESET_ARCHIVE_ENABLED": "1",
            "HELPER_CLASS_RESET_ARCHIVE_MAX_MESSAGES": "120",
        },
        clear=False,
    )
    def test_internal_reset_exports_archive_before_clear(self):
        key = engine_memory.conversation_cache_key(
            actor_key="student:66:9001",
            scope_fp="noscope",
            conversation_id="archive-reset-test",
        )
        engine_memory.save_state(
            cache_backend=cache,
            key=key,
            turns=[{"role": "student", "content": "Need help", "intent": "debug"}],
            summary="",
            ttl_seconds=300,
            actor_key="student:66:9001",
        )
        self.assertIsNotNone(cache.get(key))

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {"HELPER_CLASS_RESET_ARCHIVE_DIR": temp_dir}, clear=False):
                resp = self.client.post(
                    "/helper/internal/reset-class-conversations",
                    data=json.dumps({"class_id": 66, "export_before_reset": True}),
                    content_type="application/json",
                    HTTP_AUTHORIZATION="Bearer token-123",
                )

                self.assertEqual(resp.status_code, 200)
                body = resp.json()
                self.assertTrue(body.get("ok"))
                self.assertEqual(body.get("class_id"), 66)
                self.assertGreaterEqual(int(body.get("deleted_conversations") or 0), 1)
                self.assertGreaterEqual(int(body.get("archived_conversations") or 0), 1)
                archive_path = str(body.get("archive_path") or "")
                self.assertTrue(archive_path)
                self.assertTrue(os.path.exists(archive_path))
                self.assertTrue(Path(archive_path).resolve().is_relative_to(Path(temp_dir).resolve()))
        self.assertIsNone(cache.get(key))
