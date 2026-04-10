from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "operator_preflight.py"


def run_preflight(env_text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / ".env"
        env_path.write_text(textwrap.dedent(env_text).strip() + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--env-file", str(env_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


class OperatorPreflightTests(unittest.TestCase):
    def test_local_mode_valid_contract_passes(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=1
            LLM_BACKEND=ollama
            LLM_BASE_URL=http://ollama:11434
            LLM_MODEL=llama3.2:1b
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[operator-preflight] OK", result.stdout)

    def test_asset_mode_requires_asset_base_url(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain.assets
            DOMAIN=lms.creatempls.org
            ASSET_DOMAIN=assets.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org,assets.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=1
            LLM_BACKEND=ollama
            LLM_BASE_URL=http://ollama:11434
            LLM_MODEL=llama3.2:1b
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("missing_asset_base_url", result.stdout)

    def test_remote_compute_mode_requires_remote_target_contract(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL=http://helper_web:8000/helper/internal/remote-compute-status
            HELPER_INTERNAL_REMOTE_COMPUTE_CONTROL_URL=http://helper_web:8000/helper/internal/remote-compute-control
            HELPER_INTERNAL_API_TOKEN=test-token
            LLM_ENABLED=1
            LLM_BACKEND=ollama
            LLM_BASE_URL=http://ollama:11434
            LLM_MODEL=llama3.2:1b
            CLASSHUB_REMOTE_HELPER_COMPUTE_ENABLED=1
            CLASSHUB_REMOTE_HELPER_COMPUTE_ACKNOWLEDGED=1
            HELPER_REMOTE_COMPUTE_ACTIVATE_URL=https://ops.creatempls.org/helper-remote/activate
            HELPER_REMOTE_COMPUTE_DEACTIVATE_URL=https://ops.creatempls.org/helper-remote/deactivate
            HELPER_REMOTE_COMPUTE_HEALTHCHECK_URL=https://ops.creatempls.org/helper-remote/health
            HELPER_REMOTE_COMPUTE_CONTROL_API_KEY=bridge-token
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("missing_remote_llm_base_url", result.stdout)


if __name__ == "__main__":
    unittest.main()
