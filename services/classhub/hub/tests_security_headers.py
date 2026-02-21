import json
import zipfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Class, LessonAsset, LessonAssetFolder, Material, Module, StudentIdentity, Submission


def _sample_sb3_bytes() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", '{"targets":[],"meta":{"semver":"3.0.0"}}')
    return buf.getvalue()


def _force_login_staff_verified(client: Client, user) -> None:
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


class SecurityHeaderDriftTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Header Class", join_code="HDR12345")
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
        self.submission = Submission.objects.create(
            material=self.upload,
            student=self.student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
        )
        self.folder = LessonAssetFolder.objects.create(path="general", display_name="General")
        self.asset = LessonAsset.objects.create(
            folder=self.folder,
            title="Diagram",
            original_filename="diagram.png",
            file=SimpleUploadedFile("diagram.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"),
        )
        self.staff = get_user_model().objects.create_user(
            username="teacher_headers",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

    def _login_student(self) -> None:
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_join_post_uses_no_store_cache(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "no-store")
        self.assertEqual(resp["Pragma"], "no-cache")

    def test_student_and_teacher_pages_use_private_no_store(self):
        self._login_student()
        student_resp = self.client.get("/student")
        self.assertEqual(student_resp.status_code, 200)
        self.assertEqual(student_resp["Cache-Control"], "private, no-store")

        _force_login_staff_verified(self.client, self.staff)
        teacher_resp = self.client.get(f"/teach/class/{self.classroom.id}")
        self.assertEqual(teacher_resp.status_code, 200)
        self.assertEqual(teacher_resp["Cache-Control"], "private, no-store")

    def test_submission_download_has_uniform_safety_headers(self):
        self._login_student()
        resp = self.client.get(f"/submission/{self.submission.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'none'; sandbox")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")

    def test_portfolio_export_has_uniform_safety_headers(self):
        self._login_student()
        resp = self.client.get("/student/portfolio-export")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'none'; sandbox")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")

    def test_inline_lesson_asset_uses_private_short_cache(self):
        self._login_student()
        resp = self.client.get(f"/lesson-asset/{self.asset.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("inline;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, max-age=60")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
