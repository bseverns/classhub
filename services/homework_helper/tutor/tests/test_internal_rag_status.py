import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings


class HelperInternalRagStatusTests(TestCase):
    @override_settings(HELPER_INTERNAL_API_TOKEN="")
    def test_internal_rag_status_requires_configured_token(self):
        resp = self.client.get(
            "/helper/internal/rag-status",
            HTTP_AUTHORIZATION="Bearer test-token",
        )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "internal_token_not_configured")

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_internal_rag_status_rejects_invalid_token(self):
        with self.assertLogs("tutor.internal_audit", level="WARNING") as captured:
            resp = self.client.get(
                "/helper/internal/rag-status",
                HTTP_AUTHORIZATION="Bearer wrong-token",
            )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json().get("error"), "unauthorized")
        self.assertIn("internal_rag_status_unauthorized", captured.records[0].getMessage())

    @override_settings(HELPER_INTERNAL_API_TOKEN="token-123")
    def test_internal_rag_status_returns_curriculum_only_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "piper_scratch.md").write_text("# Piper\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "HELPER_RAG_ENABLED": "1",
                    "HELPER_REFERENCE_DIR": temp_dir,
                },
                clear=False,
            ):
                with self.assertLogs("tutor.internal_audit", level="INFO") as captured:
                    resp = self.client.get(
                        "/helper/internal/rag-status",
                        HTTP_AUTHORIZATION="Bearer token-123",
                    )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("rag_enabled"))
        self.assertTrue(body.get("student_data_excluded_from_index"))
        self.assertEqual(body.get("configured_reference_keys"), ["piper_scratch"])
        self.assertIsInstance(body.get("reference_sources"), list)
        self.assertIn("internal_rag_status_read", captured.records[0].getMessage())
        self.assertIn('"reference_source_count": 0', captured.records[0].getMessage())
