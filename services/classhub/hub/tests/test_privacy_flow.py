"""E2E tests for the privacy page and student delete-work flow."""

from ._shared import *  # noqa: F401,F403


class PrivacyPageTests(TestCase):
    def test_privacy_page_renders_for_anonymous_visitor(self):
        resp = self.client.get("/privacy")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Privacy")

    def test_privacy_page_contains_retention_and_deletion_info(self):
        resp = self.client.get("/privacy")
        self.assertEqual(resp.status_code, 200)
        # Should mention data deletion or controls
        self.assertContains(resp, "delete", status_code=200)


class StudentDeleteWorkTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Privacy Class", join_code="PRV12345")
        self.module = Module.objects.create(
            classroom=self.classroom, title="Session 1", order_index=0
        )
        self.material = Material.objects.create(
            module=self.module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ada"
        )

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_delete_work_requires_post(self):
        self._login_student()
        resp = self.client.get("/student/delete-work")
        self.assertEqual(resp.status_code, 405)

    def test_delete_work_redirects_unauthenticated_student(self):
        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/", resp["Location"])

    def test_delete_work_removes_submissions(self):
        self._login_student()

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                Submission.objects.create(
                    material=self.material,
                    student=self.student,
                    original_filename="project.sb3",
                    file=SimpleUploadedFile("project.sb3", b"dummy"),
                )
                self.assertEqual(
                    Submission.objects.filter(student=self.student).count(), 1
                )

                resp = self.client.post("/student/delete-work")
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/student/my-data", resp["Location"])

                # Submissions should be gone
                self.assertEqual(
                    Submission.objects.filter(student=self.student).count(), 0
                )

    def test_delete_work_removes_material_responses(self):
        self._login_student()

        reflection = Material.objects.create(
            module=self.module,
            title="Reflection",
            type=Material.TYPE_REFLECTION,
            body="What did you learn?",
            order_index=1,
        )
        StudentMaterialResponse.objects.create(
            student=self.student,
            material=reflection,
            reflection_text="I learned a lot!",
        )
        self.assertEqual(
            StudentMaterialResponse.objects.filter(student=self.student).count(), 1
        )

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)

        # Material responses should be gone
        self.assertEqual(
            StudentMaterialResponse.objects.filter(student=self.student).count(), 0
        )

    def test_delete_work_removes_upload_events(self):
        self._login_student()

        StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            source="test",
            details={"material_id": self.material.id},
        )
        self.assertEqual(
            StudentEvent.objects.filter(
                student=self.student,
                event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            ).count(),
            1,
        )

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)

        # Upload events should be gone
        self.assertEqual(
            StudentEvent.objects.filter(
                student=self.student,
                event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            ).count(),
            0,
        )

    def test_delete_work_does_not_remove_other_students_data(self):
        self._login_student()

        other_student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ben"
        )
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                Submission.objects.create(
                    material=self.material,
                    student=self.student,
                    original_filename="ada_project.sb3",
                    file=SimpleUploadedFile("ada_project.sb3", b"ada"),
                )
                Submission.objects.create(
                    material=self.material,
                    student=other_student,
                    original_filename="ben_project.sb3",
                    file=SimpleUploadedFile("ben_project.sb3", b"ben"),
                )
                self.assertEqual(Submission.objects.count(), 2)

                resp = self.client.post("/student/delete-work")
                self.assertEqual(resp.status_code, 302)

                # Only Ada's submission should be gone; Ben's should remain
                self.assertEqual(Submission.objects.count(), 1)
                remaining = Submission.objects.first()
                self.assertEqual(remaining.student_id, other_student.id)

    def test_delete_work_notice_message_in_redirect(self):
        self._login_student()

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                Submission.objects.create(
                    material=self.material,
                    student=self.student,
                    original_filename="project.sb3",
                    file=SimpleUploadedFile("project.sb3", b"dummy"),
                )

                resp = self.client.post("/student/delete-work")
                self.assertEqual(resp.status_code, 302)
                self.assertIn("notice=", resp["Location"])
                self.assertIn("Deleted", resp["Location"])
