from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class TeacherPortalHelperOpsTests(TeacherPortalBaseTests):
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
        self.assertContains(resp, "Export remote helper snapshot:")
        self.assertContains(resp, f"/teach/class/{classroom.id}/export-helper-remote-snapshot?format=json")
        self.assertContains(resp, f"/teach/class/{classroom.id}/export-helper-remote-snapshot?format=csv")

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

    @patch("hub.views.teacher_parts.roster_helper_exports.fetch_remote_compute_status")
    def test_teacher_can_export_remote_helper_snapshot_json(self, status_mock):
        classroom = Class.objects.create(name="Partner Session Export", join_code="GPU10001")
        status_mock.return_value = HelperRemoteComputeStatusResult(
            ok=True,
            feature_enabled=True,
            paid_usage_acknowledged=True,
            backend_configured=True,
            active=True,
            active_for_class=True,
            use_remote_backend=True,
            state="ready",
            class_id=classroom.id,
            requested_by=self.staff.username,
            requested_at="2099-04-08T12:00:00+00:00",
            expires_at="2099-04-08T13:30:00+00:00",
            remaining_minutes=90,
            provider_label="thunder-orchestration",
            provider_request_id="provider-req-1",
            provider_adapter="thunder_webhook",
            control_url_configured=True,
            healthcheck_url_configured=True,
            auto_stop_on_idle=True,
            idle_timeout_seconds=600,
            status_detail="Warm probe passed.",
            last_transition_at="2099-04-08T12:05:00+00:00",
            last_healthcheck_at="2099-04-08T12:05:30+00:00",
            last_routed_at="2099-04-08T12:07:00+00:00",
            activation_count=3,
            ready_transition_count=2,
            avg_ready_seconds=18,
            remote_route_count=4,
            fallback_local_count=1,
            degraded_transition_count=2,
            provider_unreachable_count=1,
            unused_activation_count=1,
            last_activation_at="2099-04-08T12:00:00+00:00",
            last_ready_at="2099-04-08T12:05:00+00:00",
            last_fallback_at="2099-04-08T12:06:00+00:00",
            request_id="helper-status-req-1",
            status_code=200,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get(f"/teach/class/{classroom.id}/export-helper-remote-snapshot?format=json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Content-Type"], "application/json")
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(payload["state"], "ready")
        self.assertEqual(payload["request_id"], "helper-status-req-1")
        self.assertEqual(payload["remote_route_count"], 4)

        event = AuditEvent.objects.filter(action="class.remote_helper_snapshot_export").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("format"), "json")
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-status-req-1")
        self.assertEqual(event.metadata.get("state"), "ready")
        self.assertTrue(event.metadata.get("ok"))

    @patch("hub.views.teacher_parts.roster_helper_exports.fetch_remote_compute_status")
    def test_teacher_can_export_remote_helper_snapshot_csv(self, status_mock):
        classroom = Class.objects.create(name="Partner Session Export CSV", join_code="GPU10002")
        status_mock.return_value = HelperRemoteComputeStatusResult(
            ok=False,
            state="degraded",
            class_id=classroom.id,
            status_detail="Healthcheck timeout.",
            last_error_code="provider_unreachable",
            request_id="helper-status-csv-1",
            error_code="provider_unreachable",
            status_code=503,
        )

        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get(f"/teach/class/{classroom.id}/export-helper-remote-snapshot?format=csv")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        body = resp.content.decode("utf-8")
        self.assertIn("field,value", body)
        self.assertIn("request_id,helper-status-csv-1", body)
        self.assertIn("error_code,provider_unreachable", body)

        event = AuditEvent.objects.filter(action="class.remote_helper_snapshot_export").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, classroom.id)
        self.assertEqual(event.metadata.get("format"), "csv")
        self.assertEqual(event.metadata.get("helper_request_id"), "helper-status-csv-1")
        self.assertEqual(event.metadata.get("state"), "degraded")
        self.assertFalse(event.metadata.get("ok"))
