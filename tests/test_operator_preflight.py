from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "operator_preflight.py"
QUICKSTART_PATH = REPO_ROOT / "scripts" / "quickstart_stack.sh"


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
    def test_public_domain_hostname_validation(self):
        for hostname in ("school.example.org", "lms-2.district.edu"):
            with self.subTest(hostname=hostname):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH), "--validate-public-hostname", hostname],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        for hostname in (
            "localhost",
            "203.0.113.10",
            "foo-.example",
            "-foo.example",
            "foo..example",
            "internal-only",
        ):
            with self.subTest(hostname=hostname):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT_PATH), "--validate-public-hostname", hostname],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_quickstart_validates_explicit_domain_before_creating_env(self):
        source = QUICKSTART_PATH.read_text(encoding="utf-8")
        early_validation = source.index('validate_domain_value "${DOMAIN_NAME}"')
        env_creation = source.index("prepare_env_file", source.index("main()"))
        self.assertLess(early_validation, env_creation)

    def test_shipped_profiles_require_return_code_for_cross_device_rejoin(self):
        settings_source = (REPO_ROOT / "services/classhub/config/settings.py").read_text(encoding="utf-8")
        self.assertIn("_default_require_return_code_for_rejoin = True", settings_source)

        for relative_path in (
            "compose/.env.example",
            "compose/.env.example.local",
            "compose/.env.example.domain",
        ):
            source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1", source, relative_path)

    def test_guided_quickstart_provisions_real_admin_and_otp_credentials(self) -> None:
        source = QUICKSTART_PATH.read_text(encoding="utf-8")

        self.assertIn('is_placeholder_value "${ADMIN_PASSWORD}"', source)
        self.assertIn("bootstrap_admin_otp", source)
        self.assertIn("--if-missing", source)
        password_output = source.index('echo "Generated admin password (store now): ${ADMIN_PASSWORD}"')
        otp_provisioning = source.index('log "provisioning admin authenticator"')
        self.assertLess(password_output, otp_provisioning)

    def test_guided_domain_mode_sets_django_origin_contract(self) -> None:
        source = QUICKSTART_PATH.read_text(encoding="utf-8")

        self.assertIn('--domain <name>', source)
        self.assertIn('env_set "DJANGO_ALLOWED_HOSTS" "${domain_value}"', source)
        self.assertIn('env_set "CSRF_TRUSTED_ORIGINS" "https://${domain_value}"', source)
        self.assertIn('operator_preflight.py" --env-file "${ENV_FILE}"', source)

    def test_domain_profile_closes_student_token_and_helper_identity_boundaries(self) -> None:
        domain_source = (REPO_ROOT / "compose/.env.example.domain").read_text(encoding="utf-8")
        validator_source = (REPO_ROOT / "scripts/validate_env_secrets.sh").read_text(encoding="utf-8")
        quickstart_source = QUICKSTART_PATH.read_text(encoding="utf-8")

        self.assertIn("CLASSHUB_API_TOKEN_MAX_AGE_SECONDS=86400", domain_source)
        self.assertIn("CLASSHUB_API_TOKEN_ALLOW_INDEFINITE=0", domain_source)
        self.assertIn("HELPER_REQUIRE_CLASSHUB_TABLE=1", domain_source)
        self.assertIn(
            'require_distinct_values "DJANGO_SECRET_KEY" "CLASSHUB_API_TOKEN_SIGNING_KEY"',
            validator_source,
        )
        self.assertIn(
            'fail "HELPER_REQUIRE_CLASSHUB_TABLE must be 1 in domain mode"',
            validator_source,
        )
        self.assertIn(
            'env_set "CLASSHUB_API_TOKEN_MAX_AGE_SECONDS" "86400"',
            quickstart_source,
        )
        self.assertIn(
            'env_set "HELPER_REQUIRE_CLASSHUB_TABLE" "1"',
            quickstart_source,
        )

    def test_demo_coursepack_uses_mounted_content_root(self) -> None:
        source = (REPO_ROOT / "scripts" / "load_demo_coursepack.sh").read_text(encoding="utf-8")

        self.assertIn("/content/courses", source)
        self.assertNotIn("/app/content/courses", source)

    def test_database_urls_expand_password_variable_not_literal_redaction(self) -> None:
        compose_text = (REPO_ROOT / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
        rendered = (
            compose_text.replace("${POSTGRES_USER}", "classhub")
            .replace("${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}", "runtime-secret")
            .replace("${POSTGRES_DB}", "classhub")
        )
        database_lines = [line.strip() for line in rendered.splitlines() if "DATABASE_URL:" in line]
        self.assertEqual(len(database_lines), 2)
        self.assertTrue(all(":runtime-secret@postgres:" in line for line in database_lines))
        self.assertTrue(all(":***@" not in line for line in database_lines))

        rehearsal = (REPO_ROOT / "scripts" / "backup_restore_rehearsal.sh").read_text(encoding="utf-8")
        self.assertIn("${POSTGRES_PASSWORD_URLENCODED}@${POSTGRES_HOST}", rehearsal)
        self.assertNotIn("postgres://${POSTGRES_USER_ESCAPED}:***@", rehearsal)

    def test_local_mode_valid_contract_passes(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
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
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
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

    def test_asset_mode_rejects_non_public_asset_hostname(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain.assets
            DOMAIN=lms.creatempls.org
            ASSET_DOMAIN=localhost
            CLASSHUB_ASSET_BASE_URL=https://localhost
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org,localhost
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid_public_asset_domain", result.stdout)

    def test_static_site_extra_valid_contract_passes(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            CADDY_STATIC_SITE_ROOT_HOST=/srv/cM_orgsite
            CADDY_STATIC_SITE_DOMAINS=creatempls.org, www.creatempls.org
            DOMAIN=lms.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_static_site_extra_requires_caddy_address_spacing(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            CADDY_STATIC_SITE_ROOT_HOST=/srv/cM_orgsite
            CADDY_STATIC_SITE_DOMAINS=creatempls.org,www.creatempls.org
            DOMAIN=lms.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid_static_site_domain_separator", result.stdout)

    def test_static_site_extra_requires_domain_mode_root_and_domains(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("static_site_requires_domain_mode", result.stdout)
        self.assertIn("missing_static_site_root", result.stdout)
        self.assertIn("missing_static_site_domains", result.stdout)

    def test_static_site_extra_rejects_lms_hostname_conflict(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            CADDY_STATIC_SITE_ROOT_HOST=/srv/cM_orgsite
            CADDY_STATIC_SITE_DOMAINS=lms.creatempls.org
            DOMAIN=lms.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("conflicting_static_site_domain", result.stdout)

    def test_static_site_extra_is_read_only_and_blocks_repository_metadata(self) -> None:
        compose_text = (REPO_ROOT / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
        deploy_text = (REPO_ROOT / "scripts" / "deploy_with_smoke.sh").read_text(encoding="utf-8")
        extra_text = (REPO_ROOT / "compose" / "Caddyfile.extra.static-site").read_text(encoding="utf-8")
        domain_text = (REPO_ROOT / "compose" / "Caddyfile.domain").read_text(encoding="utf-8")
        assets_text = (REPO_ROOT / "compose" / "Caddyfile.domain.assets").read_text(encoding="utf-8")

        self.assertIn(":/srv/caddy-static-site:ro", compose_text)
        self.assertIn(":/etc/caddy/Caddyfile.extra:ro", compose_text)
        self.assertIn("/.git/*", extra_text)
        self.assertIn("/README.md", extra_text)
        self.assertIn("try_files {path} {path}.html", extra_text)
        self.assertIn("import /etc/caddy/Caddyfile.extra", domain_text)
        self.assertIn("import /etc/caddy/Caddyfile.extra", assets_text)
        self.assertIn('! -d "${EXPECTED_STATIC_SITE_ROOT}"', deploy_text)
        self.assertIn('! -f "${EXPECTED_STATIC_SITE_ROOT}/index.html"', deploy_text)
        self.assertIn('eq .Destination "/etc/caddy/Caddyfile.extra"', deploy_text)
        self.assertIn('eq .Destination "/srv/caddy-static-site"', deploy_text)

    def test_memory_engine_proxy_valid_contract_passes(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain.assets
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            CADDY_STATIC_SITE_ROOT_HOST=/srv/cM_orgsite
            CADDY_STATIC_SITE_DOMAINS=creatempls.org, www.creatempls.org
            CADDY_PROXY_CONFIG_TEMPLATE=Caddyfile.proxy.memory-engine
            CADDY_MEMORY_ENGINE_DOMAIN=memory.creatempls.org
            CADDY_MEMORY_ENGINE_UPSTREAM=memory_engine_proxy:80
            DOMAIN=lms.creatempls.org
            ASSET_DOMAIN=assets.creatempls.org
            CLASSHUB_ASSET_BASE_URL=https://assets.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org,assets.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_memory_engine_proxy_rejects_local_mode_missing_domain_and_wrong_upstream(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            CADDY_PROXY_CONFIG_TEMPLATE=Caddyfile.proxy.memory-engine
            CADDY_MEMORY_ENGINE_UPSTREAM=memory-engine-api:8000
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("memory_engine_proxy_requires_domain_mode", result.stdout)
        self.assertIn("missing_memory_engine_domain", result.stdout)
        self.assertIn("invalid_memory_engine_upstream", result.stdout)

    def test_memory_engine_proxy_rejects_static_site_hostname_conflict(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain
            CADDY_EXTRA_CONFIG_TEMPLATE=Caddyfile.extra.static-site
            CADDY_STATIC_SITE_ROOT_HOST=/srv/cM_orgsite
            CADDY_STATIC_SITE_DOMAINS=creatempls.org, memory.creatempls.org
            CADDY_PROXY_CONFIG_TEMPLATE=Caddyfile.proxy.memory-engine
            CADDY_MEMORY_ENGINE_DOMAIN=memory.creatempls.org
            CADDY_MEMORY_ENGINE_UPSTREAM=memory_engine_proxy:80
            DOMAIN=lms.creatempls.org
            DJANGO_ALLOWED_HOSTS=lms.creatempls.org
            CSRF_TRUSTED_ORIGINS=https://lms.creatempls.org
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("conflicting_memory_engine_domain", result.stdout)

    def test_memory_engine_proxy_uses_tracked_fragment_and_public_edge_overlay(self) -> None:
        compose_text = (REPO_ROOT / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
        overlay_text = (REPO_ROOT / "compose" / "docker-compose.public-edge.yml").read_text(encoding="utf-8")
        proxy_text = (REPO_ROOT / "compose" / "Caddyfile.proxy.memory-engine").read_text(encoding="utf-8")
        deploy_text = (REPO_ROOT / "scripts" / "deploy_with_smoke.sh").read_text(encoding="utf-8")
        golden_smoke_text = (REPO_ROOT / "scripts" / "golden_path_smoke.sh").read_text(encoding="utf-8")
        system_doctor_text = (REPO_ROOT / "scripts" / "system_doctor.sh").read_text(encoding="utf-8")
        smoke_text = (REPO_ROOT / "scripts" / "smoke_check.sh").read_text(encoding="utf-8")

        self.assertIn(":/etc/caddy/Caddyfile.proxy:ro", compose_text)
        self.assertIn("reverse_proxy {$CADDY_MEMORY_ENGINE_UPSTREAM}", proxy_text)
        self.assertIn("redir / /kiosk/ 302", proxy_text)
        self.assertIn("public_edge:", overlay_text)
        self.assertIn("external: true", overlay_text)
        self.assertNotIn("classhub_web:", overlay_text)
        self.assertNotIn("helper_web:", overlay_text)
        self.assertIn('eq .Destination "/etc/caddy/Caddyfile.proxy"', deploy_text)
        self.assertIn("getent hosts memory_engine_proxy", deploy_text)
        self.assertIn("http://memory_engine_proxy/healthz", deploy_text)
        self.assertIn('env_file_value CADDY_PROXY_CONFIG_TEMPLATE', golden_smoke_text)
        self.assertIn('COMPOSE_ARGS+=(-f "${PUBLIC_EDGE_COMPOSE_FILE}")', golden_smoke_text)
        self.assertNotIn(
            '"$(env_file_value CADDY_PROXY_CONFIG_TEMPLATE)',
            system_doctor_text,
        )
        self.assertIn(
            'compose_env_file_value CADDY_PROXY_CONFIG_TEMPLATE "${ENV_FILE}"',
            system_doctor_text,
        )
        self.assertIn('COMPOSE_ARGS+=(-f "${PUBLIC_EDGE_COMPOSE_FILE}")', system_doctor_text)
        self.assertIn('index .NetworkSettings.Networks "public_edge"', system_doctor_text)
        self.assertIn("getent hosts memory_engine_proxy", system_doctor_text)
        self.assertIn('"http://${MEMORY_ENGINE_UPSTREAM}/healthz"', system_doctor_text)
        self.assertIn("SMOKE_RETURN_CODE_FOR_DEPLOY", deploy_text)
        self.assertIn("SMOKE_RETURN_CODE_FOR_GOLDEN", golden_smoke_text)
        self.assertIn("SMOKE_INVITE_RETURN_CODE_FOR_GOLDEN", golden_smoke_text)
        self.assertIn("print(f'FOUND:{student.return_code}' if student else 'MISSING')", deploy_text)
        self.assertIn("print(f'FOUND:{student.return_code}' if student else 'MISSING')", golden_smoke_text)
        self.assertIn('== FOUND:*', deploy_text)
        self.assertIn('== FOUND:*', golden_smoke_text)
        self.assertIn('"return_code":"%s"', golden_smoke_text)
        self.assertIn('RETURN_CODE="${SMOKE_RETURN_CODE:-}"', smoke_text)
        self.assertIn('"return_code":"%s"', smoke_text)

    def test_compose_env_file_value_selects_memory_engine_proxy_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "CADDY_PROXY_CONFIG_TEMPLATE=Caddyfile.proxy.memory-engine\n",
                encoding="utf-8",
            )
            command = (
                "CADDY_PROXY_CONFIG_TEMPLATE=Caddyfile.proxy.empty; "
                f'source "{REPO_ROOT / "scripts" / "lib" / "compose_env.sh"}"; '
                f'compose_env_file_value CADDY_PROXY_CONFIG_TEMPLATE "{env_path}"'
            )
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "Caddyfile.proxy.memory-engine")

    def test_domain_mode_rejects_non_public_hostname(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.domain
            DOMAIN=localhost
            DJANGO_ALLOWED_HOSTS=localhost
            CSRF_TRUSTED_ORIGINS=https://localhost
            DJANGO_SESSION_COOKIE_SECURE=1
            DJANGO_CSRF_COOKIE_SECURE=1
            REQUEST_SAFETY_TRUST_PROXY_HEADERS=1
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            """
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid_public_domain", result.stdout)

    def test_remote_compute_mode_requires_remote_target_contract(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
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

    def test_preflight_warns_for_simple_rejoin_and_strict_org_assignment(self) -> None:
        result = run_preflight(
            """
            CADDYFILE_TEMPLATE=Caddyfile.local
            DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
            CSRF_TRUSTED_ORIGINS=http://localhost
            DJANGO_SESSION_COOKIE_SECURE=0
            DJANGO_CSRF_COOKIE_SECURE=0
            HELPER_INTERNAL_RESET_URL=http://helper_web:8000/helper/internal/reset-class-conversations
            HELPER_INTERNAL_ACTOR_CLEAR_URL=http://helper_web:8000/helper/internal/clear-actor-conversations
            HELPER_INTERNAL_RAG_STATUS_URL=http://helper_web:8000/helper/internal/rag-status
            CLASSHUB_INTERNAL_EVENTS_URL=http://classhub_web:8000/internal/events/helper-chat-access
            LLM_ENABLED=0
            REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=1
            CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=0
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("organization_assignment_required", result.stdout)
        self.assertIn("CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
