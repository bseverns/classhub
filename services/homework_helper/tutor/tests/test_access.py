import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

class HelperAdminAccessTests(TestCase):
    def test_helper_admin_requires_superuser(self):
        user = get_user_model().objects.create_user(
            username="teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.client.force_login(user)

        resp = self.client.get("/admin/", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    def test_helper_admin_requires_2fa_for_superuser(self):
        user = get_user_model().objects.create_superuser(
            username="admin",
            password="pw12345",
            email="admin@example.org",
        )
        self.client.force_login(user)

        resp = self.client.get("/admin/", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    @override_settings(ADMIN_2FA_REQUIRED=False)
    def test_helper_admin_allows_superuser_when_2fa_disabled(self):
        user = get_user_model().objects.create_superuser(
            username="admin2",
            password="pw12345",
            email="admin2@example.org",
        )
        self.client.force_login(user)

        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)


class HelperSecurityHeaderTests(TestCase):
    @override_settings(
        CSP_POLICY="default-src 'self'",
        CSP_REPORT_ONLY_POLICY="default-src 'self'; report-uri /__csp-report__",
        PERMISSIONS_POLICY="camera=(), microphone=()",
        SECURITY_REFERRER_POLICY="strict-origin-when-cross-origin",
        X_FRAME_OPTIONS="DENY",
    )
    def test_healthz_sets_security_headers(self):
        resp = self.client.get("/helper/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'self'")
        self.assertEqual(resp["Content-Security-Policy-Report-Only"], "default-src 'self'; report-uri /__csp-report__")
        self.assertEqual(resp["Permissions-Policy"], "camera=(), microphone=()")
        self.assertEqual(resp["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(resp["X-Frame-Options"], "DENY")


class HelperCSPModeTests(TestCase):
    _RELAXED_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'"
    _STRICT_POLICY = "default-src 'self'; script-src 'self'"

    @override_settings(
        CSP_MODE="relaxed",
        CSP_MODE_DEFAULTS_ENABLED=True,
        CSP_POLICY="",
        CSP_REPORT_ONLY_POLICY="",
        CSP_POLICY_RELAXED=_RELAXED_POLICY,
        CSP_POLICY_STRICT=_STRICT_POLICY,
    )
    def test_relaxed_mode_sets_enforced_and_report_only_headers(self):
        resp = self.client.get("/helper/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Security-Policy"], self._RELAXED_POLICY)
        self.assertEqual(resp["Content-Security-Policy-Report-Only"], self._STRICT_POLICY)

    @override_settings(
        CSP_MODE="report-only",
        CSP_MODE_DEFAULTS_ENABLED=True,
        CSP_POLICY="",
        CSP_REPORT_ONLY_POLICY="",
        CSP_POLICY_RELAXED=_RELAXED_POLICY,
        CSP_POLICY_STRICT=_STRICT_POLICY,
    )
    def test_report_only_mode_sets_report_only_header_only(self):
        resp = self.client.get("/helper/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Content-Security-Policy", resp)
        self.assertEqual(resp["Content-Security-Policy-Report-Only"], self._STRICT_POLICY)

    @override_settings(
        CSP_MODE="strict",
        CSP_MODE_DEFAULTS_ENABLED=True,
        CSP_POLICY="",
        CSP_REPORT_ONLY_POLICY="",
        CSP_POLICY_RELAXED=_RELAXED_POLICY,
        CSP_POLICY_STRICT=_STRICT_POLICY,
    )
    def test_strict_mode_sets_enforced_header_only(self):
        resp = self.client.get("/helper/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Security-Policy"], self._STRICT_POLICY)
        self.assertNotIn("Content-Security-Policy-Report-Only", resp)


class HelperSiteModeTests(TestCase):
    @override_settings(SITE_MODE="join-only")
    def test_join_only_blocks_chat_endpoint(self):
        resp = self.client.post(
            "/helper/chat",
            data=json.dumps({"message": "help"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json().get("error"), "site_mode_restricted")
        self.assertEqual(resp.json().get("site_mode"), "join-only")

    @override_settings(SITE_MODE="maintenance")
    def test_maintenance_still_allows_healthz(self):
        resp = self.client.get("/helper/healthz")
        self.assertEqual(resp.status_code, 200)


