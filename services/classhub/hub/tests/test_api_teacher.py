"""Tests for the headless teacher API endpoints (read and write)."""

from ._shared import *  # noqa: F401,F403

User = get_user_model()


class _TeacherAPIBase(TestCase):
    """Common setUp for teacher API tests."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher1", password="testpass123", is_staff=True,
        )
        self.classroom = Class.objects.create(
            name="Teacher API Class", join_code="TCH12345", session_epoch=1,
        )
        self.module = Module.objects.create(
            classroom=self.classroom, title="Session 1", order_index=0,
        )
        self.material = Material.objects.create(
            module=self.module, title="Upload task",
            type=Material.TYPE_UPLOAD, accepted_extensions=".sb3",
            max_upload_mb=50, order_index=0,
        )
        self.student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ada",
        )

    def _login_teacher(self):
        _force_login_staff_verified(self.client, self.teacher)


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


class TeacherClassesEndpointTests(_TeacherAPIBase):
    """Tests for GET /api/v1/teacher/classes."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/v1/teacher/classes")
        self.assertEqual(resp.status_code, 401)

    def test_non_staff_returns_401(self):
        non_staff = User.objects.create_user(
            username="regular", password="pass", is_staff=False,
        )
        self.client.force_login(non_staff)
        resp = self.client.get("/api/v1/teacher/classes")
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_staff_returns_classes(self):
        self._login_teacher()
        resp = self.client.get("/api/v1/teacher/classes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("classes", data)
        self.assertIsInstance(data["classes"], list)
        self.assertTrue(len(data["classes"]) >= 1)

    def test_class_payload_shape(self):
        self._login_teacher()
        resp = self.client.get("/api/v1/teacher/classes")
        data = resp.json()
        cls = data["classes"][0]
        self.assertIn("id", cls)
        self.assertIn("name", cls)
        self.assertIn("join_code", cls)
        self.assertIn("is_locked", cls)
        self.assertIn("student_count", cls)
        self.assertIn("submissions_24h", cls)
        self.assertIn("is_assigned", cls)

    def test_only_get_allowed(self):
        self._login_teacher()
        resp = self.client.post("/api/v1/teacher/classes")
        self.assertEqual(resp.status_code, 405)


class TeacherClassRosterEndpointTests(_TeacherAPIBase):
    """Tests for GET /api/v1/teacher/class/<id>/roster."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/roster")
        self.assertEqual(resp.status_code, 401)

    def test_nonexistent_class_returns_404(self):
        self._login_teacher()
        resp = self.client.get("/api/v1/teacher/class/99999/roster")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "not_found")

    def test_returns_roster_with_students_and_modules(self):
        self._login_teacher()
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/roster")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("classroom", data)
        self.assertIn("students", data)
        self.assertIn("modules", data)
        self.assertIn("student_count", data)
        self.assertEqual(data["classroom"]["id"], self.classroom.id)
        self.assertEqual(data["student_count"], 1)
        self.assertEqual(len(data["students"]), 1)
        self.assertEqual(data["students"][0]["display_name"], "Ada")

    def test_roster_module_contains_materials(self):
        self._login_teacher()
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/roster")
        data = resp.json()
        modules = data["modules"]
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["title"], "Session 1")
        self.assertEqual(len(modules[0]["materials"]), 1)
        self.assertEqual(modules[0]["materials"][0]["title"], "Upload task")


class TeacherClassSubmissionsEndpointTests(_TeacherAPIBase):
    """Tests for GET /api/v1/teacher/class/<id>/submissions."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/submissions")
        self.assertEqual(resp.status_code, 401)

    def test_returns_empty_submissions(self):
        self._login_teacher()
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/submissions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["submissions"]), 0)
        self.assertEqual(data["pagination"]["total"], 0)

    def test_returns_submissions_with_student_and_material_fields(self):
        self._login_teacher()
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                Submission.objects.create(
                    material=self.material, student=self.student,
                    original_filename="project.sb3",
                    file=SimpleUploadedFile("project.sb3", b"data"),
                )
                resp = self.client.get(
                    f"/api/v1/teacher/class/{self.classroom.id}/submissions"
                )
                data = resp.json()
                self.assertEqual(len(data["submissions"]), 1)
                sub = data["submissions"][0]
                self.assertIn("student", sub)
                self.assertEqual(sub["student"]["display_name"], "Ada")
                self.assertIn("material", sub)
                self.assertEqual(sub["material"]["title"], "Upload task")

    def test_pagination_works(self):
        self._login_teacher()
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                for i in range(5):
                    Submission.objects.create(
                        material=self.material, student=self.student,
                        original_filename=f"p{i}.sb3",
                        file=SimpleUploadedFile(f"p{i}.sb3", b"data"),
                    )
                resp = self.client.get(
                    f"/api/v1/teacher/class/{self.classroom.id}/submissions?limit=2&offset=1"
                )
                data = resp.json()
                self.assertEqual(len(data["submissions"]), 2)
                self.assertEqual(data["pagination"]["total"], 5)
                self.assertEqual(data["pagination"]["limit"], 2)
                self.assertEqual(data["pagination"]["offset"], 1)


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------


