from ._shared import *  # noqa: F401,F403
from django.core.cache import cache
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

class Teacher2FASetupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.teacher = get_user_model().objects.create_user(
            username="teacher_otp",
            password="pw12345",
            email="teacher_otp@example.org",
            is_staff=True,
            is_superuser=False,
        )

    def _invite_token(self):
        return signing.dumps(
            {
                "uid": self.teacher.id,
                "email": self.teacher.email,
                "username": self.teacher.username,
            },
            salt="classhub.teacher-2fa-setup",
        )

    def test_invite_link_renders_qr_setup_page(self):
        token = self._invite_token()
        resp = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertNotIn("token=", resp["Location"])

        follow = self.client.get(resp["Location"])
        self.assertEqual(follow.status_code, 200)
        self.assertEqual(follow["Cache-Control"], "private, no-store")
        self.assertContains(follow, "Scan QR Code")
        self.assertContains(follow, "Authenticator code")
        self.assertContains(follow, "/static/css/teach_setup_otp.css")
        self.assertNotContains(follow, "<style>", html=False)
        self.assertNotContains(follow, 'style="margin:0 0 10px 0"', html=False)
        self.assertTrue(TOTPDevice.objects.filter(user=self.teacher, name="teacher-primary").exists())

    def test_invite_link_can_confirm_totp_device(self):
        token = self._invite_token()
        resp = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(resp.status_code, 302)
        self.client.get(resp["Location"])
        device = TOTPDevice.objects.get(user=self.teacher, name="teacher-primary")
        otp_value = totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=device.drift,
        )
        otp_token = f"{otp_value:0{int(device.digits)}d}"
        resp = self.client.post(
            "/teach/2fa/setup",
            {
                "otp_token": f" {otp_token[:3]} {otp_token[3:]} ",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])

        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        event = AuditEvent.objects.filter(action="teacher_2fa.enroll", target_id=str(self.teacher.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.teacher.id)

    def test_invite_link_redirects_to_tokenless_url_preserving_next(self):
        token = self._invite_token()
        resp = self.client.get(f"/teach/2fa/setup?token={token}&next=/teach/lessons")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/teach/2fa/setup?next=%2Fteach%2Flessons")

    def test_invite_link_is_consumed_only_after_totp_confirmation(self):
        token = self._invite_token()
        first = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(first.status_code, 302)

        second = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(second.status_code, 302)

        self.client.get(second["Location"])
        device = TOTPDevice.objects.get(user=self.teacher, name="teacher-primary")
        otp_value = totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=device.drift,
        )
        otp_token = f"{otp_value:0{int(device.digits)}d}"
        confirmed = self.client.post("/teach/2fa/setup", {"otp_token": otp_token})
        self.assertEqual(confirmed.status_code, 302)

        consumed = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(consumed.status_code, 400)
        self.assertContains(consumed, "already used", status_code=400)

    def test_invalid_invite_link_returns_400(self):
        resp = self.client.get("/teach/2fa/setup?token=bad-token")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "Invalid setup link", status_code=400)

    @override_settings(
        CLASSHUB_TEACHER_2FA_RATE_LIMIT_PER_MINUTE=1,
        CLASSHUB_AUTH_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_teacher_2fa_setup_post_is_rate_limited(self):
        token = self._invite_token()
        resp = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(resp.status_code, 302)
        self.client.get(resp["Location"])

        first = self.client.post("/teach/2fa/setup", {"otp_token": "000000"})
        self.assertEqual(first.status_code, 200)

        second = self.client.post("/teach/2fa/setup", {"otp_token": "000000"})
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Retry-After"], "60")
        self.assertEqual(second["Cache-Control"], "no-store")
        self.assertContains(second, "Too many 2FA verification attempts", status_code=429)


class TeacherOTPEnforcementTests(TestCase):
    def setUp(self):
        self.teacher = get_user_model().objects.create_user(
            username="teacher_gate",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

    @override_settings(TEACHER_2FA_REQUIRED=True)
    def test_unverified_staff_redirects_to_teacher_2fa_setup(self):
        self.client.force_login(self.teacher)
        resp = self.client.get("/teach/lessons")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/2fa/setup", resp["Location"])
        self.assertIn("next=%2Fteach%2Flessons", resp["Location"])

    @override_settings(TEACHER_2FA_REQUIRED=True)
    def test_verified_staff_can_access_teacher_routes(self):
        _force_login_staff_verified(self.client, self.teacher)
        resp = self.client.get("/teach/lessons")
        self.assertEqual(resp.status_code, 200)


class TeacherSSOScaffoldTests(TestCase):
    def _google_provider_config(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            client_id="google-client-id",
            client_secret="google-client-secret",
            discovery_url="https://accounts.google.com/.well-known/openid-configuration",
            allowed_domains=("example.org",),
        )

    def _google_identity(self, *, email: str):
        from types import SimpleNamespace

        return SimpleNamespace(email=email, hosted_domain=email.split("@", 1)[-1])

    def test_teach_login_hides_sso_buttons_when_disabled(self):
        resp = self.client.get("/teach/login")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Continue with Google Workspace")

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google", "microsoft"),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object(), "microsoft": object()},
    )
    def test_teach_login_shows_configured_sso_buttons(self):
        resp = self.client.get("/teach/login?next=/teach/lessons")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Continue with Google Workspace")
        self.assertContains(resp, "Continue with Microsoft")
        self.assertContains(resp, "/teach/sso/start/google?next=%2Fteach%2Flessons")
        self.assertContains(resp, "/teach/sso/start/microsoft?next=%2Fteach%2Flessons")

    @override_settings(CLASSHUB_TEACHER_SSO_ENABLED=False)
    def test_sso_start_returns_404_when_disabled(self):
        resp = self.client.get("/teach/sso/start/google")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp["Cache-Control"], "private, no-store")

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object()},
    )
    def test_sso_start_redirects_to_google_authorize_endpoint(self):
        from urllib.parse import parse_qs, urlparse

        with override_settings(CLASSHUB_TEACHER_SSO_PROVIDERS={"google": self._google_provider_config()}), patch(
            "hub.views.teacher_parts.auth_sso._load_provider_discovery",
            return_value={
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
            },
        ):
            resp = self.client.get("/teach/sso/start/google?next=/teach/lessons")
        self.assertEqual(resp.status_code, 302)
        parsed = urlparse(resp["Location"])
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "accounts.google.com")
        params = parse_qs(parsed.query)
        self.assertEqual(params.get("client_id"), ["google-client-id"])
        self.assertEqual(params.get("response_type"), ["code"])
        self.assertEqual(params.get("scope"), ["openid email profile"])
        self.assertEqual(params.get("hd"), ["example.org"])
        self.assertTrue(params.get("state"))
        self.assertTrue(params.get("nonce"))
        self.assertEqual(resp["Cache-Control"], "private, no-store")

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("microsoft",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"microsoft": object()},
    )
    def test_sso_callback_redirects_to_login_notice_when_enabled_for_non_google(self):
        resp = self.client.get("/teach/sso/callback/microsoft?next=/teach")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/login?", resp["Location"])
        self.assertIn("Microsoft+SSO+callback+is+not+active+yet+in+this+build", resp["Location"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object()},
    )
    def test_google_callback_requires_state_and_code(self):
        with override_settings(CLASSHUB_TEACHER_SSO_PROVIDERS={"google": self._google_provider_config()}):
            resp = self.client.get("/teach/sso/callback/google")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/login?", resp["Location"])
        self.assertIn("did+not+include+required+callback+parameters", resp["Location"])

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object()},
        TEACHER_2FA_REQUIRED=False,
    )
    def test_google_callback_logs_in_staff_user_on_success(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_google",
            email="teacher_google@example.org",
            password="pw12345",
            is_staff=True,
            is_active=True,
        )
        with override_settings(CLASSHUB_TEACHER_SSO_PROVIDERS={"google": self._google_provider_config()}), patch(
            "hub.views.teacher_parts.auth_sso._consume_sso_state",
            return_value={"next": "/teach/lessons", "nonce": "nonce-123"},
        ), patch(
            "hub.views.teacher_parts.auth_sso._google_exchange_code_for_identity",
            return_value=self._google_identity(email=teacher.email),
        ):
            resp = self.client.get("/teach/sso/callback/google?state=state-1&code=code-1")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/teach/lessons")
        self.assertEqual(int(self.client.session.get("_auth_user_id")), teacher.id)

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object()},
    )
    def test_google_callback_rejects_unlinked_identity(self):
        with override_settings(CLASSHUB_TEACHER_SSO_PROVIDERS={"google": self._google_provider_config()}), patch(
            "hub.views.teacher_parts.auth_sso._consume_sso_state",
            return_value={"next": "/teach", "nonce": "nonce-123"},
        ), patch(
            "hub.views.teacher_parts.auth_sso._google_exchange_code_for_identity",
            return_value=self._google_identity(email="missing_staff@example.org"),
        ):
            resp = self.client.get("/teach/sso/callback/google?state=state-1&code=code-1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/login?", resp["Location"])
        self.assertIn("No+teacher+account+is+linked+to+this+organization+email", resp["Location"])

    @override_settings(
        CLASSHUB_TEACHER_SSO_ENABLED=True,
        CLASSHUB_TEACHER_SSO_ALLOW_PASSWORD_FALLBACK=False,
        CLASSHUB_TEACHER_SSO_ENABLED_PROVIDERS=("google",),
        CLASSHUB_TEACHER_SSO_PROVIDERS={"google": object()},
    )
    def test_teach_login_hides_password_form_when_fallback_disabled(self):
        with override_settings(CLASSHUB_TEACHER_SSO_PROVIDERS={"google": self._google_provider_config()}):
            resp = self.client.get("/teach/login")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Sign in to your account")
        self.assertContains(resp, "Password login disabled")


