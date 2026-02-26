from ._shared import *  # noqa: F401,F403

class RetentionSettingParsingTests(SimpleTestCase):
    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS=0, CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=0)
    def test_retention_days_preserves_explicit_zero(self):
        from ..views.content import _retention_days as content_retention_days
        from ..views.student import _retention_days as student_retention_days

        self.assertEqual(student_retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90), 0)
        self.assertEqual(content_retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180), 0)

    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS="bad", CLASSHUB_STUDENT_EVENT_RETENTION_DAYS="bad")
    def test_retention_days_falls_back_to_default_on_invalid_values(self):
        from ..views.content import _retention_days as content_retention_days
        from ..views.student import _retention_days as student_retention_days

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

    def test_teach_login_page_uses_external_css_without_inline_styles(self):
        resp = self.client.get("/teach/login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_login.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin-bottom: 20px;"', html=False)

    def test_teach_lessons_shows_submission_progress(self):
        classroom, upload = self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/lessons?class_id={classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_lessons.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)
        self.assertContains(resp, "Session 1 lesson")
        self.assertContains(resp, "Submitted 1 / 2")
        self.assertContains(resp, "Review missing now (1)")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions?show=missing")
        self.assertContains(resp, f"/teach/material/{upload.id}/submissions?download=zip_latest")

    def test_teach_material_submissions_page_uses_external_css_without_inline_styles(self):
        classroom, upload = self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/material/{upload.id}/submissions")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_material_submissions.css")
        self.assertContains(resp, classroom.name)
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="text-decoration-thickness:2px;"', html=False)

    def test_teach_home_shows_recent_submissions(self):
        self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_home.css")
        self.assertContains(resp, "/static/js/teach_home.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0 0 10px 0"', html=False)
        self.assertNotContains(resp, "const tabRoot = document.querySelector", html=False)
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
        self.assertContains(resp, "/static/css/teach_join_card.css")
        self.assertContains(resp, "Student Join Card")
        self.assertContains(resp, "JOIN7788")
        self.assertContains(resp, "/?class_code=JOIN7788")
        self.assertContains(resp, "/static/js/teach_join_card.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, "onclick=\"window.print()\"", html=False)
        self.assertNotContains(resp, "Copied class code.", html=False)

    def test_teach_class_masks_return_codes_by_default(self):
        classroom = Class.objects.create(name="Period Roster", join_code="MASK1234")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertContains(resp, "/static/css/teach_class.css")
        self.assertContains(resp, "••••••")
        self.assertNotContains(resp, "data-secret-code=")
        self.assertContains(resp, "/static/js/teach_class.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0 0 12px 0;"', html=False)
        self.assertNotContains(resp, "returnCodeBaseUrl = ", html=False)
        self.assertNotContains(resp, "onsubmit=\"return confirm(", html=False)
        self.assertNotContains(resp, f">{student.return_code}<", html=False)
        self.assertContains(resp, "Show")

    def test_teach_student_return_code_requires_staff(self):
        classroom = Class.objects.create(name="Period Roster", join_code="MASK1234")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")

        resp = self.client.get(f"/teach/class/{classroom.id}/student/{student.id}/return-code")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/login", resp["Location"])

    def test_teach_student_return_code_returns_json_for_staff(self):
        classroom = Class.objects.create(name="Period Roster", join_code="MASK1234")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/student/{student.id}/return-code")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp.json(), {"return_code": student.return_code})

    def test_teach_student_return_code_enforces_class_scope(self):
        classroom = Class.objects.create(name="Period Roster", join_code="MASK1234")
        other_class = Class.objects.create(name="Other", join_code="OTHR1234")
        student = StudentIdentity.objects.create(classroom=other_class, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/student/{student.id}/return-code")
        self.assertEqual(resp.status_code, 404)

    def test_teach_module_uses_external_css_without_inline_styles(self):
        classroom = Class.objects.create(name="Period Module", join_code="MOD12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        Material.objects.create(
            module=module,
            title="Intro notes",
            type=Material.TYPE_TEXT,
            body="Welcome to session one.",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/module/{module.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_module.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

    def test_teach_videos_uses_external_css_without_inline_styles(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach/videos")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_videos.css")
        self.assertContains(resp, "Lesson Videos")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

    def test_teach_assets_uses_external_css_without_inline_styles(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach/assets")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_assets.css")
        self.assertContains(resp, "Lesson Assets")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

    def test_teach_class_shows_helper_signal_panel(self):
        classroom = Class.objects.create(name="Period Signals", join_code="SIG12345")
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        ben = StudentIdentity.objects.create(classroom=classroom, display_name="Ben")
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="homework_helper.chat",
            details={
                "request_id": "req-1",
                "intent": "debug",
                "follow_up_suggestions_count": 2,
                "conversation_compacted": True,
            },
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="homework_helper.chat",
            details={
                "request_id": "req-2",
                "intent": "debug",
                "follow_up_suggestions_count": 1,
                "conversation_compacted": False,
            },
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ben,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="homework_helper.chat",
            details={
                "request_id": "req-3",
                "intent": "concept",
                "follow_up_suggestions_count": 3,
                "conversation_compacted": False,
            },
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Helper Signals")
        self.assertContains(resp, "3 helper chats")
        self.assertContains(resp, "debug")
        self.assertContains(resp, "concept")
        self.assertContains(resp, "Ada")
        self.assertContains(resp, "2 chats")

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
        reset_mock.return_value = HelperResetResult(
            ok=True,
            deleted_conversations=4,
            archived_conversations=4,
            archive_path="/uploads/helper_reset_exports/sample.json",
            status_code=200,
        )

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
        self.assertEqual(event.metadata.get("archived_conversations"), 4)
        self.assertEqual(event.metadata.get("archive_path"), "/uploads/helper_reset_exports/sample.json")

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

    def test_course_overview_uses_external_css_without_inline_styles(self):
        self._login_student()

        resp = self.client.get("/course/piper_scratch_12_session")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/course_overview.css")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)

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