class TeacherToggleLockEndpointTests(_TeacherAPIBase):
    """Tests for POST /api/v1/teacher/class/<id>/toggle-lock."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 401)

    def test_get_method_not_allowed(self):
        self._login_teacher()
        resp = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 405)

    def test_toggles_lock_on(self):
        self._login_teacher()
        self.assertFalse(self.classroom.is_locked)
        resp = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_locked"])
        self.classroom.refresh_from_db()
        self.assertTrue(self.classroom.is_locked)

    def test_toggles_lock_off(self):
        self._login_teacher()
        self.classroom.is_locked = True
        self.classroom.save(update_fields=["is_locked"])
        resp = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_locked"])
        self.classroom.refresh_from_db()
        self.assertFalse(self.classroom.is_locked)

    def test_creates_audit_event(self):
        self._login_teacher()
        self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        audit = AuditEvent.objects.filter(action="class.toggle_lock").first()
        self.assertIsNotNone(audit)

    def test_nonexistent_class_returns_404(self):
        self._login_teacher()
        resp = self.client.post("/api/v1/teacher/class/99999/toggle-lock")
        self.assertEqual(resp.status_code, 404)


class TeacherRotateCodeEndpointTests(_TeacherAPIBase):
    """Tests for POST /api/v1/teacher/class/<id>/rotate-code."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/rotate-code")
        self.assertEqual(resp.status_code, 401)

    def test_rotates_join_code(self):
        self._login_teacher()
        old_code = self.classroom.join_code
        resp = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/rotate-code")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotEqual(data["join_code"], old_code)
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.join_code, data["join_code"])

    def test_creates_audit_event(self):
        self._login_teacher()
        self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/rotate-code")
        audit = AuditEvent.objects.filter(action="class.rotate_code").first()
        self.assertIsNotNone(audit)


class TeacherSetEnrollmentModeEndpointTests(_TeacherAPIBase):
    """Tests for POST /api/v1/teacher/class/<id>/set-enrollment-mode."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode"
        )
        self.assertEqual(resp.status_code, 401)

    def test_sets_enrollment_mode_via_json(self):
        self._login_teacher()
        resp = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["enrollment_mode"], "closed")
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.enrollment_mode, "closed")

    def test_sets_enrollment_mode_via_form_post(self):
        self._login_teacher()
        resp = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data={"enrollment_mode": "invite_only"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["enrollment_mode"], "invite_only")

    def test_invalid_mode_returns_400(self):
        self._login_teacher()
        resp = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "bogus"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["error"], "invalid_enrollment_mode")
        self.assertIn("valid_modes", data)

    def test_creates_audit_event(self):
        self._login_teacher()
        self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        audit = AuditEvent.objects.filter(action="class.set_enrollment_mode").first()
        self.assertIsNotNone(audit)
