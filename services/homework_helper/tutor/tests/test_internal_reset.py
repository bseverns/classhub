import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from tutor.engine import memory as engine_memory


class _FailingCacheBackend:
    def __init__(self, *, indexed=None, get_error=False, delete_result=True, delete_error=False):
        self.indexed = indexed
        self.get_error = get_error
        self.delete_result = delete_result
        self.delete_error = delete_error
        self.deleted_keys = []
        self.set_values = []

    def get(self, _key):
        if self.get_error:
            raise RuntimeError("cache read failed")
        return self.indexed

    def delete(self, key):
        self.deleted_keys.append(key)
        if self.delete_error:
            raise RuntimeError("cache delete failed")
        return self.delete_result

    def set(self, key, value, timeout=None):
        self.set_values.append((key, value, timeout))
        self.indexed = value

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
        key = engine_memory.conversation_cache_key(
            actor_key="student:55:9001",
            scope_fp="noscope",
            conversation_id="class-reset-test",
        )
        engine_memory.save_state(
            cache_backend=cache,
            key=key,
            turns=[{"role": "student", "content": "Need help", "intent": "debug"}],
            summary="",
            ttl_seconds=300,
            actor_key="student:55:9001",
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
        result = engine_memory.clear_actor_conversations(
            cache_backend=_FailingCacheBackend(get_error=True),
            actor_key="student:55:9001",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "actor_index_read_failed")
        self.assertEqual(result.deleted_conversations, 0)

    def test_actor_clear_keeps_index_when_conversation_delete_raises(self):
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"
        backend = _FailingCacheBackend(indexed=[conversation_key], delete_error=True)
        result = engine_memory.clear_actor_conversations(
            cache_backend=backend,
            actor_key="student:55:9001",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.deleted_conversations, 0)
        self.assertEqual(backend.deleted_keys, [conversation_key])
        self.assertEqual(backend.indexed, [conversation_key])

    def test_actor_clear_does_not_count_false_delete_or_remove_index(self):
        conversation_key = "helper:conversation:student:55:9001:noscope:abc"
        backend = _FailingCacheBackend(indexed=[conversation_key], delete_result=False)
        result = engine_memory.clear_actor_conversations(
            cache_backend=backend,
            actor_key="student:55:9001",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.deleted_conversations, 0)
        self.assertEqual(backend.deleted_keys, [conversation_key])
        self.assertEqual(backend.indexed, [conversation_key])

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