class Admin2FATests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="admin",
            password="pw12345",
            email="admin@example.org",
        )

    def test_admin_requires_2fa_for_superuser(self):
        self.client.force_login(self.superuser)
        resp = self.client.get("/admin/", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    @override_settings(ADMIN_2FA_REQUIRED=False)
    def test_admin_allows_superuser_when_2fa_disabled(self):
        self.client.force_login(self.superuser)
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)

    @override_settings(
        CLASSHUB_ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE=1,
        CLASSHUB_AUTH_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_admin_login_post_is_rate_limited(self):
        first = self.client.post(
            "/admin/login/",
            {"username": "admin", "password": "wrong", "otp_token": "123456"},
        )
        self.assertNotEqual(first.status_code, 429)

        second = self.client.post(
            "/admin/login/",
            {"username": "admin", "password": "wrong", "otp_token": "123456"},
        )
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Retry-After"], "60")
        self.assertEqual(second["Cache-Control"], "no-store")
        self.assertContains(second, "Too many admin login attempts", status_code=429)


class CreateTeacherCommandTests(TestCase):
    def test_create_teacher_defaults_to_staff_non_superuser(self):
        out = StringIO()
        call_command(
            "create_teacher",
            username="teacher1",
            email="teacher1@example.org",
            password="pw12345",
            stdout=out,
        )

        user = get_user_model().objects.get(username="teacher1")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("pw12345"))
        self.assertEqual(user.email, "teacher1@example.org")
        self.assertIn("Created teacher", out.getvalue())

    def test_create_teacher_existing_without_update_errors(self):
        get_user_model().objects.create_user(username="teacher1", password="pw12345")
        with self.assertRaises(CommandError):
            call_command("create_teacher", username="teacher1", password="newpass")

    def test_create_teacher_update_changes_password_and_status(self):
        user = get_user_model().objects.create_user(
            username="teacher1",
            email="old@example.org",
            password="oldpass",
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        self.assertFalse(user.is_staff)

        out = StringIO()
        call_command(
            "create_teacher",
            username="teacher1",
            password="newpass",
            update=True,
            inactive=True,
            clear_email=True,
            stdout=out,
        )

        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("newpass"))
        self.assertEqual(user.email, "")
        self.assertIn("Updated teacher", out.getvalue())


