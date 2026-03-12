from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class TeacherPortalTeacherAccountsTests(TeacherPortalBaseTests):
    def test_teacher_can_update_own_profile_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/profile/update",
            {
                "first_name": "Terry",
                "last_name": "Portal",
                "email": "terry.portal@example.org",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Terry")
        self.assertEqual(self.staff.last_name, "Portal")
        self.assertEqual(self.staff.email, "terry.portal@example.org")

        event = AuditEvent.objects.filter(action="teacher_profile.update_self").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_teacher_profile_update_rejects_invalid_email(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/update",
            {
                "first_name": "Terry",
                "last_name": "Portal",
                "email": "invalid-email",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "")

    def test_teacher_can_change_password_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/password",
            {
                "current_password": "pw12345",
                "new_password": "N3wTeacherPw123!",
                "new_password_confirm": "N3wTeacherPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("N3wTeacherPw123!"))
        teach_resp = self.client.get("/teach")
        self.assertEqual(teach_resp.status_code, 200)

        event = AuditEvent.objects.filter(action="teacher_profile.change_password").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_teacher_password_change_rejects_wrong_current_password(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/password",
            {
                "current_password": "not-right",
                "new_password": "N3wTeacherPw123!",
                "new_password_confirm": "N3wTeacherPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("pw12345"))
        self.assertFalse(AuditEvent.objects.filter(action="teacher_profile.change_password").exists())

    def test_teacher_logout_ends_staff_session(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/teach/login")
        self.assertIsNone(self.client.session.get("_auth_user_id"))

        denied = self.client.get("/teach")
        self.assertEqual(denied.status_code, 302)
        self.assertIn("/teach/login", denied["Location"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CLASSHUB_PRODUCT_NAME="Pilot Classroom Hub",
    )
    def test_superuser_can_create_teacher_and_send_invite(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/create-teacher",
            {
                "username": "teacher2",
                "email": "teacher2@example.org",
                "first_name": "Terry",
                "last_name": "Teacher",
                "password": "StartPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])

        user = get_user_model().objects.get(username="teacher2")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.email, "teacher2@example.org")
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["teacher2@example.org"])
        self.assertEqual(msg.subject, "Complete your Pilot Classroom Hub teacher 2FA setup")
        self.assertIn("Your Pilot Classroom Hub teacher account is ready.", msg.body)
        self.assertIn("/teach/2fa/setup?token=", msg.body)
        self.assertNotIn("Temporary password:", msg.body)

        event = AuditEvent.objects.filter(action="teacher_account.create", target_id=str(user.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_set_teacher_account_active_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_active_toggle",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        disable_resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_active": "0",
            },
        )
        self.assertEqual(disable_resp.status_code, 302)
        self.assertIn("teacher_invite=1", disable_resp["Location"])
        target.refresh_from_db()
        self.assertFalse(target.is_active)

        enable_resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_active": "1",
            },
        )
        self.assertEqual(enable_resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_active)

        event = AuditEvent.objects.filter(action="teacher_account.set_active", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_set_teacher_account_superuser_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_super_toggle",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        promote_resp = self.client.post(
            "/teach/teacher-account/set-superuser",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_superuser": "1",
            },
        )
        self.assertEqual(promote_resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_superuser)

        demote_resp = self.client.post(
            "/teach/teacher-account/set-superuser",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_superuser": "0",
            },
        )
        self.assertEqual(demote_resp.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_superuser)

        event = AuditEvent.objects.filter(action="teacher_account.set_superuser", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_reset_teacher_account_password_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_pw_reset",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/teacher-account/reset-password",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_password": "TempNewPassword123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.check_password("TempNewPassword123!"))

        event = AuditEvent.objects.filter(action="teacher_account.reset_password", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CLASSHUB_PRODUCT_NAME="Pilot Classroom Hub",
    )
    def test_superuser_can_resend_teacher_invite_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_resend_invite",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            email="teacher.resend@example.org",
            first_name="Resend",
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/teacher-account/resend-invite",
            {
                "teacher_account_user_id": str(target.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["teacher.resend@example.org"])
        self.assertIn("Complete your Pilot Classroom Hub teacher 2FA setup", msg.subject)
        self.assertIn("/teach/2fa/setup?token=", msg.body)

        event = AuditEvent.objects.filter(action="teacher_account.resend_invite", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_disable_current_account_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(self.staff.id),
                "teacher_account_active": "0",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

    def test_non_superuser_staff_cannot_create_teacher_account(self):
        non_super_staff = get_user_model().objects.create_user(
            username="assistant",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, non_super_staff)

        resp = self.client.post(
            "/teach/create-teacher",
            {
                "username": "blocked",
                "email": "blocked@example.org",
                "password": "StartPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(get_user_model().objects.filter(username="blocked").exists())

