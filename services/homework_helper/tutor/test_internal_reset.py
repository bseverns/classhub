import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from tutor.engine import memory as engine_memory

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
        resp = self.client.post(
            "/helper/internal/reset-class-conversations",
            data=json.dumps({"class_id": 5}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer wrong-token",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")

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
