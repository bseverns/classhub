"""Tests for the headless student API endpoints."""

from ._shared import *  # noqa: F401,F403


class _StudentAPIBase(TestCase):
    """Common setUp for all student API tests."""

    def setUp(self):
        self.classroom = Class.objects.create(
            name="API Test Class", join_code="API12345", session_epoch=1,
        )
        self.module = Module.objects.create(
            classroom=self.classroom, title="Session 1", order_index=0,
        )
        self.material = Material.objects.create(
            module=self.module, title="Upload your project",
            type=Material.TYPE_UPLOAD, accepted_extensions=".sb3",
            max_upload_mb=50, order_index=0,
        )
        self.student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ada",
        )

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session["class_epoch"] = 1
        session.save()


class StudentSessionEndpointTests(_StudentAPIBase):
    """Tests for GET /api/v1/student/session."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/v1/student/session")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "unauthorized")

    def test_authenticated_returns_200_with_correct_shape(self):
        self._login_student()
        resp = self.client.get("/api/v1/student/session")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("classroom", data)
        self.assertIn("student", data)
        self.assertIn("privacy_meta", data)
        self.assertEqual(data["classroom"]["id"], self.classroom.id)
        self.assertEqual(data["classroom"]["name"], "API Test Class")
        self.assertEqual(data["student"]["id"], self.student.id)
        self.assertEqual(data["student"]["display_name"], "Ada")
        self.assertIn("return_code", data["student"])

    def test_session_updates_last_seen_at(self):
        self._login_student()
        self.assertIsNone(self.student.last_seen_at)
        self.client.get("/api/v1/student/session")
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.last_seen_at)

    def test_only_get_allowed(self):
        self._login_student()
        resp = self.client.post("/api/v1/student/session")
        self.assertEqual(resp.status_code, 405)


class StudentModulesEndpointTests(_StudentAPIBase):
    """Tests for GET /api/v1/student/modules."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/v1/student/modules")
        self.assertEqual(resp.status_code, 401)

    def test_returns_modules_with_materials(self):
        self._login_student()
        resp = self.client.get("/api/v1/student/modules")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("modules", data)
        self.assertIn("ui_density_mode", data)
        modules = data["modules"]
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["title"], "Session 1")
        self.assertEqual(len(modules[0]["materials"]), 1)
        mat = modules[0]["materials"][0]
        self.assertEqual(mat["title"], "Upload your project")
        self.assertEqual(mat["type"], Material.TYPE_UPLOAD)

    def test_empty_classroom_returns_empty_modules(self):
        empty_class = Class.objects.create(name="Empty", join_code="EMP12345")
        empty_student = StudentIdentity.objects.create(
            classroom=empty_class, display_name="Bob",
        )
        session = self.client.session
        session["student_id"] = empty_student.id
        session["class_id"] = empty_class.id
        session["class_epoch"] = 1
        session.save()
        resp = self.client.get("/api/v1/student/modules")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["modules"]), 0)


class StudentSubmissionsEndpointTests(_StudentAPIBase):
    """Tests for GET /api/v1/student/submissions."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/v1/student/submissions")
        self.assertEqual(resp.status_code, 401)

    def test_returns_empty_submissions_for_new_student(self):
        self._login_student()
        resp = self.client.get("/api/v1/student/submissions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["submissions"]), 0)
        self.assertEqual(data["pagination"]["total"], 0)

    def test_returns_submissions_with_pagination_metadata(self):
        self._login_student()
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                for i in range(3):
                    Submission.objects.create(
                        material=self.material, student=self.student,
                        original_filename=f"project_{i}.sb3",
                        file=SimpleUploadedFile(f"project_{i}.sb3", b"data"),
                    )
                resp = self.client.get("/api/v1/student/submissions")
                data = resp.json()
                self.assertEqual(len(data["submissions"]), 3)
                self.assertEqual(data["pagination"]["total"], 3)
                self.assertEqual(data["pagination"]["limit"], 50)
                self.assertEqual(data["pagination"]["offset"], 0)

    def test_pagination_limit_and_offset(self):
        self._login_student()
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                for i in range(5):
                    Submission.objects.create(
                        material=self.material, student=self.student,
                        original_filename=f"project_{i}.sb3",
                        file=SimpleUploadedFile(f"project_{i}.sb3", b"data"),
                    )
                resp = self.client.get("/api/v1/student/submissions?limit=2&offset=1")
                data = resp.json()
                self.assertEqual(len(data["submissions"]), 2)
                self.assertEqual(data["pagination"]["total"], 5)
                self.assertEqual(data["pagination"]["limit"], 2)
                self.assertEqual(data["pagination"]["offset"], 1)

    def test_pagination_limit_capped_at_100(self):
        self._login_student()
        resp = self.client.get("/api/v1/student/submissions?limit=999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pagination"]["limit"], 100)

    def test_cross_student_isolation(self):
        """A student should not see another student's submissions."""
        self._login_student()
        other_student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ben",
        )
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                Submission.objects.create(
                    material=self.material, student=other_student,
                    original_filename="ben_project.sb3",
                    file=SimpleUploadedFile("ben_project.sb3", b"data"),
                )
                resp = self.client.get("/api/v1/student/submissions")
                data = resp.json()
                self.assertEqual(len(data["submissions"]), 0)
                self.assertEqual(data["pagination"]["total"], 0)
