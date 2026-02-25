import csv
import json
import re
import tempfile
import zipfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils import timezone

from common.helper_scope import parse_scope_token

from .models import (
    AuditEvent,
    Class,
    LessonAsset,
    LessonAssetFolder,
    LessonVideo,
    LessonRelease,
    Material,
    Module,
    StudentEvent,
    StudentIdentity,
    Submission,
)
from .services.upload_scan import ScanResult
from .services.helper_control import HelperResetResult


def _sample_sb3_bytes() -> bytes:
    """Build a tiny valid Scratch archive for upload-path tests."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", '{"targets":[],"meta":{"semver":"3.0.0"}}')
    return buf.getvalue()


def _force_login_staff_verified(client: Client, user) -> None:
    """Authenticate and mark OTP as verified for /teach tests."""
    client.force_login(user)
    device, _ = TOTPDevice.objects.get_or_create(
        user=user,
        name="teacher-primary",
        defaults={"confirmed": True},
    )
    if not device.confirmed:
        device.confirmed = True
        device.save(update_fields=["confirmed"])
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()


class RetentionSettingParsingTests(SimpleTestCase):
    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS=0, CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=0)
    def test_retention_days_preserves_explicit_zero(self):
        from .views.content import _retention_days as content_retention_days
        from .views.student import _retention_days as student_retention_days

        self.assertEqual(student_retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90), 0)
        self.assertEqual(content_retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180), 0)

    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS="bad", CLASSHUB_STUDENT_EVENT_RETENTION_DAYS="bad")
    def test_retention_days_falls_back_to_default_on_invalid_values(self):
        from .views.content import _retention_days as content_retention_days
        from .views.student import _retention_days as student_retention_days

        self.assertEqual(student_retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90), 90)
        self.assertEqual(content_retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180), 180)


class TeacherPortalTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )

    def _build_lesson_with_submission(self):
        classroom = Class.objects.create(name="Period 1", join_code="ABCD1234")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        Material.objects.create(
            module=module,
            title="Session 1 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/01-welcome-private-workflow",
            order_index=0,
        )
        upload = Material.objects.create(
            module=module,
            title="Upload your project file",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        student_a = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentIdentity.objects.create(classroom=classroom, display_name="Ben")
        Submission.objects.create(
            material=upload,
            student=student_a,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )
        return classroom, upload

    def test_teach_lessons_requires_staff(self):
        resp = self.client.get("/teach/lessons")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/login", resp["Location"])

    def test_teach_lessons_shows_submission_progress(self):
        classroom, upload = self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/lessons?class_id={classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Session 1 lesson")
        self.assertContains(resp, "Submitted 1 / 2")
        self.assertContains(resp, "Review missing now (1)")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions?show=missing")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions?download=zip_latest")

    def test_teach_home_shows_recent_submissions(self):
        self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Recent submissions")
        self.assertContains(resp, "Ada")
        self.assertContains(resp, "Generate Course Authoring Templates")
        self.assertContains(resp, "Invite teacher")

    def test_teach_home_shows_since_yesterday_digest(self):
        classroom, upload = self._build_lesson_with_submission()
        student = StudentIdentity.objects.filter(classroom=classroom, display_name="Ada").first()
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "What Changed Since Yesterday")
        self.assertContains(resp, "End-of-Class Closeout")
        self.assertContains(resp, "1 / 2")
        self.assertContains(resp, f"/teach/class/{classroom.id}/export-submissions-today")
        self.assertContains(resp, f"/teach/class/{classroom.id}/lock")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions")

    def test_teach_closeout_lock_endpoint_sets_class_locked(self):
        classroom, _upload = self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(f"/teach/class/{classroom.id}/lock")
        self.assertEqual(resp.status_code, 302)
        classroom.refresh_from_db()
        self.assertTrue(classroom.is_locked)
        self.assertIn("/teach?notice=", resp["Location"])

        event = AuditEvent.objects.filter(action="class.lock").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)

    def test_teach_closeout_export_only_includes_today_submissions(self):
        classroom, upload = self._build_lesson_with_submission()
        student = StudentIdentity.objects.filter(classroom=classroom, display_name="Ada").first()
        old_submission = Submission.objects.create(
            material=upload,
            student=student,
            original_filename="old_project.sb3",
            file=SimpleUploadedFile("old_project.sb3", b"old"),
        )
        Submission.objects.filter(id=old_submission.id).update(uploaded_at=timezone.now() - timedelta(days=2))
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/export-submissions-today")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])

        zip_bytes = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            names = archive.namelist()
        self.assertEqual(len(names), 1)
        self.assertIn("project.sb3", names[0])

    def test_teach_closeout_export_empty_zip_contains_readme(self):
        classroom = Class.objects.create(name="Period Empty", join_code="EMT12345")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/export-submissions-today")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])

        zip_bytes = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            names = archive.namelist()
            self.assertEqual(names, ["README.txt"])
            readme = archive.read("README.txt").decode("utf-8")
        self.assertIn("No submission files were available", readme)

    def test_teach_class_join_card_renders_printable_details(self):
        classroom = Class.objects.create(name="Period 2", join_code="JOIN7788")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/join-card")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "Student Join Card")
        self.assertContains(resp, "JOIN7788")
        self.assertContains(resp, "/?class_code=JOIN7788")

    def test_teach_class_masks_return_codes_by_default(self):
        classroom = Class.objects.create(name="Period Roster", join_code="MASK1234")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "••••••")
        self.assertNotContains(resp, f">{student.return_code}<", html=False)
        self.assertContains(resp, "Show")

    def test_teach_delete_student_data_removes_student_submissions_and_events(self):
        classroom = Class.objects.create(name="Delete Data Class", join_code="DEL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        upload = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        Submission.objects.create(
            material=upload,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            source="test",
            details={"submission_id": 1},
        )
        _force_login_staff_verified(self.client, self.staff)
        start_epoch = classroom.session_epoch

        resp = self.client.post(
            f"/teach/class/{classroom.id}/delete-student-data",
            {"student_id": str(student.id), "confirm_delete": "1"},
        )
        self.assertEqual(resp.status_code, 302)
        classroom.refresh_from_db()
        self.assertEqual(classroom.session_epoch, start_epoch + 1)
        self.assertFalse(StudentIdentity.objects.filter(id=student.id).exists())
        self.assertEqual(Submission.objects.filter(student_id=student.id).count(), 0)
        self.assertEqual(StudentEvent.objects.filter(student_id=student.id).count(), 0)

    @patch("hub.views.teacher_parts.content.generate_authoring_templates")
    def test_teach_home_can_generate_authoring_templates(self, mock_generate):
        mock_generate.return_value.output_paths = [
            Path("/uploads/authoring_templates/sample-teacher-plan-template.md"),
            Path("/uploads/authoring_templates/sample-teacher-plan-template.docx"),
            Path("/uploads/authoring_templates/sample-public-overview-template.md"),
            Path("/uploads/authoring_templates/sample-public-overview-template.docx"),
        ]
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/generate-authoring-templates",
            {
                "template_slug": "sample_slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("template_slug=sample_slug", resp["Location"])

        mock_generate.assert_called_once()
        kwargs = mock_generate.call_args.kwargs
        self.assertEqual(kwargs["slug"], "sample_slug")
        self.assertEqual(kwargs["title"], "Sample Course")
        self.assertEqual(kwargs["sessions"], 12)
        self.assertEqual(kwargs["duration"], 75)
        self.assertTrue(kwargs["overwrite"])

        event = AuditEvent.objects.filter(action="teacher_templates.generate").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
        self.assertEqual(event.target_id, "sample_slug")

    @patch("hub.views.teacher_parts.content.generate_authoring_templates")
    def test_teach_home_template_generator_rejects_invalid_slug(self, mock_generate):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/generate-authoring-templates",
            {
                "template_slug": "Bad Slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        mock_generate.assert_not_called()

    def test_teach_home_shows_template_download_links_for_selected_slug(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            (template_dir / "sample_slug-teacher-plan-template.md").write_text("hello", encoding="utf-8")
            with override_settings(CLASSHUB_AUTHORING_TEMPLATE_DIR=template_dir):
                resp = self.client.get("/teach?template_slug=sample_slug")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/teach/authoring-template/download?slug=sample_slug&amp;kind=teacher_plan_md")
        self.assertContains(resp, "sample_slug-teacher-plan-template.docx (not generated yet)")

    def test_staff_can_download_generated_authoring_template(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            expected_path = template_dir / "sample_slug-teacher-plan-template.md"
            expected_path.write_text("sample-body", encoding="utf-8")
            with override_settings(CLASSHUB_AUTHORING_TEMPLATE_DIR=template_dir):
                resp = self.client.get("/teach/authoring-template/download?slug=sample_slug&kind=teacher_plan_md")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertIn("sample_slug-teacher-plan-template.md", resp["Content-Disposition"])
        body = b"".join(resp.streaming_content)
        self.assertEqual(body, b"sample-body")

        event = AuditEvent.objects.filter(action="teacher_templates.download").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_staff_download_authoring_template_rejects_invalid_kind(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/authoring-template/download?slug=sample_slug&kind=unknown_kind")
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Invalid template kind.")

    def test_staff_download_authoring_template_rejects_traversal_slug(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/authoring-template/download?slug=..%2Fetc%2Fpasswd&kind=teacher_plan_md")
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Invalid template slug.")

    def test_teacher_logout_ends_staff_session(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/teach/login")
        self.assertIsNone(self.client.session.get("_auth_user_id"))

        denied = self.client.get("/teach")
        self.assertEqual(denied.status_code, 302)
        self.assertIn("/teach/login", denied["Location"])

    def test_teacher_can_rename_student(self):
        classroom = Class.objects.create(name="Period Rename", join_code="REN12345")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ari")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/rename-student",
            {"student_id": str(student.id), "display_name": "Aria"},
        )
        self.assertEqual(resp.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.display_name, "Aria")

    def test_teacher_can_merge_students(self):
        classroom = Class.objects.create(name="Period Merge", join_code="MRG12345")
        module = Module.objects.create(classroom=classroom, title="Session", order_index=0)
        upload = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        source = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        target = StudentIdentity.objects.create(classroom=classroom, display_name="Ada W")
        Submission.objects.create(
            material=upload,
            student=source,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=source,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/merge-students",
            {
                "source_student_id": str(source.id),
                "target_student_id": str(target.id),
                "confirm_merge": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(StudentIdentity.objects.filter(id=source.id).exists())
        self.assertTrue(StudentIdentity.objects.filter(id=target.id).exists())
        self.assertEqual(Submission.objects.filter(student=target).count(), 1)
        self.assertEqual(StudentEvent.objects.filter(student=target, event_type=StudentEvent.EVENT_CLASS_JOIN).count(), 1)

        event = AuditEvent.objects.filter(action="student.merge").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.target_id, str(target.id))

    def test_teacher_merge_students_requires_confirmation(self):
        classroom = Class.objects.create(name="Period Merge Confirm", join_code="MGC12345")
        source = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        target = StudentIdentity.objects.create(classroom=classroom, display_name="Ada W")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/merge-students",
            {
                "source_student_id": str(source.id),
                "target_student_id": str(target.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(StudentIdentity.objects.filter(id=source.id).exists())
        self.assertTrue(StudentIdentity.objects.filter(id=target.id).exists())
        self.assertEqual(AuditEvent.objects.filter(action="student.merge").count(), 0)

    def test_teacher_merge_students_rejects_same_source_and_target(self):
        classroom = Class.objects.create(name="Period Merge Same", join_code="MGS12345")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/merge-students",
            {
                "source_student_id": str(student.id),
                "target_student_id": str(student.id),
                "confirm_merge": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(StudentIdentity.objects.filter(id=student.id).exists())
        self.assertEqual(AuditEvent.objects.filter(action="student.merge").count(), 0)

    def test_teacher_can_reset_roster_and_rotate_code(self):
        classroom = Class.objects.create(name="Period Reset", join_code="RST12345")
        module = Module.objects.create(classroom=classroom, title="Session", order_index=0)
        upload = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Mia")
        Submission.objects.create(
            material=upload,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )
        old_code = classroom.join_code
        old_epoch = classroom.session_epoch

        student_client = Client()
        session = student_client.session
        session["student_id"] = student.id
        session["class_id"] = classroom.id
        session["class_epoch"] = old_epoch
        session.save()

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            f"/teach/class/{classroom.id}/reset-roster",
            {"rotate_code": "1"},
        )
        self.assertEqual(resp.status_code, 302)

        classroom.refresh_from_db()
        self.assertNotEqual(classroom.join_code, old_code)
        self.assertEqual(classroom.session_epoch, old_epoch + 1)
        self.assertEqual(StudentIdentity.objects.filter(classroom=classroom).count(), 0)
        self.assertEqual(Submission.objects.filter(material=upload).count(), 0)

        student_resp = student_client.get("/student")
        self.assertEqual(student_resp.status_code, 302)
        self.assertEqual(student_resp["Location"], "/")

    @patch("hub.views.teacher_parts.roster._reset_helper_class_conversations")
    def test_teacher_can_reset_helper_conversations(self, reset_mock):
        classroom = Class.objects.create(name="Period Helper", join_code="HLP12345")
        reset_mock.return_value = HelperResetResult(ok=True, deleted_conversations=4, status_code=200)

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(f"/teach/class/{classroom.id}/reset-helper-conversations")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/class/", resp["Location"])
        self.assertIn("notice=", resp["Location"])

        reset_mock.assert_called_once()
        event = AuditEvent.objects.filter(action="class.reset_helper_conversations").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("deleted_conversations"), 4)

    @patch("hub.views.teacher_parts.roster._reset_helper_class_conversations")
    def test_teacher_reset_helper_conversations_handles_failure(self, reset_mock):
        classroom = Class.objects.create(name="Period Helper Fail", join_code="HLF12345")
        reset_mock.return_value = HelperResetResult(ok=False, error_code="helper_unreachable", status_code=0)

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(f"/teach/class/{classroom.id}/reset-helper-conversations")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=", resp["Location"])

        event = AuditEvent.objects.filter(action="class.reset_helper_conversations_failed").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("error_code"), "helper_unreachable")

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


class Teacher2FASetupTests(TestCase):
    def setUp(self):
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

    def test_invite_link_is_one_time_use(self):
        token = self._invite_token()
        first = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(first.status_code, 302)

        second = self.client.get(f"/teach/2fa/setup?token={token}")
        self.assertEqual(second.status_code, 400)
        self.assertContains(second, "already used", status_code=400)

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


class LessonReleaseTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="teacher_release",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.classroom = Class.objects.create(name="Release Class", join_code="REL12345")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        Material.objects.create(
            module=self.module,
            title="Session 1 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/s01-welcome-private-workflow",
            order_index=0,
        )
        self.upload = Material.objects.create(
            module=self.module,
            title="Homework dropbox",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_teacher_can_set_release_date_from_interface(self):
        _force_login_staff_verified(self.client, self.staff)
        target_date = timezone.localdate() + timedelta(days=3)

        resp = self.client.post(
            "/teach/lessons/release",
            {
                "class_id": str(self.classroom.id),
                "course_slug": "piper_scratch_12_session",
                "lesson_slug": "s01-welcome-private-workflow",
                "action": "set_date",
                "available_on": target_date.isoformat(),
                "return_to": f"/teach/lessons?class_id={self.classroom.id}",
            },
        )
        self.assertEqual(resp.status_code, 302)

        row = LessonRelease.objects.get(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
        )
        self.assertEqual(row.available_on, target_date)
        self.assertFalse(row.force_locked)

    def test_teacher_can_set_helper_scope_from_interface(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/lessons/release",
            {
                "class_id": str(self.classroom.id),
                "course_slug": "piper_scratch_12_session",
                "lesson_slug": "s01-welcome-private-workflow",
                "action": "set_helper_scope",
                "helper_context_override": "Piper wiring mentor",
                "helper_topics_override": "Breadboard checks\nRetest loop",
                "helper_allowed_topics_override": "Piper circuits\nStoryMode controls",
                "helper_reference_override": "piper-hardware",
                "return_to": f"/teach/class/{self.classroom.id}",
            },
        )
        self.assertEqual(resp.status_code, 302)

        row = LessonRelease.objects.get(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
        )
        self.assertEqual(row.helper_context_override, "Piper wiring mentor")
        self.assertEqual(row.helper_topics_override, "Breadboard checks\nRetest loop")
        self.assertEqual(row.helper_allowed_topics_override, "Piper circuits\nStoryMode controls")
        self.assertEqual(row.helper_reference_override, "piper-hardware")

    def test_student_helper_scope_uses_class_override(self):
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            helper_context_override="Piper wiring mentor",
            helper_topics_override="Breadboard checks\nRetest loop",
            helper_allowed_topics_override="Piper circuits\nStoryMode controls",
            helper_reference_override="piper-hardware",
        )
        self._login_student()

        resp = self.client.get("/course/piper_scratch_12_session/s01-welcome-private-workflow")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-helper-context="Piper wiring mentor"')
        self.assertContains(resp, 'data-helper-topics="Breadboard checks | Retest loop"')
        self.assertContains(resp, 'data-helper-reference="piper-hardware"')

        body = resp.content.decode("utf-8")
        token_match = re.search(r'data-helper-scope-token="([^"]+)"', body)
        self.assertIsNotNone(token_match)
        scope = parse_scope_token(token_match.group(1), max_age_seconds=3600)
        self.assertEqual(scope["context"], "Piper wiring mentor")
        self.assertEqual(scope["topics"], ["Breadboard checks", "Retest loop"])
        self.assertEqual(scope["allowed_topics"], ["Piper circuits", "StoryMode controls"])
        self.assertEqual(scope["reference"], "piper-hardware")

    def test_student_lesson_is_intro_only_before_release(self):
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            available_on=timezone.localdate() + timedelta(days=2),
        )
        self._login_student()

        resp = self.client.get("/course/piper_scratch_12_session/s01-welcome-private-workflow")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "intro-only mode")
        self.assertNotContains(resp, "Homework dropbox")

    def test_student_home_shows_preview_link_for_locked_lesson(self):
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            available_on=timezone.localdate() + timedelta(days=2),
        )
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Full lesson locked")
        self.assertContains(resp, "Preview intro-only page")
        self.assertNotContains(resp, "Open lesson", status_code=200)

    def test_student_home_masks_return_code_by_default(self):
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "••••••")
        self.assertNotContains(resp, f">{self.student.return_code}<", html=False)
        self.assertContains(resp, "Copy return code")

    @patch("hub.views.content.load_course_manifest", return_value={"title": "Demo", "lessons": [{"slug": "demo-lesson"}]})
    @patch("hub.views.content.load_lesson_markdown", side_effect=ValueError("secret details should not leak"))
    def test_course_lesson_does_not_expose_metadata_exception_details(self, _mock_lesson, _mock_manifest):
        resp = self.client.get("/course/demo-course/demo-lesson")
        self.assertEqual(resp.status_code, 500)
        self.assertContains(resp, "Lesson metadata invalid.", status_code=500)
        self.assertNotContains(resp, "secret details should not leak", status_code=500)

    def test_student_upload_is_blocked_before_release(self):
        locked_until = timezone.localdate() + timedelta(days=2)
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            available_on=locked_until,
        )
        self._login_student()

        resp = self.client.post(
            f"/material/{self.upload.id}/upload",
            {"file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes())},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, locked_until.isoformat(), status_code=403)

    @override_settings(
        CLASSHUB_UPLOAD_SCAN_ENABLED=True,
        CLASSHUB_UPLOAD_SCAN_FAIL_CLOSED=True,
    )
    @patch("hub.views.student.scan_uploaded_file", return_value=ScanResult(status="error", message="scanner down"))
    def test_student_upload_blocks_when_scan_fails_closed(self, _scan_mock):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.upload.id}/upload",
            {"file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes())},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertContains(resp, "scanner unavailable", status_code=503)
        self.assertEqual(Submission.objects.filter(material=self.upload).count(), 0)

    @override_settings(CLASSHUB_UPLOAD_SCAN_ENABLED=True)
    @patch("hub.views.student.scan_uploaded_file", return_value=ScanResult(status="infected", message="FOUND"))
    def test_student_upload_blocks_when_scan_detects_threat(self, _scan_mock):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.upload.id}/upload",
            {"file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes())},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Upload blocked by malware scan", status_code=400)
        self.assertEqual(Submission.objects.filter(material=self.upload).count(), 0)


class JoinClassTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Join Test", join_code="JOIN1234")

    @override_settings(
        SECRET_KEY="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        DEVICE_HINT_SIGNING_KEY="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    def test_join_prefers_device_hint_cookie_with_dedicated_key(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        hinted = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.assertLess(oldest.id, hinted.id)

        self.client.cookies["classhub_student_hint"] = signing.dumps(
            {"class_id": self.classroom.id, "student_id": hinted.id},
            key="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            salt="classhub.student-device-hint",
        )
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("student_id"), hinted.id)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "device_hint")

    @override_settings(
        SECRET_KEY="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        DEVICE_HINT_SIGNING_KEY="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    def test_join_ignores_device_hint_cookie_signed_with_wrong_key(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        hinted = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.assertLess(oldest.id, hinted.id)

        # Cookie uses the main Django secret (wrong key for device hint signing).
        self.client.cookies["classhub_student_hint"] = signing.dumps(
            {"class_id": self.classroom.id, "student_id": hinted.id},
            key="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            salt="classhub.student-device-hint",
        )
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("student_id"), oldest.id)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "name_match")

    def test_join_same_name_without_return_code_reuses_existing_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1["Cache-Control"], "no-store")
        self.assertEqual(r1["Pragma"], "no-cache")
        first_id = self.client.session.get("student_id")
        first_event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(first_event)
        self.assertEqual(first_event.event_type, StudentEvent.EVENT_CLASS_JOIN)
        self.assertEqual(first_event.ip_address, "127.0.0.0")

        # Simulate different machine/browser (no prior device cookie).
        other = Client()
        r2 = other.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        second_id = other.session.get("student_id")

        self.assertEqual(first_id, second_id)
        self.assertTrue(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        second_event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(second_event)
        self.assertEqual(second_event.event_type, StudentEvent.EVENT_REJOIN_DEVICE_HINT)
        self.assertEqual(second_event.details.get("join_mode"), "name_match")

    def test_join_same_device_without_return_code_reuses_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")

        # Student logs out, then re-joins from the same browser/device.
        self.client.get("/logout")
        r2 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")

        self.assertEqual(first_id, second_id)
        self.assertTrue(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_REJOIN_DEVICE_HINT)

    def test_join_same_device_with_different_name_creates_new_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")

        self.client.get("/logout")
        r2 = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ben"}),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")

        self.assertNotEqual(first_id, second_id)
        self.assertFalse(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 2)

    def test_join_name_match_avoids_new_row_when_duplicates_already_exist(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        StudentIdentity.objects.create(classroom=self.classroom, display_name="ADA")

        other = Client()
        resp = other.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("rejoined"))
        self.assertEqual(other.session.get("student_id"), oldest.id)
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom, display_name__iexact="ada").count(), 2)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "name_match")

    def test_join_reuses_identity_when_return_code_matches(self):
        r1 = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")
        first_code = r1.json().get("return_code")
        self.assertTrue(first_code)

        r2 = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "ada",
                    "return_code": first_code,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")
        self.assertTrue(r2.json().get("rejoined"))

        self.assertEqual(first_id, second_id)
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_REJOIN_RETURN_CODE)

    def test_join_with_invalid_return_code_is_rejected(self):
        resp = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "Ada",
                    "return_code": "ZZZZZZ",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invalid_return_code")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    def test_join_event_details_do_not_store_display_name_or_class_code(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        resp = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_CLASS_JOIN)
        self.assertNotIn("display_name", event.details)
        self.assertNotIn("class_code", event.details)
        self.assertEqual(event.details.get("join_mode"), "new")

    def test_join_rotates_session_key_and_csrf_token(self):
        # Seed an existing session + CSRF token before join.
        self.client.get("/")
        session = self.client.session
        session["prejoin_marker"] = "keep"
        session.save()
        before_session_key = session.session_key
        before_csrf = self.client.cookies["csrftoken"].value

        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        resp = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        after_session = self.client.session
        after_session_key = after_session.session_key
        after_csrf = self.client.cookies["csrftoken"].value

        self.assertNotEqual(before_session_key, after_session_key)
        self.assertNotEqual(before_csrf, after_csrf)
        self.assertEqual(after_session.get("prejoin_marker"), "keep")
        self.assertIsNotNone(after_session.get("student_id"))
        self.assertEqual(after_session.get("class_id"), self.classroom.id)

    def test_join_enforces_csrf_for_cross_site_posts(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        strict_client = Client(enforce_csrf_checks=True)

        denied = strict_client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(denied.status_code, 403)

        strict_client.get("/")
        csrf_token = strict_client.cookies["csrftoken"].value
        allowed = strict_client.post(
            "/join",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(allowed.status_code, 200)


class TeacherAuditTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="teacher_audit",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.classroom = Class.objects.create(name="Audit Class", join_code="AUD12345")

    def test_teach_toggle_lock_creates_audit_event(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(f"/teach/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 302)

        event = AuditEvent.objects.filter(action="class.toggle_lock").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.actor_user_id, self.staff.id)


class SubmissionRetentionCommandTests(TestCase):
    def setUp(self):
        classroom = Class.objects.create(name="Retention Class", join_code="RET12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")

        self.old = Submission.objects.create(
            material=material,
            student=student,
            original_filename="old.sb3",
            file=SimpleUploadedFile("old.sb3", b"old"),
        )
        self.new = Submission.objects.create(
            material=material,
            student=student,
            original_filename="new.sb3",
            file=SimpleUploadedFile("new.sb3", b"new"),
        )
        Submission.objects.filter(id=self.old.id).update(uploaded_at=timezone.now() - timedelta(days=120))

    def test_prune_submissions_dry_run_keeps_rows(self):
        call_command("prune_submissions", older_than_days=90, dry_run=True)
        self.assertEqual(Submission.objects.count(), 2)

    def test_prune_submissions_deletes_old_rows(self):
        call_command("prune_submissions", older_than_days=90)
        ids = set(Submission.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)


class StudentEventRetentionCommandTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Events Class", join_code="EVT12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.old = StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        self.new = StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            source="test",
            details={},
        )
        StudentEvent.objects.filter(id=self.old.id).update(created_at=timezone.now() - timedelta(days=120))

    def test_prune_student_events_dry_run_keeps_rows(self):
        call_command("prune_student_events", older_than_days=90, dry_run=True)
        self.assertEqual(StudentEvent.objects.count(), 2)

    def test_prune_student_events_deletes_old_rows(self):
        call_command("prune_student_events", older_than_days=90)
        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_student_events_can_export_csv_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "student_events.csv"
            call_command(
                "prune_student_events",
                older_than_days=90,
                dry_run=True,
                export_csv=str(out),
            )
            self.assertTrue(out.exists())
            with out.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(StudentEvent.objects.count(), 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["id"]), self.old.id)
        self.assertEqual(rows[0]["event_type"], StudentEvent.EVENT_CLASS_JOIN)
        self.assertEqual(rows[0]["student_display_name"], "Ada")

    def test_prune_student_events_can_export_csv_before_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "student_events.csv"
            call_command(
                "prune_student_events",
                older_than_days=90,
                export_csv=str(out),
            )
            self.assertTrue(out.exists())
            with out.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["id"]), self.old.id)


class OrphanUploadScavengerCommandTests(TestCase):
    def _build_submission(self):
        classroom = Class.objects.create(name="Orphan Class", join_code="ORP12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        Submission.objects.create(
            material=material,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )

    def test_scavenger_report_only_does_not_delete(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self._build_submission()
                orphan = Path(media_root) / "submissions/orphan.tmp"
                orphan.parent.mkdir(parents=True, exist_ok=True)
                orphan.write_bytes(b"orphan")
                self.assertTrue(orphan.exists())

                out = StringIO()
                call_command("scavenge_orphan_uploads", stdout=out)
                output = out.getvalue()

                self.assertIn("Orphan files: 1", output)
                self.assertTrue(orphan.exists())

    def test_scavenger_delete_removes_orphan(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self._build_submission()
                orphan = Path(media_root) / "lesson_assets/orphan.pdf"
                orphan.parent.mkdir(parents=True, exist_ok=True)
                orphan.write_bytes(b"orphan")
                self.assertTrue(orphan.exists())

                out = StringIO()
                call_command("scavenge_orphan_uploads", delete=True, stdout=out)
                output = out.getvalue()

                self.assertIn("Deleted orphan files: 1", output)
                self.assertFalse(orphan.exists())


class StudentEventSubmissionTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Uploads Class", join_code="UPL12345")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.material = Material.objects.create(
            module=self.module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_material_upload_emits_student_event(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
                "note": "done",
            },
        )
        self.assertEqual(resp.status_code, 302)

        event = StudentEvent.objects.filter(event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.student_id, self.student.id)
        self.assertEqual(int(event.details.get("material_id") or 0), self.material.id)

        submission = Submission.objects.filter(material=self.material, student=self.student).order_by("-id").first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.original_filename, "project.sb3")
        stored_name = Path(submission.file.name).name
        self.assertNotEqual(stored_name, "project.sb3")
        self.assertTrue(re.match(r"^[a-f0-9]{32}\.sb3$", stored_name))

    def test_material_upload_rejects_invalid_sb3_content(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", b"not-a-zip"),
                "note": "bad",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "does not match .sb3", status_code=400)
        self.assertEqual(Submission.objects.filter(material=self.material, student=self.student).count(), 0)


class SubmissionDownloadHardeningTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Download Class", join_code="DL123456")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.material = Material.objects.create(
            module=self.module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.submission = Submission.objects.create(
            material=self.material,
            student=self.student,
            original_filename="../bad\r\nname<script>.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
        )

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_submission_download_sets_hardening_headers(self):
        self._login_student()
        resp = self.client.get(f"/submission/{self.submission.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'none'; sandbox")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")
        self.assertEqual(resp["Content-Type"], "application/octet-stream")
        self.assertIn("attachment;", resp["Content-Disposition"])

    def test_submission_download_uses_safe_content_disposition_filename(self):
        self._login_student()
        resp = self.client.get(f"/submission/{self.submission.id}/download")
        self.assertEqual(resp.status_code, 200)
        disposition = resp["Content-Disposition"]
        self.assertIn("bad_name_script_.sb3", disposition)
        self.assertNotIn("/", disposition)
        self.assertNotIn("\\", disposition)
        self.assertNotRegex(disposition, r"[\r\n]")


class FileCleanupSignalTests(TestCase):
    def _build_submission(self):
        classroom = Class.objects.create(name="Cleanup Class", join_code="CLN12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        submission = Submission.objects.create(
            material=material,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )
        return student, submission

    def test_submission_file_deleted_on_student_cascade_delete(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                student, submission = self._build_submission()
                file_path = Path(submission.file.path)
                self.assertTrue(file_path.exists())

                student.delete()

                self.assertFalse(Submission.objects.filter(id=submission.id).exists())
                self.assertFalse(file_path.exists())

    def test_submission_file_replaced_deletes_old_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                _student, submission = self._build_submission()
                old_path = Path(submission.file.path)
                self.assertTrue(old_path.exists())

                submission.file = SimpleUploadedFile("project_new.sb3", b"new")
                submission.original_filename = "project_new.sb3"
                submission.save()

                new_path = Path(submission.file.path)
                self.assertTrue(new_path.exists())
                self.assertFalse(old_path.exists())

    def test_lesson_asset_delete_removes_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                folder = LessonAssetFolder.objects.create(path="general", display_name="General")
                asset = LessonAsset.objects.create(
                    folder=folder,
                    title="Worksheet",
                    original_filename="worksheet.pdf",
                    file=SimpleUploadedFile("worksheet.pdf", b"%PDF-1.4"),
                )
                file_path = Path(asset.file.path)
                self.assertTrue(file_path.exists())

                asset.delete()
                self.assertFalse(file_path.exists())

    def test_lesson_video_delete_removes_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                video = LessonVideo.objects.create(
                    course_slug="piper_scratch_12_session",
                    lesson_slug="01-welcome-private-workflow",
                    title="Welcome video",
                    video_file=SimpleUploadedFile("welcome.mp4", b"\x00\x00\x00\x18ftypmp42"),
                )
                file_path = Path(video.video_file.path)
                self.assertTrue(file_path.exists())

                video.delete()
                self.assertFalse(file_path.exists())


class StudentPortfolioExportTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Portfolio Class", join_code="PORT1234")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.upload = Material.objects.create(
            module=self.module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.other_student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_portfolio_export_requires_student_session(self):
        resp = self.client.get("/student/portfolio-export")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")

    def test_portfolio_export_contains_student_files_and_index(self):
        Submission.objects.create(
            material=self.upload,
            student=self.student,
            original_filename="ada_project.sb3",
            file=SimpleUploadedFile("ada_project.sb3", b"ada-bytes"),
            note="My first build",
        )
        Submission.objects.create(
            material=self.upload,
            student=self.other_student,
            original_filename="ben_project.sb3",
            file=SimpleUploadedFile("ben_project.sb3", b"ben-bytes"),
            note="Other student file",
        )
        self._login_student()

        resp = self.client.get("/student/portfolio-export")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertIn("portfolio_", resp["Content-Disposition"])
        self.assertNotIn("Portfolio_Class", resp["Content-Disposition"])
        self.assertNotIn("Ada", resp["Content-Disposition"])

        archive_bytes = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
            names = archive.namelist()
            self.assertIn("index.html", names)
            file_entries = [name for name in names if name.startswith("files/")]
            self.assertEqual(len(file_entries), 1)
            self.assertIn("ada_project.sb3", file_entries[0])
            self.assertNotIn("ben_project.sb3", file_entries[0])
            index_html = archive.read("index.html").decode("utf-8")

        self.assertIn("Ada Portfolio Export", index_html)
        self.assertIn("ada_project.sb3", index_html)
        self.assertNotIn("ben_project.sb3", index_html)

    def test_portfolio_export_content_disposition_defaults_to_generic_filename(self):
        self.classroom.name = "Portfolio/Class"
        self.classroom.save(update_fields=["name"])
        self.student.display_name = "Ada\r\n../Lovelace"
        self.student.save(update_fields=["display_name"])
        self._login_student()

        resp = self.client.get("/student/portfolio-export")
        self.assertEqual(resp.status_code, 200)
        disposition = resp["Content-Disposition"]
        self.assertIn("attachment;", disposition)
        self.assertNotIn("/", disposition)
        self.assertNotIn("\\", disposition)
        self.assertNotRegex(disposition, r"[\r\n]")
        self.assertIn("portfolio_", disposition)
        self.assertNotIn("Portfolio", disposition)
        self.assertNotIn("Lovelace", disposition)

    @override_settings(CLASSHUB_PORTFOLIO_FILENAME_MODE="descriptive")
    def test_portfolio_export_can_use_descriptive_filename_mode(self):
        self.classroom.name = "Portfolio/Class"
        self.classroom.save(update_fields=["name"])
        self.student.display_name = "Ada\r\n../Lovelace"
        self.student.save(update_fields=["display_name"])
        self._login_student()

        resp = self.client.get("/student/portfolio-export")
        self.assertEqual(resp.status_code, 200)
        disposition = resp["Content-Disposition"]
        self.assertIn("attachment;", disposition)
        self.assertNotIn("/", disposition)
        self.assertNotIn("\\", disposition)
        self.assertNotRegex(disposition, r"[\r\n]")
        self.assertIn("Portfolio_Class_Ada", disposition)


class StudentDataControlsTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Data Controls Class", join_code="DATA1234")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.upload = Material.objects.create(
            module=self.module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_student_my_data_page_shows_submissions_and_no_store(self):
        Submission.objects.create(
            material=self.upload,
            student=self.student,
            original_filename="portfolio.sb3",
            file=SimpleUploadedFile("portfolio.sb3", b"demo"),
        )
        self._login_student()

        resp = self.client.get("/student/my-data")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "My submissions")
        self.assertContains(resp, "portfolio.sb3")

    def test_student_delete_work_now_clears_submissions_and_upload_events(self):
        Submission.objects.create(
            material=self.upload,
            student=self.student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"demo"),
        )
        StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            source="classhub.material_upload",
            details={"submission_id": 1},
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/student/my-data?notice="))
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 0)
        self.assertEqual(
            StudentEvent.objects.filter(student=self.student, event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD).count(),
            0,
        )

    def test_student_end_session_flushes_session_and_hint_cookie(self):
        self._login_student()
        self.client.cookies["classhub_student_hint"] = "signed-token"

        resp = self.client.post("/student/end-session")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")
        hint_cookie = resp.cookies.get("classhub_student_hint")
        self.assertIsNotNone(hint_cookie)
        self.assertEqual(hint_cookie.value, "")
        self.assertEqual(str(hint_cookie["max-age"]), "0")
        self.assertNotIn("student_id", self.client.session)
        self.assertNotIn("class_id", self.client.session)


class OperatorProfileTemplateTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Operator Profile Class", join_code="OPR12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    @override_settings(
        CLASSHUB_PRODUCT_NAME="Northside Learning Hub",
        CLASSHUB_STORAGE_LOCATION_TEXT="this server is hosted by Northside Public Schools.",
        CLASSHUB_PRIVACY_PROMISE_TEXT="No surveillance analytics. No ad-tech. No data broker sharing.",
        CLASSHUB_ADMIN_LABEL="Northside School Admin",
    )
    def test_join_and_my_data_use_operator_profile_text(self):
        join_resp = self.client.get("/")
        self.assertEqual(join_resp.status_code, 200)
        self.assertContains(join_resp, "this server is hosted by Northside Public Schools.")
        self.assertContains(join_resp, "No surveillance analytics. No ad-tech. No data broker sharing.")

        self._login_student()
        my_data_resp = self.client.get("/student/my-data")
        self.assertEqual(my_data_resp.status_code, 200)
        self.assertContains(my_data_resp, "this server is hosted by Northside Public Schools.")
        self.assertContains(my_data_resp, "No surveillance analytics. No ad-tech. No data broker sharing.")

        admin_login_resp = self.client.get("/admin/login/")
        self.assertEqual(admin_login_resp.status_code, 200)
        self.assertContains(admin_login_resp, "Northside School Admin Login")


class LessonAssetDownloadTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Asset Class", join_code="AST12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.folder = LessonAssetFolder.objects.create(path="general", display_name="General")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_html_asset_forces_download_attachment(self):
        asset = LessonAsset.objects.create(
            folder=self.folder,
            title="Unsafe HTML",
            original_filename="demo.html",
            file=SimpleUploadedFile("demo.html", b"<html><script>alert(1)</script></html>"),
        )
        self._login_student()

        resp = self.client.get(f"/lesson-asset/{asset.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("Content-Security-Policy", resp)

    def test_image_asset_allows_inline_with_sandbox_header(self):
        asset = LessonAsset.objects.create(
            folder=self.folder,
            title="Diagram",
            original_filename="diagram.png",
            file=SimpleUploadedFile("diagram.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"),
        )
        self._login_student()

        resp = self.client.get(f"/lesson-asset/{asset.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inline;", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Content-Security-Policy"], "sandbox; default-src 'none'")

    def test_svg_asset_forces_download_attachment(self):
        asset = LessonAsset.objects.create(
            folder=self.folder,
            title="Unsafe SVG",
            original_filename="diagram.svg",
            file=SimpleUploadedFile("diagram.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"),
        )
        self._login_student()

        resp = self.client.get(f"/lesson-asset/{asset.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("Content-Security-Policy", resp)


class ClassHubSecurityHeaderTests(TestCase):
    @override_settings(
        CSP_POLICY="default-src 'self'",
        CSP_REPORT_ONLY_POLICY="default-src 'self'; report-uri /__csp-report__",
        PERMISSIONS_POLICY="camera=(), microphone=()",
        SECURITY_REFERRER_POLICY="strict-origin-when-cross-origin",
        X_FRAME_OPTIONS="DENY",
    )
    def test_healthz_sets_security_headers(self):
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'self'")
        self.assertEqual(resp["Content-Security-Policy-Report-Only"], "default-src 'self'; report-uri /__csp-report__")
        self.assertEqual(resp["Permissions-Policy"], "camera=(), microphone=()")
        self.assertEqual(resp["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(resp["X-Frame-Options"], "DENY")


class ClassHubCSPModeTests(TestCase):
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
        resp = self.client.get("/healthz")
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
        resp = self.client.get("/healthz")
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
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Security-Policy"], self._STRICT_POLICY)
        self.assertNotIn("Content-Security-Policy-Report-Only", resp)


class ClassHubSiteModeTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Mode Class", join_code="MODE1234")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.upload = Material.objects.create(
            module=self.module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    @override_settings(SITE_MODE="read-only")
    def test_read_only_blocks_submission_upload(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.upload.id}/upload",
            {"file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes())},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertContains(resp, "read-only mode", status_code=503)
        self.assertEqual(resp["Cache-Control"], "no-store")

    @override_settings(SITE_MODE="join-only")
    def test_join_only_allows_join_endpoint(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "New Student"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))

    @override_settings(SITE_MODE="join-only")
    def test_join_only_blocks_teacher_portal_route(self):
        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 503)
        self.assertContains(resp, "join-only mode", status_code=503)

    @override_settings(SITE_MODE="maintenance")
    def test_maintenance_blocks_student_home(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 503)
        self.assertContains(resp, "maintenance mode", status_code=503)


class InternalHelperEventEndpointTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Internal Event Class", join_code="INT12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.url = "/internal/events/helper-chat-access"
        self.token = "internal-event-token-12345"

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="")
    def test_internal_event_endpoint_returns_503_without_configured_token(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"classroom_id": self.classroom.id, "student_id": self.student.id}),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN=self.token,
        )
        self.assertEqual(resp.status_code, 503)

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="expected-token")
    def test_internal_event_endpoint_rejects_invalid_token(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"classroom_id": self.classroom.id, "student_id": self.student.id}),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN="wrong-token",
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="expected-token")
    def test_internal_event_endpoint_appends_student_event(self):
        payload = {
            "classroom_id": self.classroom.id,
            "student_id": self.student.id,
            "ip_address": "127.0.0.1",
            "details": {"request_id": "req-123", "actor_type": "student"},
        }
        resp = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN="expected-token",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))

        event = StudentEvent.objects.filter(event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.student_id, self.student.id)
        self.assertEqual(event.source, "homework_helper.chat")
        self.assertEqual(event.ip_address, "127.0.0.0")
        self.assertEqual(event.details.get("request_id"), "req-123")
        self.assertEqual(event.details.get("actor_type"), "student")

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="expected-token", CLASSHUB_STUDENT_EVENT_IP_MODE="full")
    def test_internal_event_endpoint_can_store_full_ip_when_enabled(self):
        payload = {
            "classroom_id": self.classroom.id,
            "student_id": self.student.id,
            "ip_address": "127.0.0.1",
            "details": {"request_id": "req-full", "actor_type": "student"},
        }
        resp = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN="expected-token",
        )
        self.assertEqual(resp.status_code, 200)
        event = StudentEvent.objects.filter(event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.ip_address, "127.0.0.1")

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="expected-token")
    def test_internal_event_endpoint_drops_unallowlisted_details(self):
        payload = {
            "classroom_id": self.classroom.id,
            "student_id": self.student.id,
            "details": {
                "request_id": "req-789",
                "actor_type": "student",
                "backend": "ollama",
                "attempts": 2,
                "scope_verified": True,
                "truncated": False,
                "display_name": "Ada",
                "class_code": "JOIN1234",
                "prompt": "my name is Ada",
                "filename": "secret.txt",
            },
        }
        resp = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN="expected-token",
        )
        self.assertEqual(resp.status_code, 200)
        event = StudentEvent.objects.filter(event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(
            event.details,
            {
                "request_id": "req-789",
                "actor_type": "student",
                "backend": "ollama",
                "attempts": 2,
                "scope_verified": True,
                "truncated": False,
            },
        )
        self.assertNotIn("display_name", event.details)
        self.assertNotIn("class_code", event.details)
        self.assertNotIn("prompt", event.details)
        self.assertNotIn("filename", event.details)

    @override_settings(CLASSHUB_INTERNAL_EVENTS_TOKEN="expected-token")
    def test_internal_event_endpoint_skips_when_payload_has_no_actor(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"details": {"request_id": "req-123"}}),
            content_type="application/json",
            HTTP_X_CLASSHUB_INTERNAL_TOKEN="expected-token",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("skipped"), "no_actor")
        self.assertFalse(
            StudentEvent.objects.filter(event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS).exists()
        )
