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

    def test_empty_material_set_short_circuits_submission_queries(self):
        self.material.delete()
        self._login_student()

        with CaptureQueriesContext(connection) as capture:
            resp = self.client.get("/api/v1/student/submissions")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["submissions"], [])
        self.assertEqual(data["submissions_by_material"], {})
        self.assertEqual(data["material_responses"], {})
        self.assertEqual(data["gallery_entries_by_material"], {})
        self.assertEqual(data["pagination"]["total"], 0)
        self.assertFalse(any("hub_submission" in q["sql"].lower() for q in capture.captured_queries))

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


class StudentCsrfEndpointTests(_StudentAPIBase):
    """Tests for GET /api/v1/student/csrf."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/v1/student/csrf")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "unauthorized")

    def test_authenticated_returns_token(self):
        self._login_student()
        resp = self.client.get("/api/v1/student/csrf")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrf_token", resp.json())
        self.assertTrue(str(resp.json()["csrf_token"]).strip())


class StudentUploadEndpointTests(_StudentAPIBase):
    """Tests for POST /api/v1/student/material/<id>/upload."""

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(f"/api/v1/student/material/{self.material.id}/upload")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "unauthorized")

    def test_cross_class_material_returns_not_found(self):
        self._login_student()
        other_class = Class.objects.create(name="Other", join_code="OTH12345")
        other_module = Module.objects.create(classroom=other_class, title="Other Module", order_index=0)
        other_material = Material.objects.create(
            module=other_module,
            title="Other Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=5,
            order_index=0,
        )
        resp = self.client.post(f"/api/v1/student/material/{other_material.id}/upload")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "not_found")

    def test_non_upload_material_returns_not_upload_material(self):
        self._login_student()
        link_material = Material.objects.create(
            module=self.module, title="Read first", type=Material.TYPE_LINK, url="/x", order_index=1,
        )
        resp = self.client.post(f"/api/v1/student/material/{link_material.id}/upload")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "not_upload_material")

    def test_invalid_form_returns_400(self):
        self._login_student()
        resp = self.client.post(f"/api/v1/student/material/{self.material.id}/upload")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "invalid_form")

    @patch("hub.views.api_student_upload.scan_uploaded_file", return_value=ScanResult(status="clean", message=""))
    def test_upload_success_returns_ok_and_creates_submission(self, _scan_mock):
        self._login_student()
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                upload = SimpleUploadedFile("project.sb3", _sample_sb3_bytes(), content_type="application/octet-stream")
                resp = self.client.post(
                    f"/api/v1/student/material/{self.material.id}/upload",
                    {"file": upload},
                )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["material_id"], self.material.id)
        self.assertIn(f"/material/{self.material.id}/upload", payload["redirect_url"])
        self.assertEqual(Submission.objects.filter(material=self.material, student=self.student).count(), 1)

    @patch("hub.views.api_student_upload.process_material_upload_form", side_effect=RuntimeError("boom"))
    def test_internal_upload_error_returns_non_retryable_json(self, _upload_mock):
        self._login_student()
        upload = SimpleUploadedFile("project.sb3", _sample_sb3_bytes(), content_type="application/octet-stream")
        resp = self.client.post(
            f"/api/v1/student/material/{self.material.id}/upload",
            {"file": upload},
        )
        self.assertEqual(resp.status_code, 500)
        payload = resp.json()
        self.assertEqual(payload["error"], "upload_internal_error")
        self.assertFalse(payload["retry"])
        self.assertIn("temporarily unavailable", payload["message"])


class StudentUploadSyncWorkerEndpointTests(TestCase):
    """Tests for GET /student-upload-sync-sw.js."""

    def test_service_worker_endpoint_returns_javascript_with_root_scope(self):
        resp = self.client.get("/student-upload-sync-sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp["Content-Type"])
        self.assertEqual(resp["Service-Worker-Allowed"], "/")
        self.assertIn("no-store", (resp.get("Cache-Control") or "").lower())

    def test_student_shell_manifest_returns_installable_json(self):
        resp = self.client.get("/student-shell.webmanifest")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/manifest+json", resp.get("Content-Type", ""))
        payload = resp.json()
        self.assertEqual(payload.get("start_url"), "/?kiosk=1")
        self.assertEqual(payload.get("display"), "standalone")
        icons = payload.get("icons") or []
        self.assertTrue(any("student-kiosk-192.svg" in str(icon.get("src", "")) for icon in icons))
