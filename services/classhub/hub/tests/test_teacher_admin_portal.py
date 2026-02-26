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


class TeacherRosterClassServiceTests(TestCase):
    def test_material_submission_counts_uses_distinct_student_aggregation(self):
        from ..services.teacher_roster_class import _material_submission_counts

        classroom = Class.objects.create(name="Period Svc", join_code="SVCCOUNT")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        upload = Material.objects.create(
            module=module,
            title="Upload your project file",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        student_a = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        student_b = StudentIdentity.objects.create(classroom=classroom, display_name="Ben")

        # Ada submits twice; count should still be 1 for Ada + 1 for Ben.
        Submission.objects.create(
            material=upload,
            student=student_a,
            original_filename="ada_first.sb3",
            file=SimpleUploadedFile("ada_first.sb3", b"first"),
        )
        Submission.objects.create(
            material=upload,
            student=student_a,
            original_filename="ada_second.sb3",
            file=SimpleUploadedFile("ada_second.sb3", b"second"),
        )
        Submission.objects.create(
            material=upload,
            student=student_b,
            original_filename="ben.sb3",
            file=SimpleUploadedFile("ben.sb3", b"third"),
        )

        with CaptureQueriesContext(connection) as queries:
            counts = _material_submission_counts([upload.id])

        self.assertEqual(counts.get(upload.id), 2)
        sql_text = "\n".join(q["sql"] for q in queries.captured_queries).upper()
        self.assertIn("COUNT(DISTINCT", sql_text)


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
        classroom, _upload = self._build_lesson_with_submission()
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
        classroom, _upload = self._build_lesson_with_submission()
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
        classroom, _upload = self._build_lesson_with_submission()
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

    def test_teach_class_can_create_student_invite_link(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="INV12345")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/create-invite-link",
            {
                "label": "After-school paid cohort",
                "expires_in_hours": "48",
                "seat_cap": "12",
            },
        )
        self.assertEqual(resp.status_code, 302)
        invite = ClassInviteLink.objects.filter(classroom=classroom).first()
        self.assertIsNotNone(invite)
        self.assertEqual(invite.label, "After-school paid cohort")
        self.assertEqual(invite.max_uses, 12)
        self.assertTrue(invite.is_active)
        self.assertIsNotNone(invite.expires_at)

    def test_teach_class_can_set_enrollment_mode(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="ENR12345")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/set-enrollment-mode",
            {"enrollment_mode": "invite_only"},
        )
        self.assertEqual(resp.status_code, 302)
        classroom.refresh_from_db()
        self.assertEqual(classroom.enrollment_mode, Class.ENROLLMENT_INVITE_ONLY)
        event = AuditEvent.objects.filter(action="class.set_enrollment_mode").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("enrollment_mode"), Class.ENROLLMENT_INVITE_ONLY)

    def test_teach_class_export_summary_csv_contains_class_student_and_lesson_rows(self):
        classroom, upload = self._build_lesson_with_submission()
        student = StudentIdentity.objects.filter(classroom=classroom, display_name="Ada").first()
        rubric = Material.objects.create(
            module=upload.module,
            title="Session rubric",
            type=Material.TYPE_RUBRIC,
            body="Problem solving\nCode quality",
            rubric_scale_max=4,
            order_index=2,
        )
        StudentMaterialResponse.objects.create(
            material=rubric,
            student=student,
            rubric_scores=[4, 3],
            rubric_feedback="private rubric note",
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentEvent.EVENT_HELPER_CHAT_ACCESS,
            source="test",
            details={"prompt": "do not export this"},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/export-summary-csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        body = resp.content.decode("utf-8")
        self.assertIn("class_summary", body)
        self.assertIn("student_summary", body)
        self.assertIn("lesson_summary", body)
        self.assertIn("Ada", body)
        self.assertIn("piper_scratch_12_session", body)
        self.assertIn("rubric_responses", body)
        self.assertNotIn("do not export this", body)
        self.assertNotIn("prompt", body)
        self.assertNotIn("private rubric note", body)

    @override_settings(
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=1,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=1,
    )
    def test_teach_class_export_outcomes_csv_contains_rollups_without_details_payloads(self):
        classroom, _upload = self._build_lesson_with_submission()
        student = StudentIdentity.objects.filter(classroom=classroom, display_name="Ada").first()
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            source="test",
            details={"private_note": "do-not-export"},
        )
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={"internal": "nope"},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/export-outcomes-csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        body = resp.content.decode("utf-8")
        self.assertIn("class_outcome_summary", body)
        self.assertIn("student_outcome_summary", body)
        self.assertIn("Ada", body)
        self.assertIn("yes", body)
        self.assertNotIn("do-not-export", body)
        self.assertNotIn("private_note", body)

        event = AuditEvent.objects.filter(action="class.export_outcomes_csv").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)

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

    def test_teach_module_can_add_checklist_material(self):
        classroom = Class.objects.create(name="Checklist Class", join_code="CHK12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_CHECKLIST,
                "title": "Class checklist",
                "checklist_items": "I completed the warm-up\nI tested my code",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_CHECKLIST).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Class checklist")
        self.assertIn("I completed the warm-up", created.body)

    def test_teach_module_can_add_reflection_material(self):
        classroom = Class.objects.create(name="Reflection Class", join_code="RFL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_REFLECTION,
                "title": "Reflection journal",
                "reflection_prompt": "What changed in your code today?",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_REFLECTION).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Reflection journal")
        self.assertIn("What changed in your code today?", created.body)

    def test_teach_module_can_add_gallery_material(self):
        classroom = Class.objects.create(name="Gallery Class", join_code="GAL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_GALLERY,
                "title": "Share to gallery",
                "accepted_extensions": ".png,.jpg,.jpeg,.pdf",
                "max_upload_mb": "20",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_GALLERY).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Share to gallery")
        self.assertEqual(created.accepted_extensions, ".png,.jpg,.jpeg,.pdf")
        self.assertEqual(created.max_upload_mb, 20)

    def test_teach_module_can_add_rubric_material(self):
        classroom = Class.objects.create(name="Rubric Class", join_code="RUB12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_RUBRIC,
                "title": "Session rubric",
                "rubric_criteria": "Problem solving\nCode quality\nReflection depth",
                "rubric_scale_max": "5",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Material.objects.filter(module=module, type=Material.TYPE_RUBRIC).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Session rubric")
        self.assertEqual(created.rubric_scale_max, 5)
        self.assertIn("Problem solving", created.body)

    def test_teach_material_submissions_supports_rubric_responses(self):
        classroom = Class.objects.create(name="Rubric Review", join_code="RBR12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        rubric = Material.objects.create(
            module=module,
            title="Session rubric",
            type=Material.TYPE_RUBRIC,
            body="Problem solving\nCode quality",
            rubric_scale_max=4,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentMaterialResponse.objects.create(
            material=rubric,
            student=student,
            rubric_scores=[4, 3],
            rubric_feedback="Strong growth this week.",
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/material/{rubric.id}/submissions")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Responses")
        self.assertContains(resp, "Scale 1-4")
        self.assertContains(resp, "Strong growth this week.")

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

    @override_settings(
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=1,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=1,
    )
    def test_teach_class_shows_outcomes_snapshot_panel(self):
        classroom = Class.objects.create(name="Period Outcomes", join_code="OUT12345")
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            source="test",
            details={},
        )
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Outcomes Snapshot")
        self.assertContains(resp, "session completions")
        self.assertContains(resp, "artifact submissions")
        self.assertContains(resp, "certificate eligible")
        self.assertContains(resp, "Top outcome students")
        self.assertContains(resp, "Ada")
        self.assertContains(resp, "eligible")

    def test_teach_delete_student_data_removes_submissions_and_detaches_events(self):
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
        self.assertEqual(StudentEvent.objects.filter(classroom=classroom).count(), 1)

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


class TeacherOrganizationAccessTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="org_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.org_a = Organization.objects.create(name="Org Alpha")
        self.org_b = Organization.objects.create(name="Org Beta")
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.staff,
            role=OrganizationMembership.ROLE_TEACHER,
        )
        self.class_a = Class.objects.create(name="Alpha Cohort", join_code="ORGA1234", organization=self.org_a)
        self.class_b = Class.objects.create(name="Beta Cohort", join_code="ORGB1234", organization=self.org_b)
        _force_login_staff_verified(self.client, self.staff)

    def test_teach_home_lists_only_accessible_org_classes(self):
        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha Cohort")
        self.assertNotContains(resp, "Beta Cohort")

    def test_teach_class_dashboard_blocks_other_org(self):
        resp = self.client.get(f"/teach/class/{self.class_b.id}")
        self.assertEqual(resp.status_code, 404)

    def test_viewer_membership_cannot_mutate_class(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])

        resp = self.client.post(f"/teach/class/{self.class_a.id}/toggle-lock")
        self.assertEqual(resp.status_code, 403)

    def test_viewer_membership_cannot_set_enrollment_mode(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/set-enrollment-mode",
            {"enrollment_mode": "closed"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_create_class_assigns_default_org_for_membership_staff(self):
        resp = self.client.post("/teach/create-class", {"name": "New Alpha Class"})
        self.assertEqual(resp.status_code, 302)
        created = Class.objects.filter(name="New Alpha Class").order_by("-id").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.organization_id, self.org_a.id)

    def test_legacy_staff_without_membership_keeps_global_access(self):
        legacy_staff = get_user_model().objects.create_user(
            username="legacy_staff",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, legacy_staff)

        resp = self.client.get(f"/teach/class/{self.class_b.id}")
        self.assertEqual(resp.status_code, 200)