class BootstrapAdminOTPCommandTests(TestCase):
    def test_bootstrap_admin_otp_creates_totp_device_for_superuser(self):
        get_user_model().objects.create_superuser(
            username="admin",
            password="pw12345",
            email="admin@example.org",
        )
        out = StringIO()
        call_command("bootstrap_admin_otp", username="admin", stdout=out)
        self.assertTrue(TOTPDevice.objects.filter(user__username="admin", name="admin-primary").exists())
        self.assertIn("Created TOTP device", out.getvalue())

    def test_bootstrap_admin_otp_rejects_non_superuser(self):
        get_user_model().objects.create_user(
            username="teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        with self.assertRaises(CommandError):
            call_command("bootstrap_admin_otp", username="teacher")

    def test_bootstrap_admin_otp_if_missing_preserves_existing_device(self):
        user = get_user_model().objects.create_superuser(
            username="admin",
            password="pw12345",
            email="admin@example.org",
        )
        existing = TOTPDevice.objects.create(user=user, name="admin-primary", confirmed=True)
        out = StringIO()

        call_command("bootstrap_admin_otp", username="admin", if_missing=True, stdout=out)

        self.assertEqual(TOTPDevice.objects.filter(user=user, name="admin-primary").count(), 1)
        self.assertTrue(TOTPDevice.objects.filter(pk=existing.pk).exists())
        self.assertIn("already exists", out.getvalue())

    def test_bootstrap_admin_otp_if_missing_adds_requested_static_backup(self):
        user = get_user_model().objects.create_superuser(
            username="admin",
            password="pw12345",
            email="admin@example.org",
        )
        existing = TOTPDevice.objects.create(user=user, name="admin-primary", confirmed=True)
        out = StringIO()

        call_command(
            "bootstrap_admin_otp",
            username="admin",
            if_missing=True,
            with_static_backup=True,
            stdout=out,
        )

        self.assertTrue(TOTPDevice.objects.filter(pk=existing.pk).exists())
        backup_device = StaticDevice.objects.get(user=user, name="admin-primary-backup")
        self.assertEqual(StaticToken.objects.filter(device=backup_device).count(), 1)
        self.assertIn("Generated one-time static backup token", out.getvalue())
