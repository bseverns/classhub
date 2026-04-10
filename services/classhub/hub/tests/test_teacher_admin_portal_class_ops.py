from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class TeacherPortalClassOpsTests(TeacherPortalBaseTests):
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

        resp = self.client.get("/teach?portal_mode=day")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_home.css")
        self.assertContains(resp, "/static/js/teach_home.js")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0 0 10px 0"', html=False)
        self.assertNotContains(resp, "const tabRoot = document.querySelector", html=False)
        self.assertContains(resp, "Recent submissions")
        self.assertContains(resp, "Ada")
        self.assertNotContains(resp, "Import Syllabus Source")
        self.assertNotContains(resp, "Generate Course Authoring Templates")
        self.assertNotContains(resp, "Syllabus Exports")
        self.assertContains(resp, "Show operator tools")
        self.assertNotContains(resp, "Invite teacher")
        self.assertNotContains(resp, "My profile")

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=False)
    def test_teach_home_warns_when_org_membership_strict_mode_off(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Org-boundary warning: strict org membership mode is currently off.")

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_teach_home_hides_org_boundary_warning_when_strict_mode_on(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Org-boundary warning: strict org membership mode is currently off.")

    def test_teach_home_day_mode_hides_setup_and_admin_sections(self):
        self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?portal_mode=day")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Here Today")
        self.assertContains(resp, "Portal modes")
        self.assertContains(resp, "Classroom focus")
        self.assertContains(resp, "Recent submissions")
        self.assertNotContains(resp, "Import Syllabus Source")
        self.assertNotContains(resp, "Portal setup + account tools")
        self.assertNotContains(resp, "Operator config snapshot")

    def test_teach_home_setup_mode_hides_day_sections(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?portal_mode=setup")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Here Today")
        self.assertContains(resp, "Daily teaching workflows (tasks 1-8)")
        self.assertContains(resp, "Operator + policy workflows (tasks 9-10)")
        self.assertContains(resp, "Portal setup + account tools")
        self.assertContains(resp, "Import Syllabus Source")
        self.assertNotContains(resp, "Classroom focus")
        self.assertNotContains(resp, "Recent submissions")

    def test_teach_home_setup_mode_surfaces_class_workspace_seed_fields(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?portal_mode=setup")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Create a class workspace")
        self.assertContains(resp, 'name="student_landing_title"', html=False)
        self.assertContains(resp, 'name="student_landing_message"', html=False)
        self.assertContains(resp, 'name="first_module_title"', html=False)
        self.assertContains(resp, 'name="open_after_create"', html=False)
        self.assertContains(resp, "Create class workspace")

    def test_teach_home_admin_mode_shows_operator_snapshot_and_org_controls(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?portal_mode=admin&advanced=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Operator config snapshot")
        self.assertContains(resp, "Organizations + Staff Memberships")
        self.assertContains(resp, "Portal setup + account tools")
        self.assertNotContains(resp, "Start Here Today")
        self.assertNotContains(resp, "Classroom focus")
        self.assertNotContains(resp, "Recent submissions")

    def test_superuser_teach_home_hides_operator_config_snapshot_by_default(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Here Today")
        self.assertNotContains(resp, "Operator config snapshot")
        self.assertContains(resp, "Show operator tools")

    def test_superuser_teach_home_shows_operator_config_snapshot_in_advanced_mode(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?advanced=1&portal_mode=all")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Operator config snapshot")
        self.assertContains(resp, "Telemetry rollout status")
        self.assertContains(resp, "Parity + rollback evidence captured")
        self.assertContains(resp, "telemetry_stabilization_evidence.sh")
        self.assertContains(resp, "Program profile")
        self.assertContains(resp, "docs/FEATURE_MATURITY.md")

    @override_settings(
        REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=False,
        CLASSHUB_TELEMETRY_WRITE_MODE="off",
        CLASSHUB_TELEMETRY_READ_MODE="core",
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=8,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=6,
    )
    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_CERTIFICATE_MIN_SESSIONS": "",
            "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS": "",
        },
        clear=False,
    )
    def test_superuser_runtime_policy_lock_surfaces_mismatches(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?advanced=1&portal_mode=admin")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Runtime policy lock")
        self.assertContains(resp, "Runtime lock mismatch detected; align runtime values before release sign-off.")
        self.assertContains(resp, "Org boundary strict mode")
        self.assertContains(resp, "Telemetry write mode")
        self.assertContains(resp, "Telemetry read mode")
        self.assertContains(resp, "Certificate min sessions env")
        self.assertContains(resp, "Certificate min artifacts env")
        self.assertContains(resp, "FAIL")

    @override_settings(
        REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True,
        CLASSHUB_TELEMETRY_WRITE_MODE="dual",
        CLASSHUB_TELEMETRY_READ_MODE="telemetry",
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=2,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=2,
    )
    @patch.dict(
        "os.environ",
        {
            "CLASSHUB_CERTIFICATE_MIN_SESSIONS": "2",
            "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS": "2",
        },
        clear=False,
    )
    def test_superuser_runtime_policy_lock_passes_when_expected_values_are_set(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach?advanced=1&portal_mode=admin")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Runtime policy lock")
        self.assertContains(resp, "All runtime lock checks pass for this node.")
        self.assertContains(resp, "PASS")

    def test_superuser_can_export_syllabus_catalog_csv(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach/syllabus-export?kind=catalog_csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        body = resp.content.decode("utf-8")
        self.assertIn("course_slug,course_title", body)
        self.assertIn("piper_scratch_12_session", body)

        event = AuditEvent.objects.filter(action="syllabus_export.catalog_csv").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_export_syllabus_backup_zip(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach/syllabus-export?kind=backup_zip")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")

        zip_bytes = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            names = archive.namelist()
        self.assertTrue(any(name.startswith("courses/") for name in names))

        event = AuditEvent.objects.filter(action="syllabus_export.backup_zip").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

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

        resp = self.client.get("/teach?portal_mode=day")
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

    def test_teach_create_class_can_seed_workspace_and_redirect_into_it(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/create-class",
            {
                "name": "Workspace Cohort",
                "student_landing_title": "Week 1 kickoff",
                "student_landing_message": "Start with the warm-up, then open Session 1.",
                "first_module_title": "Session 1 - Warm-up + Build",
                "open_after_create": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        created = Class.objects.filter(name="Workspace Cohort").order_by("-id").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.student_landing_title, "Week 1 kickoff")
        self.assertEqual(created.student_landing_message, "Start with the warm-up, then open Session 1.")
        self.assertIn(f"/teach/class/{created.id}", resp["Location"])
        self.assertIn("notice=", resp["Location"])
        module = Module.objects.filter(classroom=created).order_by("order_index", "id").first()
        self.assertIsNotNone(module)
        self.assertEqual(module.title, "Session 1 - Warm-up + Build")

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

    def test_teach_class_can_set_retention_preset(self):
        classroom = Class.objects.create(name="Retention Cohort", join_code="RET22345")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/set-retention-preset",
            {"retention_preset": Class.RETENTION_KEEP_SEMESTER},
        )
        self.assertEqual(resp.status_code, 302)
        classroom.refresh_from_db()
        self.assertEqual(classroom.retention_preset, Class.RETENTION_KEEP_SEMESTER)

        event = AuditEvent.objects.filter(action="class.set_retention_preset").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("retention_preset"), Class.RETENTION_KEEP_SEMESTER)

    def test_teach_class_can_update_student_landing_page(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="LND12345")
        module = Module.objects.create(classroom=classroom, title="Session 4", order_index=4)
        Material.objects.create(
            module=module,
            title="Session 4 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/s04-pipercode-debugging",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/update-landing-page",
            {
                "student_landing_title": "Week 4: Cutscene polish",
                "student_landing_message": "Start with your highlighted lesson, then open course links below.",
                "student_landing_hero_url": "https://example.org/landing.png",
                "student_landing_default_module_id": str(module.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        classroom.refresh_from_db()
        self.assertEqual(classroom.student_landing_title, "Week 4: Cutscene polish")
        self.assertEqual(
            classroom.student_landing_message,
            "Start with your highlighted lesson, then open course links below.",
        )
        self.assertEqual(classroom.student_landing_hero_url, "https://example.org/landing.png")
        self.assertEqual(classroom.student_landing_default_module_id, module.id)

        event = AuditEvent.objects.filter(action="class.update_student_landing").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("default_module_id"), module.id)

    def test_teach_class_rejects_invalid_student_landing_hero_url(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="LND12346")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/update-landing-page",
            {
                "student_landing_title": "Week 4",
                "student_landing_message": "Message",
                "student_landing_hero_url": "ftp://example.org/image.png",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/class/", resp["Location"])
        self.assertIn("error=", resp["Location"])
        classroom.refresh_from_db()
        self.assertEqual(classroom.student_landing_hero_url, "")

    def test_teach_class_rejects_default_landing_module_without_lesson_link(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="LND12347")
        module = Module.objects.create(classroom=classroom, title="Session notes only", order_index=1)
        Material.objects.create(
            module=module,
            title="Session text",
            type=Material.TYPE_TEXT,
            body="No lesson link here",
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/update-landing-page",
            {
                "student_landing_title": "Week 4",
                "student_landing_message": "Message",
                "student_landing_default_module_id": str(module.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=", resp["Location"])
        classroom.refresh_from_db()
        self.assertIsNone(classroom.student_landing_default_module_id)

    def test_teach_class_landing_form_shows_default_lesson_selector(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="LND12348")
        module = Module.objects.create(classroom=classroom, title="Session 2", order_index=1)
        Material.objects.create(
            module=module,
            title="Session 2 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/s02-piper-desktop-basics",
            order_index=0,
        )
        classroom.student_landing_default_module = module
        classroom.save(update_fields=["student_landing_default_module"])
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="student_landing_default_module_id"', html=False)
        self.assertContains(
            resp,
            f'<option value="{module.id}" selected>',
            html=False,
        )

    def test_teach_class_landing_forms_render_csrf_tokens(self):
        classroom = Class.objects.create(name="Paid Cohort", join_code="LND12349")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'action="/teach/class/{classroom.id}/update-landing-page"', html=False)
        self.assertContains(resp, 'name="csrfmiddlewaretoken"', html=False)

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
        CertificateIssuance.objects.create(
            classroom=classroom,
            student=student,
            issued_by=self.staff,
            code="CERT0001",
            signed_token="signed-token",
            session_count=1,
            artifact_count=1,
            milestone_count=0,
            min_sessions_required=1,
            min_artifacts_required=1,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}/export-outcomes-csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        body = resp.content.decode("utf-8")
        self.assertIn("class_outcome_summary", body)
        self.assertIn("student_outcome_summary", body)
        self.assertIn("certificate_issued", body)
        self.assertIn("certificate_issued_students", body)
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

    def test_teach_class_start_here_links_match_section_anchors(self):
        classroom = Class.objects.create(name="Period Layout", join_code="LAY12345")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Here In This Class")
        self.assertContains(resp, 'href="#section-invite-links"')
        self.assertContains(resp, 'href="#section-roster"')
        self.assertContains(resp, 'href="#section-support-board"')
        self.assertContains(resp, 'href="#section-outcomes"')
        self.assertContains(resp, 'href="#section-helper-signals"')
        self.assertContains(resp, 'href="#section-module-editor"')
        self.assertContains(resp, 'id="section-invite-links"', html=False)
        self.assertContains(resp, 'id="section-roster"', html=False)
        self.assertContains(resp, 'id="section-support-board"', html=False)
        self.assertContains(resp, 'id="section-outcomes"', html=False)
        self.assertContains(resp, 'id="section-helper-signals"', html=False)
        self.assertContains(resp, 'id="section-module-editor"', html=False)

    def test_teach_class_shows_unified_workspace_controls(self):
        classroom = Class.objects.create(name="Period Workspace", join_code="WRK12345")
        Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unified Class Workspace")
        self.assertContains(resp, f'action="/teach/class/{classroom.id}/set-enrollment-mode"', html=False)
        self.assertContains(resp, f'action="/teach/class/{classroom.id}/set-retention-preset"', html=False)
        self.assertContains(resp, f'action="/teach/class/{classroom.id}/update-landing-page"', html=False)
        self.assertContains(resp, f'action="/teach/class/{classroom.id}/add-module"', html=False)
        self.assertContains(resp, "Build today")
        self.assertContains(resp, "Student access controls")

    def test_teach_class_module_editor_surfaces_quick_add_forms(self):
        classroom = Class.objects.create(name="Rolling Build Class", join_code="RBL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Add to this session now")
        self.assertContains(resp, f'action="/teach/module/{module.id}/add-material"', html=False)
        self.assertContains(resp, f'<input type="hidden" name="return_to" value="/teach/class/{classroom.id}" />', html=False)
        self.assertContains(resp, "Add note")
        self.assertContains(resp, "Add link")
        self.assertContains(resp, "Add image")
        self.assertContains(resp, "Add dropbox")

    def test_teach_class_can_quick_add_text_material_to_existing_module(self):
        classroom = Class.objects.create(name="Rolling Build Class", join_code="RBL12346")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/module/{module.id}/add-material",
            {
                "type": Material.TYPE_TEXT,
                "title": "Mid-class pivot",
                "body": "Follow the student questions and test two alternatives.",
                "return_to": f"/teach/class/{classroom.id}",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/teach/class/{classroom.id}", resp["Location"])
        self.assertIn("notice=", resp["Location"])
        created = Material.objects.filter(module=module, type=Material.TYPE_TEXT, title="Mid-class pivot").first()
        self.assertIsNotNone(created)
        self.assertIn("Follow the student questions", created.body)

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

    def test_teach_videos_uses_external_css_without_inline_styles(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach/videos")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_videos.css")
        self.assertContains(resp, "Lesson Videos")
        self.assertContains(resp, "Optional: auto-filled from the URL or file name")
        self.assertNotContains(resp, "<style>", html=False)
        self.assertNotContains(resp, 'style="margin:0"', html=False)
        self.assertNotContains(resp, 'name="title" placeholder="e.g., Save privately: Download to your computer" required', html=False)

    def test_teach_videos_can_add_youtube_url_without_manual_title(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/videos",
            {
                "action": "add",
                "course_slug": "energy_electronics_circuits_9_session",
                "lesson_slug": "s01-energy-is-everywhere",
                "title": "",
                "minutes": "2",
                "outcome": "Hear one beginner-friendly oscillator example.",
                "source_url": "https://www.youtube.com/watch?v=QixV_Hlh2CM",
                "is_active": "1",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/videos?", resp["Location"])
        created = LessonVideo.objects.filter(
            course_slug="energy_electronics_circuits_9_session",
            lesson_slug="s01-energy-is-everywhere",
            source_url="https://www.youtube.com/watch?v=QixV_Hlh2CM",
        ).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "YouTube video (QixV_Hlh2CM)")
        self.assertTrue(created.is_active)

    def test_teach_videos_reorder_updates_changed_rows(self):
        _force_login_staff_verified(self.client, self.staff)
        first = LessonVideo.objects.create(
            course_slug="energy_electronics_circuits_9_session",
            lesson_slug="s01-energy-is-everywhere",
            title="Video 1",
            source_url="https://example.com/1",
            order_index=0,
            is_active=True,
        )
        second = LessonVideo.objects.create(
            course_slug="energy_electronics_circuits_9_session",
            lesson_slug="s01-energy-is-everywhere",
            title="Video 2",
            source_url="https://example.com/2",
            order_index=1,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/videos",
            {
                "action": "move",
                "course_slug": "energy_electronics_circuits_9_session",
                "lesson_slug": "s01-energy-is-everywhere",
                "video_id": second.id,
                "direction": "up",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/videos?", resp["Location"])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.order_index, first.order_index), (0, 1))

    def test_course_lesson_renders_teacher_added_published_youtube_video(self):
        _force_login_staff_verified(self.client, self.staff)
        LessonVideo.objects.create(
            course_slug="energy_electronics_circuits_9_session",
            lesson_slug="s01-energy-is-everywhere",
            title="YouTube video (QixV_Hlh2CM)",
            source_url="https://www.youtube.com/watch?v=QixV_Hlh2CM",
            is_active=True,
        )

        resp = self.client.get("/course/energy_electronics_circuits_9_session/s01-energy-is-everywhere")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Lesson videos")
        self.assertContains(resp, "YouTube video (QixV_Hlh2CM)")
        self.assertContains(resp, "https://www.youtube.com/watch?v=QixV_Hlh2CM")
        self.assertContains(resp, "https://www.youtube-nocookie.com/embed/QixV_Hlh2CM")

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
        self.assertContains(resp, "helper chats")
        self.assertContains(resp, "debug")
        self.assertContains(resp, "concept")
        self.assertContains(resp, "Ada")
        self.assertContains(resp, "2 chats")

    def test_teach_class_shows_facilitator_support_board(self):
        classroom = Class.objects.create(name="Period Support", join_code="SUPP1234")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload work",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentIdentity.objects.filter(id=ada.id).update(last_seen_at=timezone.now() - timedelta(minutes=31))
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD_ERROR,
            source="test",
            details={"material_id": material.id, "reason_code": "content_validation_failed"},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Facilitator Support Board")
        self.assertContains(resp, "Students asking for help (1)")
        self.assertContains(resp, "Deletion requests (1)")
        self.assertContains(resp, "Recent upload errors (1)")
        self.assertContains(resp, "Idle signals (20+ min)")
        self.assertContains(resp, f"/teach/class/{classroom.id}/resolve-stuck")
        self.assertContains(resp, f"/teach/class/{classroom.id}/resolve-delete-request")
        self.assertContains(resp, "Support tags")
        self.assertContains(resp, "Needs extra time")
        self.assertContains(resp, f"/teach/class/{classroom.id}/support-tag/add")

    def test_teacher_can_resolve_stuck_flag(self):
        classroom = Class.objects.create(name="Resolve Stuck Class", join_code="RSK12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/resolve-stuck",
            {"student_id": str(ada.id), "module_id": str(module.id)},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/class/", resp["Location"])

        event = StudentEvent.objects.filter(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
        ).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(int((event.details or {}).get("module_id") or 0), module.id)

    def test_teacher_can_resolve_delete_request(self):
        classroom = Class.objects.create(name="Resolve Delete Class", join_code="RDL12345")
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/resolve-delete-request",
            {"student_id": str(ada.id)},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach/class/", resp["Location"])

        event = StudentEvent.objects.filter(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
        ).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(int((event.details or {}).get("resolved_by_user_id") or 0), self.staff.id)

    def test_teacher_can_add_and_remove_support_tag(self):
        classroom = Class.objects.create(name="Support Tags Class", join_code="TAG12345")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        add_resp = self.client.post(
            f"/teach/class/{classroom.id}/support-tag/add",
            {"student_id": str(student.id), "tag": StudentSupportTag.TAG_DEVICE_HELP},
        )
        self.assertEqual(add_resp.status_code, 302)
        self.assertTrue(
            StudentSupportTag.objects.filter(
                classroom=classroom,
                student=student,
                tag=StudentSupportTag.TAG_DEVICE_HELP,
            ).exists()
        )

        remove_resp = self.client.post(
            f"/teach/class/{classroom.id}/support-tag/remove",
            {"student_id": str(student.id), "tag": StudentSupportTag.TAG_DEVICE_HELP},
        )
        self.assertEqual(remove_resp.status_code, 302)
        self.assertFalse(
            StudentSupportTag.objects.filter(
                classroom=classroom,
                student=student,
                tag=StudentSupportTag.TAG_DEVICE_HELP,
            ).exists()
        )

        add_event = AuditEvent.objects.filter(action="student.support_tag_add").order_by("-id").first()
        remove_event = AuditEvent.objects.filter(action="student.support_tag_remove").order_by("-id").first()
        self.assertIsNotNone(add_event)
        self.assertIsNotNone(remove_event)
        self.assertEqual(add_event.classroom_id, classroom.id)
        self.assertEqual(remove_event.classroom_id, classroom.id)

    def test_teacher_cannot_add_support_tag_to_other_class_student(self):
        classroom = Class.objects.create(name="Support Tags Scope A", join_code="TAGA1234")
        other_classroom = Class.objects.create(name="Support Tags Scope B", join_code="TAGB1234")
        other_student = StudentIdentity.objects.create(classroom=other_classroom, display_name="Ben")
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/support-tag/add",
            {"student_id": str(other_student.id), "tag": StudentSupportTag.TAG_NEEDS_EXTRA_TIME},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            StudentSupportTag.objects.filter(
                classroom=classroom,
                student=other_student,
            ).exists()
        )

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

    @override_settings(
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=1,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=1,
    )
    def test_teacher_can_mark_session_completed_and_view_certificate_page(self):
        classroom = Class.objects.create(name="Period Manual Session", join_code="MAN12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        _force_login_staff_verified(self.client, self.staff)

        view_resp = self.client.get(f"/teach/class/{classroom.id}/certificate-eligibility")
        self.assertEqual(view_resp.status_code, 200)
        self.assertContains(view_resp, "Certificate Eligibility")
        self.assertContains(view_resp, "Mark Session Completed")
        self.assertContains(view_resp, "Ada")

        post_resp = self.client.post(
            f"/teach/class/{classroom.id}/mark-session-completed",
            {"student_id": str(student.id), "module_id": str(module.id)},
        )
        self.assertEqual(post_resp.status_code, 302)
        self.assertIn("/teach/class/", post_resp["Location"])

        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                classroom=classroom,
                student=student,
                module=module,
                event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            ).count(),
            1,
        )

    @override_settings(
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=1,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=1,
    )
    def test_teacher_can_issue_and_download_certificate(self):
        classroom = Class.objects.create(name="Period Certs", join_code="CER12345")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            source="test",
            details={},
        )
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )
        _force_login_staff_verified(self.client, self.staff)

        issue_resp = self.client.post(
            f"/teach/class/{classroom.id}/issue-certificate",
            {"student_id": str(student.id)},
        )
        self.assertEqual(issue_resp.status_code, 302)

        issuance = CertificateIssuance.objects.filter(classroom=classroom, student=student).first()
        self.assertIsNotNone(issuance)
        self.assertTrue((issuance.signed_token or "").strip())
        self.assertGreaterEqual(issuance.session_count, 1)
        self.assertGreaterEqual(issuance.artifact_count, 1)

        view_resp = self.client.get(f"/teach/class/{classroom.id}/certificate-eligibility")
        self.assertEqual(view_resp.status_code, 200)
        self.assertContains(view_resp, "Download PDF")
        self.assertContains(view_resp, "TXT")
        self.assertContains(view_resp, issuance.code)

        download_resp = self.client.get(f"/teach/class/{classroom.id}/certificate/{student.id}/download")
        self.assertEqual(download_resp.status_code, 200)
        self.assertIn("attachment;", download_resp["Content-Disposition"])
        self.assertIn(issuance.code, download_resp["Content-Disposition"])
        self.assertContains(download_resp, "Class Hub Certificate Record")
        self.assertContains(download_resp, "Signed token")

        pdf_resp = self.client.get(f"/teach/class/{classroom.id}/certificate/{student.id}/download.pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp["Content-Type"], "application/pdf")
        self.assertIn(".pdf", pdf_resp["Content-Disposition"])
        self.assertTrue(pdf_resp.content.startswith(b"%PDF-1.4"))

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

    @patch("hub.views.teacher_parts.roster_class._reset_helper_class_conversations")
    def test_teacher_can_reset_helper_conversations(self, reset_mock):
        classroom = Class.objects.create(name="Period Helper", join_code="HLP12345")
        reset_mock.return_value = HelperResetResult(
            ok=True,
            deleted_conversations=4,
            archived_conversations=4,
            archive_path="/uploads/helper_reset_exports/sample.json",
            request_id="helper-reset-req-1",
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
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-reset-req-1")

    @patch("hub.views.teacher_parts.roster_class._reset_helper_class_conversations")
    def test_teacher_reset_helper_conversations_handles_failure(self, reset_mock):
        classroom = Class.objects.create(name="Period Helper Fail", join_code="HLF12345")
        reset_mock.return_value = HelperResetResult(
            ok=False,
            request_id="helper-reset-fail-1",
            error_code="helper_unreachable",
            status_code=0,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(f"/teach/class/{classroom.id}/reset-helper-conversations")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=", resp["Location"])

        event = AuditEvent.objects.filter(action="class.reset_helper_conversations_failed").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("error_code"), "helper_unreachable")
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-reset-fail-1")

    @patch("hub.views.teacher_parts.roster_class_remote_compute.set_remote_compute_state")
    def test_teacher_can_activate_remote_helper_compute(self, set_remote_compute_mock):
        classroom = Class.objects.create(name="Partner Session", join_code="GPU12345")
        set_remote_compute_mock.return_value = HelperRemoteComputeActionResult(
            ok=True,
            action="activate",
            active=True,
            active_for_class=True,
            class_id=classroom.id,
            requested_by=self.staff.username,
            expires_at="2099-04-08T13:30:00+00:00",
            remaining_minutes=90,
            provider_request_id="req-remote-1",
            request_id="helper-remote-req-1",
            detail="warming",
            status_code=200,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            f"/teach/class/{classroom.id}/remote-helper-compute",
            {"action": "activate", "duration_minutes": "90"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("notice=", resp["Location"])

        event = AuditEvent.objects.filter(action="class.remote_helper_compute_activate").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("remaining_minutes"), 90)
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-remote-req-1")

    @patch("hub.views.teacher_parts.roster_class_remote_compute.set_remote_compute_state")
    def test_teacher_remote_helper_compute_failure_redirects_with_error(self, set_remote_compute_mock):
        classroom = Class.objects.create(name="Partner Session Fail", join_code="GPU54321")
        set_remote_compute_mock.return_value = HelperRemoteComputeActionResult(
            ok=False,
            action="activate",
            request_id="helper-remote-fail-1",
            error_code="remote_compute_control_not_configured",
            status_code=503,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            f"/teach/class/{classroom.id}/remote-helper-compute",
            {"action": "activate", "duration_minutes": "90"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=", resp["Location"])

        event = AuditEvent.objects.filter(action="class.remote_helper_compute_failed").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("action_requested"), "activate")
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-remote-fail-1")

    @patch("hub.views.teacher_parts.roster_class_dashboard.fetch_remote_compute_status")
    def test_teach_class_dashboard_shows_remote_helper_compute_panel_for_policy_managers(self, status_mock):
        classroom = Class.objects.create(name="Partner Session Status", join_code="GPU00001")
        status_mock.return_value = HelperRemoteComputeStatusResult(
            ok=True,
            feature_enabled=True,
            paid_usage_acknowledged=True,
            backend_configured=True,
            active=True,
            active_for_class=True,
            use_remote_backend=False,
            state="starting",
            class_id=classroom.id,
            requested_by=self.staff.username,
            remaining_minutes=60,
            provider_label="thunder-orchestration",
            control_url_configured=True,
            healthcheck_url_configured=True,
            status_detail="Booting remote helper node.",
            activation_count=3,
            avg_ready_seconds=18,
            remote_route_count=4,
            fallback_local_count=1,
            degraded_transition_count=2,
            provider_unreachable_count=1,
            unused_activation_count=1,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Remote helper compute")
        self.assertContains(resp, "Request remote helper compute")
        self.assertContains(resp, "State: <strong>starting</strong>.", html=False)
        self.assertContains(resp, "Helper will use remote backend: <strong>No</strong>", html=False)
        self.assertContains(resp, "Recorded activations: <strong>3</strong>", html=False)
        self.assertContains(resp, "Average time to ready: <strong>18 second(s)</strong>", html=False)
        self.assertContains(resp, "Remote-routed helper chats: <strong>4</strong>", html=False)
        self.assertContains(resp, "Remote fallbacks to local/default: <strong>1</strong>", html=False)

    @patch("hub.views.teacher_parts.roster_class_dashboard.staff_can_manage_policy", return_value=False)
    @patch("hub.views.teacher_parts.roster_class_dashboard.fetch_remote_compute_status")
    def test_teach_class_dashboard_hides_remote_helper_compute_panel_without_policy_capability(
        self,
        status_mock,
        _manage_policy_mock,
    ):
        classroom = Class.objects.create(name="Partner Session Hidden", join_code="GPU00002")
        status_mock.return_value = HelperRemoteComputeStatusResult(ok=True, state="ready", use_remote_backend=True)

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Remote helper compute")
        status_mock.assert_not_called()
