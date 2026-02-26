from ._shared import *  # noqa: F401,F403

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
                "intent": "debug",
                "attempts": 2,
                "follow_up_suggestions_count": 3,
                "conversation_compacted": True,
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
                "intent": "debug",
                "attempts": 2,
                "follow_up_suggestions_count": 3,
                "conversation_compacted": True,
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
