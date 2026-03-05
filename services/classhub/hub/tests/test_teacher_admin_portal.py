from ._shared import *  # noqa: F401,F403

class RetentionSettingParsingTests(SimpleTestCase):
    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS=0, CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=0)
    def test_retention_days_preserves_explicit_zero(self):
        from ..services.student_home import _retention_days

        self.assertEqual(_retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90), 0)
        self.assertEqual(_retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180), 0)

    @override_settings(CLASSHUB_SUBMISSION_RETENTION_DAYS="bad", CLASSHUB_STUDENT_EVENT_RETENTION_DAYS="bad")
    def test_retention_days_falls_back_to_default_on_invalid_values(self):
        from ..services.student_home import _retention_days

        self.assertEqual(_retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90), 90)
        self.assertEqual(_retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180), 180)


class DataLifespanDashboardTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_user(
            username="ops_super",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )
        self.viewer = get_user_model().objects.create_user(
            username="ops_viewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.org = Organization.objects.create(name="Ops Org", is_active=True)
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.viewer,
            role=OrganizationMembership.ROLE_VIEWER,
            is_active=True,
        )
        self.classroom = Class.objects.create(
            name="Ops Class",
            join_code="OPS12345",
            organization=self.org,
        )
        module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        old_submission = Submission.objects.create(
            material=material,
            student=student,
            original_filename="old.sb3",
            file=SimpleUploadedFile("old.sb3", b"old"),
        )
        Submission.objects.filter(id=old_submission.id).update(uploaded_at=timezone.now() - timedelta(days=30))
        old_event = StudentEvent.objects.create(
            classroom=self.classroom,
            student=student,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        StudentEvent.objects.filter(id=old_event.id).update(created_at=timezone.now() - timedelta(days=30))
        AuditEvent.objects.create(
            action="retention.prune_submissions",
            target_type="RetentionJob",
            target_id="submissions",
            summary="Pruned submissions (deleted 1 rows)",
            metadata={"matched_rows": 1, "deleted_rows": 1},
        )

    def test_superuser_can_view_data_lifespan_dashboard(self):
        _force_login_staff_verified(self.client, self.superuser)

        resp = self.client.get("/teach/data-lifespan")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/static/css/teach_home.css")
        self.assertContains(resp, "Data Lifespan Dashboard")
        self.assertContains(resp, "Last successful retention prune")
        self.assertContains(resp, "retention.prune_submissions")
        snapshot = resp.context["snapshot"]
        self.assertGreaterEqual(int(snapshot["events_total"]), 1)
        self.assertGreaterEqual(int(snapshot["submissions_total"]), 1)
        self.assertEqual(snapshot["last_prune_run"].action, "retention.prune_submissions")

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_viewer_membership_cannot_view_data_lifespan_dashboard(self):
        _force_login_staff_verified(self.client, self.viewer)
        resp = self.client.get("/teach/data-lifespan")
        self.assertEqual(resp.status_code, 403)


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

    def test_facilitator_snapshot_scopes_to_class_and_unresolved_stuck(self):
        from ..services.teacher_roster_class import _build_facilitator_support_snapshot

        classroom = Class.objects.create(name="Support Class", join_code="SUP12345")
        other_class = Class.objects.create(name="Other Class", join_code="OTH12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload Box",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )

        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        ben = StudentIdentity.objects.create(classroom=classroom, display_name="Ben")
        zed = StudentIdentity.objects.create(classroom=other_class, display_name="Zed")
        StudentIdentity.objects.filter(id=ada.id).update(last_seen_at=timezone.now() - timedelta(minutes=42))
        StudentIdentity.objects.filter(id=ben.id).update(last_seen_at=timezone.now() - timedelta(minutes=4))
        ada.refresh_from_db()
        ben.refresh_from_db()

        StudentEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ben,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ben,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
            source="test",
            details={"module_id": module.id},
        )
        StudentEvent.objects.create(
            classroom=other_class,
            student=zed,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={},
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
        StudentEvent.objects.create(
            classroom=classroom,
            student=ben,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            source="test",
            details={},
        )
        StudentEvent.objects.create(
            classroom=classroom,
            student=ben,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
            source="test",
            details={},
        )
        StudentEvent.objects.create(
            classroom=other_class,
            student=zed,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD_ERROR,
            source="test",
            details={"reason_code": "content_validation_failed"},
        )

        snapshot = _build_facilitator_support_snapshot(
            classroom=classroom,
            students=[ada, ben],
            modules=[module],
        )

        self.assertEqual(snapshot["stuck_count"], 1)
        self.assertEqual(snapshot["stuck_rows"][0]["display_name"], "Ada")
        self.assertEqual(snapshot["upload_error_count"], 1)
        self.assertEqual(snapshot["upload_error_rows"][0]["display_name"], "Ada")
        self.assertEqual(snapshot["upload_error_rows"][0]["material_title"], "Upload Box")
        self.assertEqual(snapshot["delete_request_count"], 1)
        self.assertEqual(snapshot["delete_request_rows"][0]["display_name"], "Ada")
        self.assertEqual([row["display_name"] for row in snapshot["idle_rows"]], ["Ada"])


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
        self.assertContains(resp, "Import Syllabus Source")
        self.assertContains(resp, "Generate Course Authoring Templates")
        self.assertContains(resp, "Syllabus Exports")
        self.assertContains(resp, "Invite teacher")
        self.assertContains(resp, "My profile")

    def test_superuser_teach_home_shows_operator_config_snapshot(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Operator config snapshot")
        self.assertContains(resp, "Program profile")
        self.assertContains(resp, "docs/FEATURE_MATURITY.md")

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

    def test_teacher_can_update_own_profile_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/profile/update",
            {
                "first_name": "Terry",
                "last_name": "Portal",
                "email": "terry.portal@example.org",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Terry")
        self.assertEqual(self.staff.last_name, "Portal")
        self.assertEqual(self.staff.email, "terry.portal@example.org")

        event = AuditEvent.objects.filter(action="teacher_profile.update_self").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_teacher_profile_update_rejects_invalid_email(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/update",
            {
                "first_name": "Terry",
                "last_name": "Portal",
                "email": "invalid-email",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "")

    def test_teacher_can_change_password_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/password",
            {
                "current_password": "pw12345",
                "new_password": "N3wTeacherPw123!",
                "new_password_confirm": "N3wTeacherPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("N3wTeacherPw123!"))
        teach_resp = self.client.get("/teach")
        self.assertEqual(teach_resp.status_code, 200)

        event = AuditEvent.objects.filter(action="teacher_profile.change_password").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_teacher_password_change_rejects_wrong_current_password(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/profile/password",
            {
                "current_password": "not-right",
                "new_password": "N3wTeacherPw123!",
                "new_password_confirm": "N3wTeacherPw123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertIn("profile_tab=1", resp["Location"])

        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("pw12345"))
        self.assertFalse(AuditEvent.objects.filter(action="teacher_profile.change_password").exists())

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
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            f"/teach/class/{classroom.id}/update-landing-page",
            {
                "student_landing_title": "Week 4: Cutscene polish",
                "student_landing_message": "Start with your highlighted lesson, then open course links below.",
                "student_landing_hero_url": "https://example.org/landing.png",
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

        event = AuditEvent.objects.filter(action="class.update_student_landing").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)

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

    def test_teacher_can_toggle_module_session_gallery(self):
        classroom = Class.objects.create(name="Gallery Toggle", join_code="GTL12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0, gallery_enabled=True)
        Material.objects.create(
            module=module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf",
            max_upload_mb=20,
            order_index=0,
        )
        _force_login_staff_verified(self.client, self.staff)

        disable = self.client.post(f"/teach/module/{module.id}/set-gallery-enabled", {"gallery_enabled": "0"})
        self.assertEqual(disable.status_code, 302)
        module.refresh_from_db()
        self.assertFalse(module.gallery_enabled)

        enable = self.client.post(f"/teach/module/{module.id}/set-gallery-enabled", {"gallery_enabled": "1"})
        self.assertEqual(enable.status_code, 302)
        module.refresh_from_db()
        self.assertTrue(module.gallery_enabled)

    def test_teacher_can_moderate_gallery_submission(self):
        classroom = Class.objects.create(name="Gallery Moderate", join_code="GMD12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        gallery = Material.objects.create(
            module=module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        submission = Submission.objects.create(
            material=gallery,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        _force_login_staff_verified(self.client, self.staff)

        approve = self.client.post(
            f"/teach/material/{gallery.id}/submission/{submission.id}/moderate",
            {"approve": "1", "return_to": f"/teach/material/{gallery.id}/submissions"},
        )
        self.assertEqual(approve.status_code, 302)
        submission.refresh_from_db()
        self.assertTrue(submission.is_gallery_shared)

        unapprove = self.client.post(
            f"/teach/material/{gallery.id}/submission/{submission.id}/moderate",
            {"approve": "0", "return_to": f"/teach/material/{gallery.id}/submissions"},
        )
        self.assertEqual(unapprove.status_code, 302)
        submission.refresh_from_db()
        self.assertFalse(submission.is_gallery_shared)

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

    @patch("hub.views.teacher_parts.content_home.generate_authoring_templates")
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

    @patch("hub.views.teacher_parts.content_home.generate_authoring_templates")
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

    def test_teacher_can_import_markdown_syllabus_source(self):
        _force_login_staff_verified(self.client, self.staff)
        source_md = """# Field Systems Studio

Program Profile: advanced
Grade Band: Grades 11-12
Meeting Time: 90 minutes

Session 01: Signals + Baselines
## Materials
- notebook

Session 02: Drift Tests
## Materials
- laptop
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "field_systems_studio",
                        "import_course_title": "",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("field_systems.md", source_md.encode("utf-8")),
                    },
                )

                course_yaml_path = content_root / "courses" / "field_systems_studio" / "course.yaml"
                self.assertTrue(course_yaml_path.exists())
                course_yaml = course_yaml_path.read_text(encoding="utf-8")
                self.assertIn('title: "Field Systems Studio"', course_yaml)
                self.assertIn("ui_level: advanced", course_yaml)
                lesson_files = sorted((course_yaml_path.parent / "lessons").glob("*.md"))
                self.assertEqual(len(lesson_files), 2)

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        event = AuditEvent.objects.filter(action="teacher_syllabus_import.upload").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_id, "field_systems_studio")

    def test_staff_teacher_syllabus_import_creates_assigned_class_with_modules(self):
        teacher = get_user_model().objects.create_user(
            username="staff_teacher_import",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, teacher)
        source_md = """# Course Forge

Session 01: Intro Builds
## Materials
- notebook

Session 02: Final Build
## Materials
- laptop
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "course_forge",
                        "import_course_title": "",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("course_forge.md", source_md.encode("utf-8")),
                    },
                )

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])

        classroom = Class.objects.filter(name="Course Forge").order_by("-id").first()
        self.assertIsNotNone(classroom)
        self.assertTrue(
            ClassStaffAssignment.objects.filter(
                classroom=classroom,
                user=teacher,
                is_active=True,
            ).exists()
        )
        self.assertEqual(Module.objects.filter(classroom=classroom).count(), 2)
        self.assertTrue(
            Material.objects.filter(
                module__classroom=classroom,
                type=Material.TYPE_LINK,
                url__startswith="/course/course_forge/",
            ).exists()
        )

    def test_teacher_can_import_docx_syllabus_source(self):
        from ..services.authoring_templates import generate_authoring_templates

        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            template_dir = Path(temp_dir) / "templates"
            template_result = generate_authoring_templates(
                slug="docx_source",
                title="DOCX Source",
                sessions=2,
                duration=60,
                age_band="Grades 7-8",
                out_dir=template_dir,
                overwrite=True,
            )
            docx_bytes = template_result.teacher_plan_docx_path.read_bytes()
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "docx_source",
                        "import_course_title": "DOCX Source",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "template",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile(
                            "docx_source.docx",
                            docx_bytes,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    },
                )

                course_yaml_path = content_root / "courses" / "docx_source" / "course.yaml"
                self.assertTrue(course_yaml_path.exists())
                course_yaml = course_yaml_path.read_text(encoding="utf-8")
                self.assertIn('title: "DOCX Source"', course_yaml)
                lesson_files = sorted((course_yaml_path.parent / "lessons").glob("*.md"))
                self.assertEqual(len(lesson_files), 2)

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])

    def test_teacher_can_import_zip_syllabus_source(self):
        _force_login_staff_verified(self.client, self.staff)
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "swarm/COURSE_DESCRIPTION.md",
                "# Swarm Aesthetics\n\nA studio course for drift and systems.",
            )
            archive.writestr(
                "swarm/sessions/session01_swarms_systems.md",
                "# Session 01 - Swarms & Systems\n\n## Materials\n- paper\n",
            )
            archive.writestr(
                "swarm/sessions/session02_drift.md",
                "# Session 02 - Drift Studies\n\n## Materials\n- laptop\n",
            )
            archive.writestr(
                "swarm/media/01-swarm-map.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00IHDR",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "swarm_aesthetics",
                        "import_course_title": "",
                        "import_default_ui_level": "advanced",
                        "import_session_parse_mode": "verbose",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("swarm.zip", zip_buffer.getvalue(), content_type="application/zip"),
                    },
                )

                course_yaml_path = content_root / "courses" / "swarm_aesthetics" / "course.yaml"
                self.assertTrue(course_yaml_path.exists())
                course_yaml = course_yaml_path.read_text(encoding="utf-8")
                self.assertIn('title: "Swarm Aesthetics"', course_yaml)
                self.assertIn("ui_level: advanced", course_yaml)
                lesson_files = sorted((course_yaml_path.parent / "lessons").glob("*.md"))
                self.assertEqual(len(lesson_files), 2)
                first_lesson = lesson_files[0].read_text(encoding="utf-8")
                self.assertIn("support_images:", first_lesson)
                self.assertIn("lesson_support_images/s01-swarm-map.png", first_lesson)

                classroom = Class.objects.filter(name="Swarm Aesthetics").first()
                self.assertIsNotNone(classroom)
                first_module = Module.objects.filter(classroom=classroom).order_by("order_index", "id").first()
                self.assertIsNotNone(first_module)
                support_material = Material.objects.filter(
                    module=first_module,
                    type=Material.TYPE_LINK,
                    title__startswith="Support image:",
                ).first()
                self.assertIsNotNone(support_material)
                self.assertTrue((support_material.url or "").startswith("/lesson-asset/"))
                support_asset = LessonAsset.objects.filter(
                    course_slug="swarm_aesthetics",
                    lesson_slug="s01-swarms-systems",
                ).first()
                self.assertIsNotNone(support_asset)
                self.assertEqual(support_asset.original_filename, "s01-swarm-map.png")

        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])

    def test_teacher_syllabus_import_rejects_unsupported_extension(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "bad_source",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "syllabus_source": SimpleUploadedFile("bad_source.txt", b"hello"),
                    },
                )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertEqual(AuditEvent.objects.filter(action="teacher_syllabus_import.upload").count(), 0)

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
        self.assertContains(resp, "Invalid template kind.", status_code=400)

    def test_staff_download_authoring_template_rejects_traversal_slug(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/authoring-template/download?slug=..%2Fetc%2Fpasswd&kind=teacher_plan_md")
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Invalid template slug.", status_code=400)

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

    @patch("hub.views.teacher_parts.roster_class._reset_helper_class_conversations")
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

    @patch("hub.views.teacher_parts.roster_class._reset_helper_class_conversations")
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

    def test_superuser_can_set_teacher_account_active_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_active_toggle",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        disable_resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_active": "0",
            },
        )
        self.assertEqual(disable_resp.status_code, 302)
        self.assertIn("teacher_invite=1", disable_resp["Location"])
        target.refresh_from_db()
        self.assertFalse(target.is_active)

        enable_resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_active": "1",
            },
        )
        self.assertEqual(enable_resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_active)

        event = AuditEvent.objects.filter(action="teacher_account.set_active", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_set_teacher_account_superuser_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_super_toggle",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        promote_resp = self.client.post(
            "/teach/teacher-account/set-superuser",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_superuser": "1",
            },
        )
        self.assertEqual(promote_resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_superuser)

        demote_resp = self.client.post(
            "/teach/teacher-account/set-superuser",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_superuser": "0",
            },
        )
        self.assertEqual(demote_resp.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_superuser)

        event = AuditEvent.objects.filter(action="teacher_account.set_superuser", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_reset_teacher_account_password_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_pw_reset",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/teacher-account/reset-password",
            {
                "teacher_account_user_id": str(target.id),
                "teacher_account_password": "TempNewPassword123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.check_password("TempNewPassword123!"))

        event = AuditEvent.objects.filter(action="teacher_account.reset_password", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CLASSHUB_PRODUCT_NAME="Pilot Classroom Hub",
    )
    def test_superuser_can_resend_teacher_invite_from_teach(self):
        target = get_user_model().objects.create_user(
            username="teacher_resend_invite",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            email="teacher.resend@example.org",
            first_name="Resend",
        )
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/teacher-account/resend-invite",
            {
                "teacher_account_user_id": str(target.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["teacher.resend@example.org"])
        self.assertIn("Complete your Pilot Classroom Hub teacher 2FA setup", msg.subject)
        self.assertIn("/teach/2fa/setup?token=", msg.body)

        event = AuditEvent.objects.filter(action="teacher_account.resend_invite", target_id=str(target.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_disable_current_account_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(self.staff.id),
                "teacher_account_active": "0",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_active)

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

    def test_superuser_teach_home_shows_org_admin_controls(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="UI Org Actions")
        teacher = get_user_model().objects.create_user(
            username="ui_membership_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Organizations + Staff Memberships")
        self.assertContains(resp, "/teach/create-organization")
        self.assertContains(resp, "/teach/org-membership/upsert")
        self.assertContains(resp, f"/teach/org/{org.id}/rename")
        self.assertContains(resp, "Archive")
        self.assertContains(resp, "Save role")
        self.assertContains(resp, "/teach/class-organization/set")
        self.assertContains(resp, "Move class organization")
        self.assertContains(resp, "/teach/teacher-account/set-active")
        self.assertContains(resp, "/teach/teacher-account/set-superuser")
        self.assertContains(resp, "/teach/teacher-account/reset-password")
        self.assertContains(resp, "/teach/teacher-account/resend-invite")

    def test_superuser_can_create_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/create-organization",
            {"org_name": "createMPLS Programs"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        created = Organization.objects.filter(name="createMPLS Programs").first()
        self.assertIsNotNone(created)

        event = AuditEvent.objects.filter(action="organization.create", target_id=str(created.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_upsert_organization_membership_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Membership Lab")
        teacher = get_user_model().objects.create_user(
            username="membership_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

        create_resp = self.client.post(
            "/teach/org-membership/upsert",
            {
                "org_membership_org_id": str(org.id),
                "org_membership_user_id": str(teacher.id),
                "org_membership_role": OrganizationMembership.ROLE_ADMIN,
                "org_membership_active": "1",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        membership = OrganizationMembership.objects.get(organization=org, user=teacher)
        self.assertEqual(membership.role, OrganizationMembership.ROLE_ADMIN)
        self.assertTrue(membership.is_active)

        update_resp = self.client.post(
            "/teach/org-membership/upsert",
            {
                "org_membership_org_id": str(org.id),
                "org_membership_user_id": str(teacher.id),
                "org_membership_role": OrganizationMembership.ROLE_VIEWER,
                # unchecked checkbox -> inactive
            },
        )
        self.assertEqual(update_resp.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMembership.ROLE_VIEWER)
        self.assertFalse(membership.is_active)

        event = AuditEvent.objects.filter(action="organization.membership.upsert", target_id=str(membership.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_rename_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Rename Before")

        resp = self.client.post(
            f"/teach/org/{org.id}/rename",
            {"org_rename_name": "Org Rename After"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        org.refresh_from_db()
        self.assertEqual(org.name, "Org Rename After")
        event = AuditEvent.objects.filter(action="organization.rename", target_id=str(org.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_archive_organization_with_classes_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Archive Guard Org", is_active=True)
        Class.objects.create(name="Archive Guard Class", join_code="ARCH0001", organization=org)

        resp = self.client.post(f"/teach/org/{org.id}/set-active", {"is_active": "0"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        org.refresh_from_db()
        self.assertTrue(org.is_active)

    def test_superuser_can_move_class_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org_source = Organization.objects.create(name="Move Source Org", is_active=True)
        org_target = Organization.objects.create(name="Move Target Org", is_active=True)
        classroom = Class.objects.create(name="Move Class Org", join_code="MOVC0001", organization=org_source)

        resp = self.client.post(
            "/teach/class-organization/set",
            {
                "class_move_class_id": str(classroom.id),
                "class_move_org_id": str(org_target.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        classroom.refresh_from_db()
        self.assertEqual(classroom.organization_id, org_target.id)
        event = AuditEvent.objects.filter(action="class.organization.set", target_id=str(classroom.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
        self.assertEqual(event.metadata.get("organization_id"), org_target.id)

    def test_superuser_can_upsert_org_role_capability_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Role Capability Lab")

        resp = self.client.post(
            "/teach/org-role-capability/upsert",
            {
                "org_rolecap_org_id": str(org.id),
                "org_rolecap_role": OrganizationMembership.ROLE_TEACHER,
                "org_rolecap_capability": OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                "org_rolecap_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        row = OrganizationRoleCapability.objects.filter(
            organization=org,
            role=OrganizationMembership.ROLE_TEACHER,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
        ).first()
        self.assertIsNotNone(row)
        self.assertTrue(row.is_active)
        event = AuditEvent.objects.filter(action="organization.role_capability.upsert", target_id=str(row.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_upsert_class_staff_assignment_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Class Assignment Lab", join_code="ASGN0001")
        target_staff = get_user_model().objects.create_user(
            username="class_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

        create_resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_staff.id),
                "class_assignment_active": "1",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        assignment = ClassStaffAssignment.objects.get(classroom=classroom, user=target_staff)
        self.assertTrue(assignment.is_active)

        update_resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_staff.id),
                "class_assignment_active": "0",
            },
        )
        self.assertEqual(update_resp.status_code, 302)
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)

        event = AuditEvent.objects.filter(action="class.staff_assignment.upsert", target_id=str(assignment.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_assign_superuser_account_to_class(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Class Assignment Guard", join_code="ASGN0009")
        target_superuser = get_user_model().objects.create_user(
            username="class_assign_superuser_target",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )

        resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_superuser.id),
                "class_assignment_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(
            ClassStaffAssignment.objects.filter(
                classroom=classroom,
                user=target_superuser,
            ).exists()
        )

    def test_superuser_can_bulk_set_class_staff_assignments_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        class_a = Class.objects.create(name="Bulk Assign A", join_code="BULK0001")
        class_b = Class.objects.create(name="Bulk Assign B", join_code="BULK0002")
        class_c = Class.objects.create(name="Bulk Assign C", join_code="BULK0003")
        target_staff = get_user_model().objects.create_user(
            username="class_bulk_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        ClassStaffAssignment.objects.create(classroom=class_a, user=target_staff, is_active=True)
        ClassStaffAssignment.objects.create(classroom=class_b, user=target_staff, is_active=True)

        resp = self.client.post(
            "/teach/class-staff-assignment/bulk-set",
            {
                "class_assignment_bulk_user_id": str(target_staff.id),
                "class_assignment_bulk_class_ids": [str(class_b.id), str(class_c.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            ClassStaffAssignment.objects.get(classroom=class_a, user=target_staff).is_active
        )
        self.assertTrue(
            ClassStaffAssignment.objects.get(classroom=class_b, user=target_staff).is_active
        )
        self.assertTrue(
            ClassStaffAssignment.objects.get(classroom=class_c, user=target_staff).is_active
        )
        event = AuditEvent.objects.filter(action="class.staff_assignment.bulk_set", target_id=str(target_staff.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_teach_home_shows_assign_teacher_link_per_class(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Per Class Assign Link", join_code="ASGN0002")

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"/teach?org_admin=1&class_assignment_class_id={classroom.id}")

    def test_superuser_teach_class_dashboard_shows_teaching_staff_assignments_panel(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Dashboard Assignment Lab", join_code="ASGN0004")
        target_staff = get_user_model().objects.create_user(
            username="dashboard_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        ClassStaffAssignment.objects.create(classroom=classroom, user=target_staff, is_active=True)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Teaching Staff Assignments")
        self.assertContains(resp, "dashboard_assign_target")
        self.assertContains(resp, "/teach/class-staff-assignment/upsert")

    def test_teach_class_assignment_picker_only_lists_teacher_accounts(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Dashboard Assignment Filter", join_code="ASGN0010")
        teacher_user = get_user_model().objects.create_user(
            username="dashboard_teacher_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        superuser_user = get_user_model().objects.create_user(
            username="dashboard_superuser_target",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Select teacher account")
        self.assertContains(resp, f'value="{teacher_user.id}"', html=False)
        self.assertNotContains(resp, f'value="{superuser_user.id}"', html=False)

    def test_superuser_can_toggle_organization_active_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Toggle Lab", is_active=True)

        resp = self.client.post(f"/teach/org/{org.id}/set-active", {"is_active": "0"})
        self.assertEqual(resp.status_code, 302)
        org.refresh_from_db()
        self.assertFalse(org.is_active)

        event = AuditEvent.objects.filter(action="organization.set_active", target_id=str(org.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)


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

    def test_teach_home_hides_syllabus_exports_for_teacher_role(self):
        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Syllabus Exports")
        self.assertNotContains(resp, "RBAC tools")
        self.assertNotContains(resp, "Operator config snapshot")

    def test_teacher_role_cannot_export_syllabus(self):
        resp = self.client.get("/teach/syllabus-export?kind=catalog_csv")
        self.assertEqual(resp.status_code, 403)

    def test_org_admin_membership_can_export_syllabus(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        home_resp = self.client.get("/teach")
        self.assertEqual(home_resp.status_code, 200)
        self.assertContains(home_resp, "Syllabus Exports")
        self.assertContains(home_resp, "RBAC tools")
        self.assertContains(home_resp, "/teach/rbac/module-scope-grant/upsert")
        self.assertContains(home_resp, "/teach/rbac/simulate")

        resp = self.client.get("/teach/syllabus-export?kind=catalog_csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])

    def test_org_admin_can_upsert_scoped_grant_from_teach_home(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_target_org",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/upsert",
            {
                "rbac_class_id": str(self.class_a.id),
                "rbac_user_id": str(target_staff.id),
                "rbac_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_effect": ClassStaffModuleScopeGrant.EFFECT_DENY,
                "rbac_module_start": "0",
                "rbac_module_end": "1",
                "rbac_grant_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        grant = ClassStaffModuleScopeGrant.objects.filter(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start=0,
            module_order_end=1,
        ).first()
        self.assertIsNotNone(grant)
        self.assertTrue(grant.is_active)

        event = AuditEvent.objects.filter(action="rbac.scope_grant.portal_upsert", target_id=str(grant.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_can_toggle_scoped_grant_active_from_teach_home(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_toggle_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        grant = ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/set-active",
            {"rbac_grant_id": str(grant.id), "rbac_grant_active": "0"},
        )
        self.assertEqual(resp.status_code, 302)
        grant.refresh_from_db()
        self.assertFalse(grant.is_active)
        event = AuditEvent.objects.filter(action="rbac.scope_grant.portal_set_active", target_id=str(grant.id)).first()
        self.assertIsNotNone(event)

    def test_org_admin_can_simulate_rbac_from_teach_home(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_sim_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        module = Module.objects.create(classroom=self.class_a, title="Sim Module", order_index=0)

        resp = self.client.post(
            "/teach/rbac/simulate",
            {
                "rbac_sim_user_id": str(target_staff.id),
                "rbac_sim_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_sim_class_id": str(self.class_a.id),
                "rbac_sim_module_id": str(module.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("rbac_sim_result=1", resp["Location"])

        result_page = self.client.get(resp["Location"])
        self.assertEqual(result_page.status_code, 200)
        self.assertContains(result_page, "Simulation result")
        self.assertContains(result_page, "reason=")

        event = AuditEvent.objects.filter(action="rbac.simulate.portal", target_id=str(target_staff.id)).first()
        self.assertIsNotNone(event)

    def test_org_admin_bulk_simulation_matrix_scopes_to_class_org(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        viewer_staff = get_user_model().objects.create_user(
            username="rbac_bulk_viewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=viewer_staff,
            role=OrganizationMembership.ROLE_VIEWER,
            is_active=True,
        )
        outsider_staff = get_user_model().objects.create_user(
            username="rbac_bulk_outsider",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=outsider_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.get(
            "/teach",
            {
                "rbac_tools": "1",
                "rbac_bulk_class_id": str(self.class_a.id),
                "rbac_bulk_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bulk simulation result")
        self.assertContains(resp, "rbac_bulk_viewer")
        self.assertContains(resp, "role_missing_capability")
        self.assertContains(resp, "allowed=1")
        self.assertContains(resp, "denied=1")
        self.assertNotContains(resp, "rbac_bulk_outsider")

    def test_org_admin_can_filter_rbac_audit_ops_feed(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        outsider = get_user_model().objects.create_user(
            username="rbac_audit_outsider",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        event_in_scope = AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=self.class_a,
            action="rbac.scope_grant.portal_upsert",
            target_type="ClassStaffModuleScopeGrant",
            target_id="101",
            summary="In-scope scoped grant audit row",
            metadata={"class_id": self.class_a.id},
        )
        AuditEvent.objects.create(
            actor_user=self.staff,
            classroom=self.class_a,
            action="rbac.simulate.portal",
            target_type="User",
            target_id=str(self.staff.id),
            summary="In-scope simulation row",
            metadata={"class_id": self.class_a.id},
        )
        AuditEvent.objects.create(
            actor_user=outsider,
            classroom=self.class_b,
            action="rbac.scope_grant.portal_upsert",
            target_type="ClassStaffModuleScopeGrant",
            target_id="202",
            summary="Out-of-scope grant row",
            metadata={"class_id": self.class_b.id},
        )

        resp = self.client.get(
            "/teach",
            {
                "rbac_tools": "1",
                "rbac_audit_action": "rbac.scope_grant.",
                "rbac_audit_class_id": str(self.class_a.id),
                "rbac_audit_limit": "25",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "RBAC audit operations")
        self.assertContains(resp, event_in_scope.summary)
        self.assertNotContains(resp, "In-scope simulation row")
        self.assertNotContains(resp, "Out-of-scope grant row")

    def test_org_admin_can_export_rbac_policy_json(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_export_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        OrganizationRoleCapability.objects.create(
            organization=self.org_a,
            role=OrganizationMembership.ROLE_TEACHER,
            capability=OrganizationRoleCapability.CAP_POLICY_MANAGE,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=target_staff,
            capability=ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/json", resp["Content-Type"])
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(payload.get("schema_version"), "classhub.rbac_policy.v1")
        self.assertTrue(any(org.get("name") == self.org_a.name for org in payload.get("organizations", [])))
        self.assertTrue(
            any(grant.get("class_join_code") == self.class_a.join_code for grant in payload.get("scoped_grants", []))
        )
        event = AuditEvent.objects.filter(action="rbac.policy.export").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_can_import_rbac_policy_json(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_import_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [
                {
                    "name": self.org_a.name,
                    "role_capabilities": [
                        {
                            "role": OrganizationMembership.ROLE_VIEWER,
                            "capability": OrganizationRoleCapability.CAP_CLASS_VIEW,
                            "is_active": True,
                        }
                    ],
                }
            ],
            "scoped_grants": [
                {
                    "class_join_code": self.class_a.join_code,
                    "username": target_staff.username,
                    "capability": ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
                    "effect": ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                    "module_order_start": 0,
                    "module_order_end": 0,
                    "is_active": True,
                }
            ],
        }

        resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertTrue(
            OrganizationRoleCapability.objects.filter(
                organization=self.org_a,
                role=OrganizationMembership.ROLE_VIEWER,
                capability=OrganizationRoleCapability.CAP_CLASS_VIEW,
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            ClassStaffModuleScopeGrant.objects.filter(
                classroom=self.class_a,
                user=target_staff,
                capability=ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
                effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                module_order_start=0,
                module_order_end=0,
                is_active=True,
            ).exists()
        )
        event = AuditEvent.objects.filter(action="rbac.policy.import").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_org_admin_policy_export_includes_custom_roles_and_assignments(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_export_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        role = OrganizationCustomRole.objects.create(
            organization=self.org_a,
            slug="district_exporter",
            name="District Exporter",
            description="Can export curriculum policy bundles",
            is_active=True,
        )
        OrganizationCustomRoleCapability.objects.create(
            role=role,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
            is_active=True,
        )
        OrganizationCustomRoleAssignment.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=role,
            is_active=True,
        )

        resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(any(row.get("slug") == "district_exporter" for row in payload.get("custom_roles", [])))
        self.assertTrue(
            any(
                row.get("username") == target_staff.username and row.get("role_slug") == "district_exporter"
                for row in payload.get("custom_role_assignments", [])
            )
        )

    def test_org_admin_policy_import_can_upsert_custom_roles_and_assignments(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_import_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [],
            "scoped_grants": [],
            "custom_roles": [
                {
                    "organization_name": self.org_a.name,
                    "slug": "ops_observer",
                    "name": "Ops Observer",
                    "description": "Read-only operations observer",
                    "is_active": True,
                    "capabilities": [
                        {"capability": OrganizationRoleCapability.CAP_CLASS_VIEW, "is_active": True},
                    ],
                }
            ],
            "custom_role_assignments": [
                {
                    "organization_name": self.org_a.name,
                    "role_slug": "ops_observer",
                    "username": target_staff.username,
                    "is_active": True,
                }
            ],
        }

        resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(resp.status_code, 302)
        role = OrganizationCustomRole.objects.filter(organization=self.org_a, slug="ops_observer").first()
        self.assertIsNotNone(role)
        self.assertTrue(
            OrganizationCustomRoleCapability.objects.filter(
                role=role,
                capability=OrganizationRoleCapability.CAP_CLASS_VIEW,
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            OrganizationCustomRoleAssignment.objects.filter(
                organization=self.org_a,
                role=role,
                user=target_staff,
                is_active=True,
            ).exists()
        )

    def test_org_admin_can_upsert_custom_roles_from_teach_home(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_custom_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        role_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "district_exporter",
                "rbac_custom_role_name": "District Exporter",
                "rbac_custom_role_description": "District export rights",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(role_resp.status_code, 302)
        role = OrganizationCustomRole.objects.filter(organization=self.org_a, slug="district_exporter").first()
        self.assertIsNotNone(role)

        cap_resp = self.client.post(
            "/teach/rbac/custom-role/capability/upsert",
            {
                "rbac_custom_role_cap_org_id": str(self.org_a.id),
                "rbac_custom_role_cap_slug": "district_exporter",
                "rbac_custom_role_capability": OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                "rbac_custom_role_cap_active": "1",
            },
        )
        self.assertEqual(cap_resp.status_code, 302)
        self.assertTrue(
            OrganizationCustomRoleCapability.objects.filter(
                role=role,
                capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                is_active=True,
            ).exists()
        )

        assign_resp = self.client.post(
            "/teach/rbac/custom-role/assignment/upsert",
            {
                "rbac_custom_role_assign_org_id": str(self.org_a.id),
                "rbac_custom_role_assign_slug": "district_exporter",
                "rbac_custom_role_assign_user_id": str(target_staff.id),
                "rbac_custom_role_assign_active": "1",
            },
        )
        self.assertEqual(assign_resp.status_code, 302)
        self.assertTrue(
            OrganizationCustomRoleAssignment.objects.filter(
                organization=self.org_a,
                role=role,
                user=target_staff,
                is_active=True,
            ).exists()
        )
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role.portal_upsert").exists())
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role_capability.portal_upsert").exists())
        self.assertTrue(AuditEvent.objects.filter(action="organization.custom_role_assignment.portal_upsert").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)
    def test_policy_approval_workflow_requires_separate_reviewer(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        request_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "review_gated_role",
                "rbac_custom_role_name": "Review Gated Role",
                "rbac_custom_role_description": "Requires approval",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(request_resp.status_code, 302)
        change = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT
        ).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertFalse(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="review_gated_role").exists())

        self_review_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(self_review_resp.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)

        reviewer = get_user_model().objects.create_user(
            username="rbac_change_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_ADMIN,
            is_active=True,
        )
        _force_login_staff_verified(self.client, reviewer)
        approve_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
                "rbac_change_review_note": "Looks good.",
            },
        )
        self.assertEqual(approve_resp.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_APPROVED)
        self.assertEqual(change.reviewed_by_id, reviewer.id)
        self.assertTrue(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="review_gated_role").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)
    def test_policy_import_is_queued_and_applied_after_approval(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])
        target_staff = get_user_model().objects.create_user(
            username="rbac_policy_queue_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        policy = {
            "schema_version": "classhub.rbac_policy.v1",
            "organizations": [],
            "scoped_grants": [],
            "custom_roles": [
                {
                    "organization_name": self.org_a.name,
                    "slug": "queued_policy_role",
                    "name": "Queued Policy Role",
                    "description": "Policy import via approval",
                    "is_active": True,
                    "capabilities": [
                        {"capability": OrganizationRoleCapability.CAP_CLASS_VIEW, "is_active": True},
                    ],
                }
            ],
            "custom_role_assignments": [
                {
                    "organization_name": self.org_a.name,
                    "role_slug": "queued_policy_role",
                    "username": target_staff.username,
                    "is_active": True,
                }
            ],
        }

        queue_resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    json.dumps(policy).encode("utf-8"),
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(queue_resp.status_code, 302)
        request_row = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_POLICY_IMPORT
        ).first()
        self.assertIsNotNone(request_row)
        self.assertEqual(request_row.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertFalse(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="queued_policy_role").exists())

        reviewer = get_user_model().objects.create_user(
            username="rbac_policy_queue_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_ADMIN,
            is_active=True,
        )
        _force_login_staff_verified(self.client, reviewer)
        approve_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(request_row.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(approve_resp.status_code, 302)
        request_row.refresh_from_db()
        self.assertEqual(request_row.status, RbacPolicyChangeRequest.STATUS_APPROVED)
        self.assertTrue(OrganizationCustomRole.objects.filter(organization=self.org_a, slug="queued_policy_role").exists())

    @override_settings(CLASSHUB_RBAC_POLICY_APPROVAL_REQUIRED=True)
    def test_teacher_with_export_capability_cannot_review_policy_change_request(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        request_resp = self.client.post(
            "/teach/rbac/custom-role/upsert",
            {
                "rbac_custom_role_org_id": str(self.org_a.id),
                "rbac_custom_role_slug": "restricted_review_target",
                "rbac_custom_role_name": "Restricted Review Target",
                "rbac_custom_role_description": "Queued for review",
                "rbac_custom_role_active": "1",
            },
        )
        self.assertEqual(request_resp.status_code, 302)
        change = RbacPolicyChangeRequest.objects.filter(
            request_type=RbacPolicyChangeRequest.REQUEST_CUSTOM_ROLE_UPSERT
        ).first()
        self.assertIsNotNone(change)
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)

        reviewer = get_user_model().objects.create_user(
            username="rbac_export_only_reviewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=reviewer,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        export_only_role = OrganizationCustomRole.objects.create(
            organization=self.org_a,
            slug="review_export_only",
            name="Review Export Only",
            description="Can export but cannot review approvals",
            is_active=True,
        )
        OrganizationCustomRoleCapability.objects.create(
            role=export_only_role,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
            is_active=True,
        )
        OrganizationCustomRoleAssignment.objects.create(
            organization=self.org_a,
            role=export_only_role,
            user=reviewer,
            is_active=True,
        )

        _force_login_staff_verified(self.client, reviewer)
        review_resp = self.client.post(
            "/teach/rbac/change-request/review",
            {
                "rbac_change_review_id": str(change.id),
                "rbac_change_review_decision": "approve",
            },
        )
        self.assertEqual(review_resp.status_code, 302)
        self.assertIn("owners%2Fadmins", review_resp["Location"])
        change.refresh_from_db()
        self.assertEqual(change.status, RbacPolicyChangeRequest.STATUS_PENDING)
        self.assertIsNone(change.reviewed_by_id)
        self.assertFalse(
            OrganizationCustomRole.objects.filter(organization=self.org_a, slug="restricted_review_target").exists()
        )

    def test_teacher_role_cannot_import_or_export_rbac_policy(self):
        export_resp = self.client.get("/teach/rbac/policy/export")
        self.assertEqual(export_resp.status_code, 302)
        self.assertIn("/teach?error=", export_resp["Location"])

        import_resp = self.client.post(
            "/teach/rbac/policy/import",
            {
                "rbac_policy_file": SimpleUploadedFile(
                    "rbac_policy.json",
                    b'{"schema_version":"classhub.rbac_policy.v1","organizations":[],"scoped_grants":[]}',
                    content_type="application/json",
                )
            },
        )
        self.assertEqual(import_resp.status_code, 302)
        self.assertIn("/teach?error=", import_resp["Location"])
        self.assertFalse(AuditEvent.objects.filter(action="rbac.policy.import").exists())

    def test_teacher_role_cannot_upsert_scoped_grant_from_teach_home(self):
        target_staff = get_user_model().objects.create_user(
            username="rbac_blocked_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=target_staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

        resp = self.client.post(
            "/teach/rbac/module-scope-grant/upsert",
            {
                "rbac_class_id": str(self.class_a.id),
                "rbac_user_id": str(target_staff.id),
                "rbac_capability": ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                "rbac_effect": ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                "rbac_module_start": "0",
                "rbac_module_end": "0",
                "rbac_grant_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(
            ClassStaffModuleScopeGrant.objects.filter(
                classroom=self.class_a,
                user=target_staff,
                capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
                effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
                module_order_start=0,
                module_order_end=0,
            ).exists()
        )

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

    def test_viewer_membership_cannot_set_retention_preset(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/set-retention-preset",
            {"retention_preset": Class.RETENTION_KEEP_SEMESTER},
        )
        self.assertEqual(resp.status_code, 403)

    def test_viewer_membership_cannot_mark_session_completed(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        module = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/mark-session-completed",
            {"student_id": str(student.id), "module_id": str(module.id)},
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_submission_view_grant_limits_material_submissions_route(self):
        module_1 = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        module_2 = Module.objects.create(classroom=self.class_a, title="Session 2", order_index=1)
        material_1 = Material.objects.create(
            module=module_1,
            title="Upload 1",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        material_2 = Material.objects.create(
            module=module_2,
            title="Upload 2",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        submission_1 = Submission.objects.create(
            material=material_1,
            student=student,
            original_filename="one.sb3",
            file=SimpleUploadedFile("one.sb3", _sample_sb3_bytes()),
        )
        submission_2 = Submission.objects.create(
            material=material_2,
            student=student,
            original_filename="two.sb3",
            file=SimpleUploadedFile("two.sb3", _sample_sb3_bytes()),
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        allowed = self.client.get(f"/teach/material/{material_1.id}/submissions")
        self.assertEqual(allowed.status_code, 200)
        blocked = self.client.get(f"/teach/material/{material_2.id}/submissions")
        self.assertEqual(blocked.status_code, 404)

        allowed_download = self.client.get(f"/submission/{submission_1.id}/download")
        self.assertEqual(allowed_download.status_code, 200)
        blocked_download = self.client.get(f"/submission/{submission_2.id}/download")
        self.assertEqual(blocked_download.status_code, 403)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_submission_delete_grant_limits_gallery_moderation(self):
        module_1 = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        module_2 = Module.objects.create(classroom=self.class_a, title="Session 2", order_index=1)
        gallery_1 = Material.objects.create(
            module=module_1,
            title="Gallery 1",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        gallery_2 = Material.objects.create(
            module=module_2,
            title="Gallery 2",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        submission_1 = Submission.objects.create(
            material=gallery_1,
            student=student,
            original_filename="one.sb3",
            file=SimpleUploadedFile("one.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        submission_2 = Submission.objects.create(
            material=gallery_2,
            student=student,
            original_filename="two.sb3",
            file=SimpleUploadedFile("two.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        allowed = self.client.post(
            f"/teach/material/{gallery_1.id}/submission/{submission_1.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(allowed.status_code, 302)
        blocked = self.client.post(
            f"/teach/material/{gallery_2.id}/submission/{submission_2.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(blocked.status_code, 403)

    def test_viewer_membership_cannot_resolve_stuck_flag(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        module = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        StudentEvent.objects.create(
            classroom=self.class_a,
            student=student,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/resolve-stuck",
            {"student_id": str(student.id), "module_id": str(module.id)},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            StudentEvent.objects.filter(
                classroom=self.class_a,
                student=student,
                event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
            ).exists()
        )

    def test_viewer_membership_cannot_resolve_delete_request(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        StudentEvent.objects.create(
            classroom=self.class_a,
            student=student,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            source="test",
            details={},
        )

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/resolve-delete-request",
            {"student_id": str(student.id)},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            StudentEvent.objects.filter(
                classroom=self.class_a,
                student=student,
                event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
            ).exists()
        )

    def test_viewer_membership_cannot_add_support_tag(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")

        resp = self.client.post(
            f"/teach/class/{self.class_a.id}/support-tag/add",
            {"student_id": str(student.id), "tag": StudentSupportTag.TAG_PREFERS_QUIET},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            StudentSupportTag.objects.filter(
                classroom=self.class_a,
                student=student,
                tag=StudentSupportTag.TAG_PREFERS_QUIET,
            ).exists()
        )

    def test_viewer_membership_certificate_page_hides_mark_completed_form(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")

        resp = self.client.get(f"/teach/class/{self.class_a.id}/certificate-eligibility")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "/mark-session-completed")
        self.assertContains(resp, "Read-only role")

    def test_create_class_assigns_default_org_for_membership_staff(self):
        resp = self.client.post("/teach/create-class", {"name": "New Alpha Class"})
        self.assertEqual(resp.status_code, 302)
        created = Class.objects.filter(name="New Alpha Class").order_by("-id").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.organization_id, self.org_a.id)
        self.assertTrue(
            ClassStaffAssignment.objects.filter(
                classroom=created,
                user=self.staff,
                is_active=True,
            ).exists()
        )

    def test_teach_home_prioritizes_assigned_classes_within_org_access(self):
        Class.objects.create(name="Alpha Unassigned", join_code="ALUN1234", organization=self.org_a)
        assigned = Class.objects.create(name="Zulu Assigned", join_code="ZUAS1234", organization=self.org_a)
        ClassStaffAssignment.objects.create(classroom=assigned, user=self.staff, is_active=True)

        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha Unassigned")
        self.assertContains(resp, "Zulu Assigned")

        html = resp.content.decode("utf-8")
        self.assertLess(html.find("Zulu Assigned"), html.find("Alpha Unassigned"))
        self.assertIn("Assigned", html)

    def test_teach_lessons_class_filter_lists_assigned_first(self):
        Class.objects.create(name="Alpha Unassigned", join_code="ALUN5678", organization=self.org_a)
        assigned = Class.objects.create(name="Zulu Assigned", join_code="ZUAS5678", organization=self.org_a)
        ClassStaffAssignment.objects.create(classroom=assigned, user=self.staff, is_active=True)

        resp = self.client.get("/teach/lessons")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertLess(html.find("Zulu Assigned"), html.find("Alpha Unassigned"))

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

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_hard_org_boundary_blocks_legacy_staff_without_membership(self):
        legacy_staff = get_user_model().objects.create_user(
            username="legacy_staff_hard",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, legacy_staff)

        teach_resp = self.client.get("/teach")
        self.assertEqual(teach_resp.status_code, 200)
        self.assertNotContains(teach_resp, "Alpha Cohort")
        blocked_resp = self.client.get(f"/teach/class/{self.class_a.id}")
        self.assertEqual(blocked_resp.status_code, 404)

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_hard_org_boundary_blocks_class_create_without_membership(self):
        legacy_staff = get_user_model().objects.create_user(
            username="legacy_staff_create",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, legacy_staff)
        resp = self.client.post("/teach/create-class", {"name": "Should Not Create"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Class.objects.filter(name="Should Not Create").exists())

    def test_non_superuser_staff_cannot_manage_organizations_from_teach(self):
        resp = self.client.post("/teach/create-organization", {"org_name": "Blocked Org"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(Organization.objects.filter(name="Blocked Org").exists())

        rename_org = Organization.objects.create(name="Blocked Rename Org")
        rename_resp = self.client.post(
            f"/teach/org/{rename_org.id}/rename",
            {"org_rename_name": "Should Not Rename"},
        )
        self.assertEqual(rename_resp.status_code, 302)
        self.assertIn("/teach?error=", rename_resp["Location"])
        rename_org.refresh_from_db()
        self.assertEqual(rename_org.name, "Blocked Rename Org")

        class_move_resp = self.client.post(
            "/teach/class-organization/set",
            {
                "class_move_class_id": str(self.class_a.id),
                "class_move_org_id": str(self.org_b.id),
            },
        )
        self.assertEqual(class_move_resp.status_code, 302)
        self.assertIn("/teach?error=", class_move_resp["Location"])
        self.class_a.refresh_from_db()
        self.assertEqual(self.class_a.organization_id, self.org_a.id)

        org = Organization.objects.create(name="Blocked Membership Org")
        resp_membership = self.client.post(
            "/teach/org-membership/upsert",
            {
                "org_membership_org_id": str(org.id),
                "org_membership_user_id": str(self.staff.id),
                "org_membership_role": OrganizationMembership.ROLE_TEACHER,
                "org_membership_active": "1",
            },
        )
        self.assertEqual(resp_membership.status_code, 302)
        self.assertIn("/teach?error=", resp_membership["Location"])
        self.assertFalse(OrganizationMembership.objects.filter(organization=org, user=self.staff).exists())

        rolecap_resp = self.client.post(
            "/teach/org-role-capability/upsert",
            {
                "org_rolecap_org_id": str(org.id),
                "org_rolecap_role": OrganizationMembership.ROLE_TEACHER,
                "org_rolecap_capability": OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                "org_rolecap_active": "1",
            },
        )
        self.assertEqual(rolecap_resp.status_code, 302)
        self.assertIn("/teach?error=", rolecap_resp["Location"])
        self.assertFalse(
            OrganizationRoleCapability.objects.filter(
                organization=org,
                role=OrganizationMembership.ROLE_TEACHER,
                capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
            ).exists()
        )

    def test_non_superuser_staff_cannot_manage_class_assignments_from_teach(self):
        target_staff = get_user_model().objects.create_user(
            username="blocked_class_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        upsert_resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(self.class_a.id),
                "class_assignment_user_id": str(target_staff.id),
                "class_assignment_active": "1",
            },
        )
        self.assertEqual(upsert_resp.status_code, 302)
        self.assertIn("/teach?error=", upsert_resp["Location"])
        self.assertFalse(
            ClassStaffAssignment.objects.filter(
                classroom=self.class_a,
                user=target_staff,
                is_active=True,
            ).exists()
        )

        bulk_resp = self.client.post(
            "/teach/class-staff-assignment/bulk-set",
            {
                "class_assignment_bulk_user_id": str(target_staff.id),
                "class_assignment_bulk_class_ids": [str(self.class_a.id)],
            },
        )
        self.assertEqual(bulk_resp.status_code, 302)
        self.assertIn("/teach?error=", bulk_resp["Location"])
        self.assertFalse(
            ClassStaffAssignment.objects.filter(
                classroom=self.class_a,
                user=target_staff,
            ).exists()
        )

    def test_non_superuser_staff_cannot_manage_teacher_accounts_from_teach(self):
        target_staff = get_user_model().objects.create_user(
            username="blocked_teacher_account_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
            email="blocked.target@example.org",
        )
        set_active_resp = self.client.post(
            "/teach/teacher-account/set-active",
            {
                "teacher_account_user_id": str(target_staff.id),
                "teacher_account_active": "0",
            },
        )
        self.assertEqual(set_active_resp.status_code, 302)
        self.assertIn("/teach?error=", set_active_resp["Location"])
        target_staff.refresh_from_db()
        self.assertTrue(target_staff.is_active)

        set_superuser_resp = self.client.post(
            "/teach/teacher-account/set-superuser",
            {
                "teacher_account_user_id": str(target_staff.id),
                "teacher_account_superuser": "1",
            },
        )
        self.assertEqual(set_superuser_resp.status_code, 302)
        self.assertIn("/teach?error=", set_superuser_resp["Location"])
        target_staff.refresh_from_db()
        self.assertFalse(target_staff.is_superuser)

        reset_password_resp = self.client.post(
            "/teach/teacher-account/reset-password",
            {
                "teacher_account_user_id": str(target_staff.id),
                "teacher_account_password": "new-pass-123-ABC",
            },
        )
        self.assertEqual(reset_password_resp.status_code, 302)
        self.assertIn("/teach?error=", reset_password_resp["Location"])
        target_staff.refresh_from_db()
        self.assertTrue(target_staff.check_password("pw12345"))

        resend_invite_resp = self.client.post(
            "/teach/teacher-account/resend-invite",
            {"teacher_account_user_id": str(target_staff.id)},
        )
        self.assertEqual(resend_invite_resp.status_code, 302)
        self.assertIn("/teach?error=", resend_invite_resp["Location"])
        self.assertFalse(AuditEvent.objects.filter(action="teacher_account.resend_invite").exists())

    def test_non_superuser_staff_can_update_own_profile(self):
        resp = self.client.post(
            "/teach/profile/update",
            {
                "first_name": "Org",
                "last_name": "Teacher",
                "email": "org.teacher@example.org",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Org")
        self.assertEqual(self.staff.email, "org.teacher@example.org")
