from ._shared import *  # noqa: F401,F403

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

    @override_settings(HELPER_SCOPE_SIGNING_KEY="scope-signing-key-cccccccccccccccccccccccccccccccc")
    def test_student_helper_scope_token_uses_dedicated_signing_key(self):
        self._login_student()

        resp = self.client.get("/course/piper_scratch_12_session/s01-welcome-private-workflow")
        self.assertEqual(resp.status_code, 200)
        token_match = re.search(r'data-helper-scope-token="([^"]+)"', resp.content.decode("utf-8"))
        self.assertIsNotNone(token_match)
        token = token_match.group(1)

        with self.assertRaises(signing.BadSignature):
            parse_scope_token(
                token,
                max_age_seconds=3600,
                signing_key="wrong-signing-key-dddddddddddddddddddddddddddddd",
            )

        scope = parse_scope_token(
            token,
            max_age_seconds=3600,
            signing_key="scope-signing-key-cccccccccccccccccccccccccccccccc",
        )
        self.assertTrue(scope.get("context"))

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
        self.assertContains(resp, "/static/css/lesson_page.css")
        self.assertContains(resp, "/static/js/lesson_page.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin-top:0;"', html=False)
        self.assertNotContains(resp, "const items = Array.from(document.querySelectorAll('.video-item'))", html=False)
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

    def test_student_home_landing_highlights_this_weeks_lesson(self):
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            available_on=timezone.localdate(),
        )
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "highlighted lesson")
        self.assertContains(resp, "Start this")
        self.assertContains(resp, "Session 1")
        self.assertContains(resp, "View full course lesson links")

    def test_student_home_compact_mode_shows_single_my_data_link(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Open My Data")
        self.assertNotContains(resp, "End my session on this device")

    def test_course_overview_uses_external_css_without_inline_styles(self):
        self._login_student()

        resp = self.client.get("/course/piper_scratch_12_session")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/course_overview.css")
        self.assertContains(resp, "ui-density-compact")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

    @override_settings(CLASSHUB_PROGRAM_PROFILE="advanced")
    def test_student_home_prefers_course_ui_level_over_global_profile(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ui-density-compact")

    def test_student_home_masks_return_code_by_default(self):
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "/static/css/student_class.css")
        self.assertContains(resp, "••••••")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin-top:8px"', html=False)
        self.assertNotContains(resp, "data-secret-code=")
        self.assertContains(resp, "/static/js/student_class.js")
        self.assertNotContains(resp, "returnCodeUrl = ", html=False)
        self.assertNotContains(resp, "onsubmit=\"return confirm(", html=False)
        self.assertNotContains(resp, f">{self.student.return_code}<", html=False)
        self.assertContains(resp, "Copy return code")

    def test_student_return_code_endpoint_requires_student_session(self):
        resp = self.client.get("/student/return-code")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")

    def test_student_return_code_endpoint_returns_json_for_logged_in_student(self):
        self._login_student()

        resp = self.client.get("/student/return-code")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp.json(), {"return_code": self.student.return_code})

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

    def test_material_upload_page_uses_external_css_without_inline_styles(self):
        self._login_student()

        resp = self.client.get(f"/material/{self.upload.id}/upload")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/material_upload.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

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
