from ._shared import *  # noqa: F401,F403


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
        self.assertNotIn("<style", index_html)

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
        self.assertContains(resp, "/static/css/student_my_data.css")
        self.assertContains(resp, "/static/js/confirm_forms.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)
        self.assertNotContains(resp, "onsubmit=\"return confirm(", html=False)
        self.assertContains(resp, "My submissions")
        self.assertContains(resp, "portfolio.sb3")
        self.assertContains(resp, "class activity events in this class")

    def test_student_my_data_page_simple_reading_level_uses_simpler_copy(self):
        self._login_student()

        resp = self.client.get("/student/my-data?reading_level=simple")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reading level: Simple")
        self.assertContains(resp, "Stored data: your class name, your uploads, and basic class timestamps.")
        self.assertContains(resp, "Delete now removes your uploads, class responses, and class activity history")

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
        StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="classhub.student_home",
            details={"signal": "stuck"},
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/student/my-data?notice="))
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 0)
        self.assertEqual(StudentEvent.objects.filter(student=self.student, classroom=self.classroom).count(), 0)

    def test_student_rename_updates_display_name(self):
        self._login_student()

        resp = self.client.post("/student/rename", {"display_name": "Ada Star"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/student/my-data?notice="))
        self.student.refresh_from_db()
        self.assertEqual(self.student.display_name, "Ada Star")
        self.assertEqual(
            StudentEvent.objects.filter(
                student=self.student,
                event_type="student_rename_display_name",
            ).count(),
            1,
        )

    @override_settings(NAME_SAFETY_MODE="strict")
    def test_student_rename_rejects_strict_name_safety_patterns(self):
        self._login_student()

        resp = self.client.post("/student/rename", {"display_name": "kid@example.org"})
        self.assertEqual(resp.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.display_name, "Ada")

    @override_settings(CLASSHUB_STUDENT_SELF_DELETE_MODE="request")
    def test_student_delete_work_request_mode_logs_request_and_keeps_data(self):
        Submission.objects.create(
            material=self.upload,
            student=self.student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"demo"),
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Submission.objects.filter(student=self.student).count(), 1)
        self.assertEqual(
            StudentEvent.objects.filter(
                student=self.student,
                event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            ).count(),
            1,
        )

    def test_student_delete_work_now_clears_material_responses(self):
        checklist = Material.objects.create(
            module=self.module,
            title="Checklist",
            type=Material.TYPE_CHECKLIST,
            body="I did the thing",
            order_index=1,
        )
        StudentMaterialResponse.objects.create(
            material=checklist,
            student=self.student,
            checklist_checked=[0],
            reflection_text="",
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            StudentMaterialResponse.objects.filter(student=self.student, material=checklist).count(),
            0,
        )

    def test_student_delete_work_now_clears_artifact_outcome_events(self):
        StudentOutcomeEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            module=self.module,
            material=self.upload,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                student=self.student,
                event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            ).count(),
            0,
        )

    def test_student_delete_work_now_keeps_other_students_events(self):
        other_student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")
        StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="classhub.student_home",
            details={},
        )
        StudentEvent.objects.create(
            classroom=self.classroom,
            student=other_student,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="classhub.student_home",
            details={},
        )
        StudentOutcomeEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            module=self.module,
            material=self.upload,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )
        StudentOutcomeEvent.objects.create(
            classroom=self.classroom,
            student=other_student,
            module=self.module,
            material=self.upload,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )
        self._login_student()

        resp = self.client.post("/student/delete-work")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(StudentEvent.objects.filter(student=self.student, classroom=self.classroom).count(), 0)
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(student=self.student, classroom=self.classroom).count(),
            0,
        )
        self.assertEqual(StudentEvent.objects.filter(student=other_student, classroom=self.classroom).count(), 1)
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(student=other_student, classroom=self.classroom).count(),
            1,
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
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    @override_settings(CLASSHUB_PROGRAM_PROFILE="advanced")
    def test_join_page_uses_profile_ui_density_default(self):
        join_resp = self.client.get("/")
        self.assertEqual(join_resp.status_code, 200)
        self.assertContains(join_resp, "ui-density-expanded")

    @override_settings(CLASSHUB_PROGRAM_PROFILE="advanced")
    def test_student_home_expanded_mode_shows_studio_handles(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ui-density-expanded")
        self.assertContains(resp, "Studio handles")
        self.assertContains(resp, "Export portfolio snapshot")
        self.assertContains(resp, "Rubric links")
        self.assertContains(resp, "Gallery share toggles")
        self.assertContains(resp, "Studio accountability")

    def test_student_home_renders_class_landing_content(self):
        self.classroom.student_landing_title = "Week 5 Landing"
        self.classroom.student_landing_message = "Start here, then open your course links."
        self.classroom.student_landing_hero_url = "/lesson-asset/42/download"
        self.classroom.save(
            update_fields=["student_landing_title", "student_landing_message", "student_landing_hero_url"]
        )
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Week 5 Landing")
        self.assertContains(resp, "Start here, then open your course links.")
        self.assertContains(resp, "/lesson-asset/42/download")

    def test_student_home_renders_inline_image_material(self):
        folder = LessonAssetFolder.objects.create(path="lesson-images")
        asset = LessonAsset.objects.create(
            folder=folder,
            title="Storyboard reference",
            description="Use this image as your inspiration board.",
            original_filename="storyboard.png",
            file=SimpleUploadedFile("storyboard.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00", content_type="image/png"),
        )
        Material.objects.create(
            module=self.module,
            title="Storyboard reference",
            type=Material.TYPE_LINK,
            url=f"/lesson-asset/{asset.id}/download",
            order_index=1,
        )
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'/lesson-asset/{asset.id}/download')
        self.assertContains(resp, 'class="mat-image"', html=False)
        self.assertContains(resp, "Use this image as your inspiration board.")

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
        self.assertNotContains(join_resp, "{% trans", html=False)
        self.assertNotContains(join_resp, "{{ operator_profile.", html=False)
        self.assertContains(join_resp, "/static/css/student_join.css")
        self.assertContains(join_resp, "/static/js/return_code_icons.js")
        self.assertContains(join_resp, "/static/js/student_join.js")
        self.assertContains(join_resp, 'name="csrfmiddlewaretoken"', html=False)
        self.assertNotContains(join_resp, "<style>", html=False)
        self.assertNotContains(join_resp, 'style="display:none"', html=False)
        self.assertNotContains(join_resp, "const csrfToken = () =>", html=False)
        self.assertNotContains(join_resp, "document.getElementById('join-form')", html=False)

        self._login_student()
        my_data_resp = self.client.get("/student/my-data")
        self.assertEqual(my_data_resp.status_code, 200)
        self.assertContains(my_data_resp, "this server is hosted by Northside Public Schools.")
        self.assertContains(my_data_resp, "No surveillance analytics. No ad-tech. No data broker sharing.")
        self.assertNotContains(my_data_resp, "{% trans", html=False)
        self.assertNotContains(my_data_resp, "{{ operator_profile.", html=False)

        admin_login_resp = self.client.get("/admin/login/")
        self.assertEqual(admin_login_resp.status_code, 200)
        self.assertContains(admin_login_resp, "Northside School Admin Login")
        self.assertContains(admin_login_resp, "/static/css/admin_login.css")
        self.assertContains(admin_login_resp, "/static/js/admin_login.js")
        self.assertNotContains(admin_login_resp, "<style>", html=False)
        self.assertNotContains(admin_login_resp, 'style="margin:8px 0 0 0;"', html=False)
        self.assertNotContains(admin_login_resp, 'var form = document.getElementById("login-form")', html=False)
