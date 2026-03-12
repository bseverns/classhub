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

    @patch("hub.views.teacher_parts.content_data_lifespan.fetch_rag_status")
    def test_dashboard_renders_rag_panel_from_helper_status(self, rag_status_mock):
        rag_status_mock.return_value = HelperRagStatusResult(
            ok=True,
            rag_enabled=True,
            index_ready=True,
            indexed_chunk_count=42,
            reference_source_count=1,
            last_index_built_at="2026-03-06T12:00:00+00:00",
            reference_sources=[
                {
                    "reference_key": "piper_scratch",
                    "chunk_count": 42,
                    "last_indexed_at": "2026-03-06T12:00:00+00:00",
                }
            ],
            configured_reference_keys=["piper_scratch"],
            student_data_excluded_from_index=True,
            status_code=200,
        )
        _force_login_staff_verified(self.client, self.superuser)

        resp = self.client.get("/teach/data-lifespan")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Local RAG index posture")
        self.assertContains(resp, "RAG enabled and indexed")
        self.assertContains(resp, "Student uploads and student PII are excluded from the RAG index.")
        self.assertContains(resp, "piper_scratch")

    def test_superuser_can_export_data_lifespan_json_snapshot(self):
        _force_login_staff_verified(self.client, self.superuser)
        resp = self.client.get("/teach/data-lifespan/export?format=json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        self.assertIn("attachment; filename=", resp["Content-Disposition"])
        payload = resp.json()
        self.assertIn("snapshot", payload)
        self.assertIn("rag_status", payload)
        self.assertIn("policy_overdue_total", payload["snapshot"])

        event = AuditEvent.objects.filter(action="data_lifespan.snapshot_export").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_id, "json")
        self.assertEqual(str(event.metadata.get("format")), "json")

    def test_superuser_can_export_data_lifespan_csv_snapshot(self):
        _force_login_staff_verified(self.client, self.superuser)
        resp = self.client.get("/teach/data-lifespan/export?format=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", resp["Content-Disposition"])
        self.assertIn("field,value", resp.content.decode("utf-8"))
        self.assertIn("policy_overdue_total", resp.content.decode("utf-8"))
        self.assertIn("rag_status", resp.content.decode("utf-8"))

        event = AuditEvent.objects.filter(action="data_lifespan.snapshot_export").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_id, "csv")
        self.assertEqual(str(event.metadata.get("format")), "csv")

    def test_data_lifespan_export_rejects_invalid_format(self):
        _force_login_staff_verified(self.client, self.superuser)
        resp = self.client.get("/teach/data-lifespan/export?format=pdf")
        self.assertEqual(resp.status_code, 400)

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_viewer_membership_cannot_view_data_lifespan_dashboard(self):
        _force_login_staff_verified(self.client, self.viewer)
        resp = self.client.get("/teach/data-lifespan")
        self.assertEqual(resp.status_code, 403)

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_viewer_membership_cannot_export_data_lifespan_snapshot(self):
        _force_login_staff_verified(self.client, self.viewer)
        resp = self.client.get("/teach/data-lifespan/export?format=json")
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

    @override_settings(
        CLASSHUB_CERTIFICATE_MIN_SESSIONS=1,
        CLASSHUB_CERTIFICATE_MIN_ARTIFACTS=1,
    )
    def test_outcome_snapshot_and_certificate_rows_share_class_scoped_counts(self):
        from ..services.teacher_roster_class import _build_outcome_snapshot, build_certificate_eligibility_rows

        classroom = Class.objects.create(name="Outcome Scope A", join_code="OSCOPEA1")
        other_classroom = Class.objects.create(name="Outcome Scope B", join_code="OSCOPEB1")
        ada = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        StudentOutcomeEvent.objects.create(
            classroom=classroom,
            student=ada,
            event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
            source="test",
            details={},
        )
        # Mismatched classroom row should not leak into class A snapshots.
        StudentOutcomeEvent.objects.create(
            classroom=other_classroom,
            student=ada,
            event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            source="test",
            details={},
        )

        summary = build_certificate_eligibility_rows(
            classroom=classroom,
            students=[ada],
            certificate_min_sessions=1,
            certificate_min_artifacts=1,
        )
        snapshot = _build_outcome_snapshot(classroom=classroom, students=[ada])
        row = summary["rows"][0]
        top = snapshot["top_students"][0]

        self.assertEqual(row["session_count"], 1)
        self.assertEqual(row["artifact_count"], 0)
        self.assertEqual(row["certificate_eligible"], False)
        self.assertEqual(snapshot["total_sessions"], 1)
        self.assertEqual(snapshot["total_artifacts"], 0)
        self.assertEqual(snapshot["eligible_students"], summary["eligible_students"])
        self.assertEqual(top["session_count"], row["session_count"])
        self.assertEqual(top["artifact_count"], row["artifact_count"])




