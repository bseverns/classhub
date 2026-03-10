from ._shared import *  # noqa: F401,F403

class JoinClassTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Join Test", join_code="JOIN1234")

    @override_settings(
        SECRET_KEY="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        DEVICE_HINT_SIGNING_KEY="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    def test_join_prefers_device_hint_cookie_with_dedicated_key(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        hinted = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.assertLess(oldest.id, hinted.id)

        self.client.cookies["classhub_student_hint"] = signing.dumps(
            {"class_id": self.classroom.id, "student_id": hinted.id},
            key="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            salt="classhub.student-device-hint",
        )
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("student_id"), hinted.id)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "device_hint")

    @override_settings(
        SECRET_KEY="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        DEVICE_HINT_SIGNING_KEY="device-hint-key-bbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    def test_join_ignores_device_hint_cookie_signed_with_wrong_key(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        hinted = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.assertLess(oldest.id, hinted.id)

        # Cookie uses the main Django secret (wrong key for device hint signing).
        self.client.cookies["classhub_student_hint"] = signing.dumps(
            {"class_id": self.classroom.id, "student_id": hinted.id},
            key="primary-secret-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            salt="classhub.student-device-hint",
        )
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("student_id"), oldest.id)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "name_match")

    def test_join_same_name_without_return_code_reuses_existing_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1["Cache-Control"], "no-store")
        self.assertEqual(r1["Pragma"], "no-cache")
        first_id = self.client.session.get("student_id")
        first_event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(first_event)
        self.assertEqual(first_event.event_type, StudentEvent.EVENT_CLASS_JOIN)
        self.assertEqual(first_event.ip_address, "127.0.0.0")

        # Simulate different machine/browser (no prior device cookie).
        other = Client()
        r2 = other.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        second_id = other.session.get("student_id")

        self.assertEqual(first_id, second_id)
        self.assertTrue(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        second_event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(second_event)
        self.assertEqual(second_event.event_type, StudentEvent.EVENT_REJOIN_DEVICE_HINT)
        self.assertEqual(second_event.details.get("join_mode"), "name_match")

    def test_join_same_device_without_return_code_reuses_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")

        # Student logs out, then re-joins from the same browser/device.
        self.client.get("/logout")
        r2 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")

        self.assertEqual(first_id, second_id)
        self.assertTrue(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_REJOIN_DEVICE_HINT)

    def test_join_same_device_with_different_name_creates_new_identity(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")

        self.client.get("/logout")
        r2 = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ben"}),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")

        self.assertNotEqual(first_id, second_id)
        self.assertFalse(r2.json().get("rejoined"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 2)

    def test_join_name_match_avoids_new_row_when_duplicates_already_exist(self):
        oldest = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        StudentIdentity.objects.create(classroom=self.classroom, display_name="ADA")

        other = Client()
        resp = other.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("rejoined"))
        self.assertEqual(other.session.get("student_id"), oldest.id)
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom, display_name__iexact="ada").count(), 2)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.details.get("join_mode"), "name_match")

    def test_join_reuses_identity_when_return_code_matches(self):
        r1 = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        first_id = self.client.session.get("student_id")
        first_code = r1.json().get("return_code")
        self.assertTrue(first_code)

        r2 = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "ada",
                    "return_code": first_code,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        second_id = self.client.session.get("student_id")
        self.assertTrue(r2.json().get("rejoined"))

        self.assertEqual(first_id, second_id)
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_REJOIN_RETURN_CODE)

    def test_join_with_invalid_return_code_is_rejected(self):
        resp = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "Ada",
                    "return_code": "ZZZZZZ",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invalid_return_code")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    @override_settings(CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=True)
    def test_join_requires_return_code_for_existing_name_when_strict_rejoin_enabled(self):
        StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "return_code_required")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)

    def test_join_event_details_do_not_store_display_name_or_class_code(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        resp = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_CLASS_JOIN)
        self.assertNotIn("display_name", event.details)
        self.assertNotIn("class_code", event.details)
        self.assertEqual(event.details.get("join_mode"), "new")

    def test_join_rotates_session_key_and_csrf_token(self):
        # Seed an existing session + CSRF token before join.
        self.client.get("/")
        session = self.client.session
        session["prejoin_marker"] = "keep"
        session.save()
        before_session_key = session.session_key
        before_csrf = self.client.cookies["csrftoken"].value

        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        resp = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        after_session = self.client.session
        after_session_key = after_session.session_key
        after_csrf = self.client.cookies["csrftoken"].value

        self.assertNotEqual(before_session_key, after_session_key)
        self.assertNotEqual(before_csrf, after_csrf)
        self.assertEqual(after_session.get("prejoin_marker"), "keep")
        self.assertIsNotNone(after_session.get("student_id"))
        self.assertEqual(after_session.get("class_id"), self.classroom.id)

    def test_join_enforces_csrf_for_cross_site_posts(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        strict_client = Client(enforce_csrf_checks=True)

        denied = strict_client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(denied.status_code, 403)

        strict_client.get("/")
        csrf_token = strict_client.cookies["csrftoken"].value
        allowed = strict_client.post(
            "/join",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(allowed.status_code, 200)

    def test_invite_url_renders_join_page_with_token(self):
        invite = ClassInviteLink.objects.create(classroom=self.classroom, label="Paid cohort")

        resp = self.client.get(f"/invite/{invite.token}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'value="{invite.token}"')

    def test_join_allows_invite_token_without_class_code(self):
        invite = ClassInviteLink.objects.create(classroom=self.classroom, label="Paid cohort")

        resp = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("class_id"), self.classroom.id)
        invite.refresh_from_db()
        self.assertEqual(invite.use_count, 1)

    def test_join_blocks_new_student_when_invite_seat_cap_reached(self):
        invite = ClassInviteLink.objects.create(classroom=self.classroom, max_uses=1, use_count=1)

        resp = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invite_seat_cap_reached")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    def test_join_rejoin_does_not_consume_new_invite_seat(self):
        invite = ClassInviteLink.objects.create(classroom=self.classroom, max_uses=1)
        first = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.client.get("/logout")

        second = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        invite.refresh_from_db()
        self.assertEqual(invite.use_count, 1)

    def test_join_by_class_code_is_blocked_when_invite_only_enrollment(self):
        self.classroom.enrollment_mode = Class.ENROLLMENT_INVITE_ONLY
        self.classroom.save(update_fields=["enrollment_mode"])

        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "invite_required")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    def test_join_by_invite_is_allowed_when_invite_only_enrollment(self):
        self.classroom.enrollment_mode = Class.ENROLLMENT_INVITE_ONLY
        self.classroom.save(update_fields=["enrollment_mode"])
        invite = ClassInviteLink.objects.create(classroom=self.classroom, label="Invite only cohort")

        resp = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session.get("class_id"), self.classroom.id)

    def test_join_is_blocked_when_enrollment_closed_even_with_invite(self):
        self.classroom.enrollment_mode = Class.ENROLLMENT_CLOSED
        self.classroom.save(update_fields=["enrollment_mode"])
        invite = ClassInviteLink.objects.create(classroom=self.classroom, label="Closed cohort")

        resp = self.client.post(
            "/join",
            data=json.dumps({"display_name": "Ada", "invite_token": invite.token}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "class_enrollment_closed")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    def test_join_rejoin_with_return_code_allowed_when_enrollment_closed(self):
        first = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        return_code = first.json().get("return_code")
        self.client.get("/logout")
        self.classroom.enrollment_mode = Class.ENROLLMENT_CLOSED
        self.classroom.save(update_fields=["enrollment_mode"])

        second = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "Ada",
                    "return_code": return_code,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json().get("rejoined"))

    def test_join_rejoin_with_return_code_allowed_when_invite_only(self):
        first = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        return_code = first.json().get("return_code")
        self.client.get("/logout")
        self.classroom.enrollment_mode = Class.ENROLLMENT_INVITE_ONLY
        self.classroom.save(update_fields=["enrollment_mode"])

        second = self.client.post(
            "/join",
            data=json.dumps(
                {
                    "class_code": self.classroom.join_code,
                    "display_name": "Ada",
                    "return_code": return_code,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json().get("rejoined"))


class TeacherAuditTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="teacher_audit",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.classroom = Class.objects.create(name="Audit Class", join_code="AUD12345")

    def test_teach_toggle_lock_creates_audit_event(self):
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(f"/teach/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(resp.status_code, 302)

        event = AuditEvent.objects.filter(action="class.toggle_lock").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.actor_user_id, self.staff.id)


class SubmissionRetentionCommandTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Retention Class", join_code="RET12345")
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

        self.old = Submission.objects.create(
            material=material,
            student=student,
            original_filename="old.sb3",
            file=SimpleUploadedFile("old.sb3", b"old"),
        )
        self.new = Submission.objects.create(
            material=material,
            student=student,
            original_filename="new.sb3",
            file=SimpleUploadedFile("new.sb3", b"new"),
        )
        Submission.objects.filter(id=self.old.id).update(uploaded_at=timezone.now() - timedelta(days=120))

    def test_prune_submissions_dry_run_keeps_rows(self):
        call_command("prune_submissions", older_than_days=90, dry_run=True)
        self.assertEqual(Submission.objects.count(), 2)

    def test_prune_submissions_deletes_old_rows(self):
        call_command("prune_submissions", older_than_days=90)
        ids = set(Submission.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_submissions_respects_keep_until_student_deletes_preset(self):
        self.classroom.retention_preset = Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES
        self.classroom.save(update_fields=["retention_preset"])

        call_command("prune_submissions", older_than_days=90)
        ids = set(Submission.objects.values_list("id", flat=True))
        self.assertIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_submissions_can_ignore_class_presets(self):
        self.classroom.retention_preset = Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES
        self.classroom.save(update_fields=["retention_preset"])
        call_command("prune_submissions", older_than_days=90, ignore_class_presets=True)
        ids = set(Submission.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_submissions_records_retention_audit_event(self):
        call_command("prune_submissions", older_than_days=90)
        event = AuditEvent.objects.filter(action="retention.prune_submissions").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_type, "RetentionJob")
        self.assertEqual(event.target_id, "submissions")
        self.assertEqual(int(event.metadata.get("matched_rows", 0)), 1)
        self.assertEqual(int(event.metadata.get("deleted_rows", 0)), 1)

    def test_prune_submissions_dry_run_does_not_record_retention_audit_event(self):
        call_command("prune_submissions", older_than_days=90, dry_run=True)
        self.assertFalse(AuditEvent.objects.filter(action="retention.prune_submissions").exists())


class StudentEventRetentionCommandTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Events Class", join_code="EVT12345")
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.old = StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_CLASS_JOIN,
            source="test",
            details={},
        )
        self.new = StudentEvent.objects.create(
            classroom=self.classroom,
            student=self.student,
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
            source="test",
            details={},
        )
        StudentEvent.objects.filter(id=self.old.id).update(created_at=timezone.now() - timedelta(days=120))

    def test_prune_student_events_dry_run_keeps_rows(self):
        call_command("prune_student_events", older_than_days=90, dry_run=True)
        self.assertEqual(StudentEvent.objects.count(), 2)

    def test_studentevent_queryset_delete_requires_retention_context(self):
        with self.assertRaises(ValueError):
            StudentEvent.objects.filter(id=self.old.id).delete()
        self.assertTrue(StudentEvent.objects.filter(id=self.old.id).exists())

    def test_prune_student_events_deletes_old_rows(self):
        call_command("prune_student_events", older_than_days=90)
        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_student_events_can_export_csv_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "student_events.csv"
            call_command(
                "prune_student_events",
                older_than_days=90,
                dry_run=True,
                export_csv=str(out),
            )
            self.assertTrue(out.exists())
            with out.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(StudentEvent.objects.count(), 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["id"]), self.old.id)
        self.assertEqual(rows[0]["event_type"], StudentEvent.EVENT_CLASS_JOIN)
        self.assertEqual(rows[0]["student_display_name"], "Ada")

    def test_prune_student_events_can_export_csv_before_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "student_events.csv"
            call_command(
                "prune_student_events",
                older_than_days=90,
                export_csv=str(out),
            )
            self.assertTrue(out.exists())
            with out.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["id"]), self.old.id)

    def test_prune_student_events_respects_keep_until_student_deletes_preset(self):
        self.classroom.retention_preset = Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES
        self.classroom.save(update_fields=["retention_preset"])

        call_command("prune_student_events", older_than_days=90)
        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_student_events_can_ignore_class_presets(self):
        self.classroom.retention_preset = Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES
        self.classroom.save(update_fields=["retention_preset"])

        call_command("prune_student_events", older_than_days=90, ignore_class_presets=True)
        ids = set(StudentEvent.objects.values_list("id", flat=True))
        self.assertNotIn(self.old.id, ids)
        self.assertIn(self.new.id, ids)

    def test_prune_student_events_records_retention_audit_event(self):
        call_command("prune_student_events", older_than_days=90)
        event = AuditEvent.objects.filter(action="retention.prune_student_events").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_type, "RetentionJob")
        self.assertEqual(event.target_id, "student_events")
        self.assertEqual(int(event.metadata.get("matched_rows", 0)), 1)
        self.assertEqual(int(event.metadata.get("deleted_rows", 0)), 1)

    def test_prune_student_events_dry_run_does_not_record_retention_audit_event(self):
        call_command("prune_student_events", older_than_days=90, dry_run=True)
        self.assertFalse(AuditEvent.objects.filter(action="retention.prune_student_events").exists())


class OrphanUploadScavengerCommandTests(TestCase):
    def _build_submission(self):
        classroom = Class.objects.create(name="Orphan Class", join_code="ORP12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        Submission.objects.create(
            material=material,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )

    def test_scavenger_report_only_does_not_delete(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self._build_submission()
                orphan = Path(media_root) / "submissions/orphan.tmp"
                orphan.parent.mkdir(parents=True, exist_ok=True)
                orphan.write_bytes(b"orphan")
                self.assertTrue(orphan.exists())

                out = StringIO()
                call_command("scavenge_orphan_uploads", stdout=out)
                output = out.getvalue()

                self.assertIn("Orphan files: 1", output)
                self.assertTrue(orphan.exists())

    def test_scavenger_delete_removes_orphan(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self._build_submission()
                orphan = Path(media_root) / "lesson_assets/orphan.pdf"
                orphan.parent.mkdir(parents=True, exist_ok=True)
                orphan.write_bytes(b"orphan")
                self.assertTrue(orphan.exists())

                out = StringIO()
                call_command("scavenge_orphan_uploads", delete=True, stdout=out)
                output = out.getvalue()

                self.assertIn("Deleted orphan files: 1", output)
                self.assertFalse(orphan.exists())


class StudentEventSubmissionTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Uploads Class", join_code="UPL12345")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.material = Material.objects.create(
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

    def test_material_upload_emits_student_event(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
                "note": "done",
            },
        )
        self.assertEqual(resp.status_code, 302)

        event = StudentEvent.objects.filter(event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD).order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.student_id, self.student.id)
        self.assertEqual(int(event.details.get("material_id") or 0), self.material.id)
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                student=self.student,
                classroom=self.classroom,
                event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
            ).count(),
            1,
        )
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                student=self.student,
                classroom=self.classroom,
                event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
                module=self.module,
            ).count(),
            1,
        )

        submission = Submission.objects.filter(material=self.material, student=self.student).order_by("-id").first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.original_filename, "project.sb3")
        stored_name = Path(submission.file.name).name
        self.assertNotEqual(stored_name, "project.sb3")
        self.assertTrue(re.match(r"^[a-f0-9]{32}\.sb3$", stored_name))

    def test_material_upload_does_not_duplicate_session_completed_for_same_module(self):
        self._login_student()
        first = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project1.sb3", _sample_sb3_bytes()),
                "note": "first",
            },
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project2.sb3", _sample_sb3_bytes()),
                "note": "second",
            },
        )
        self.assertEqual(second.status_code, 302)
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                student=self.student,
                classroom=self.classroom,
                event_type=StudentOutcomeEvent.EVENT_SESSION_COMPLETED,
                module=self.module,
            ).count(),
            1,
        )
        self.assertEqual(
            StudentOutcomeEvent.objects.filter(
                student=self.student,
                classroom=self.classroom,
                event_type=StudentOutcomeEvent.EVENT_ARTIFACT_SUBMITTED,
                module=self.module,
            ).count(),
            2,
        )

    def test_material_upload_rejects_invalid_sb3_content(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.material.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", b"not-a-zip"),
                "note": "bad",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "does not match .sb3", status_code=400)
        self.assertEqual(Submission.objects.filter(material=self.material, student=self.student).count(), 0)
        error_event = StudentEvent.objects.filter(
            event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD_ERROR,
            student=self.student,
            classroom=self.classroom,
        ).order_by("-id").first()
        self.assertIsNotNone(error_event)
        self.assertEqual(int((error_event.details or {}).get("material_id") or 0), self.material.id)
        self.assertEqual((error_event.details or {}).get("reason_code"), "content_validation_failed")

    def test_gallery_upload_can_opt_in_to_class_sharing(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()

        resp = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
                "share_with_class": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)
        self.assertTrue(saved.is_published)
        self.assertFalse(saved.is_gallery_shared)

    def test_student_home_shows_shared_gallery_entries_only(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        other = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")
        Submission.objects.create(
            material=gallery,
            student=other,
            original_filename="shared.sb3",
            file=SimpleUploadedFile("shared.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=True,
        )
        Submission.objects.create(
            material=gallery,
            student=other,
            original_filename="private.sb3",
            file=SimpleUploadedFile("private.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        self._login_student()

        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Shared gallery")
        self.assertContains(resp, "shared.sb3")
        self.assertNotContains(resp, "private.sb3")

    def test_student_gallery_page_hides_unapproved_artifacts(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        other = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")
        Submission.objects.create(
            material=gallery,
            student=other,
            original_filename="approved.sb3",
            file=SimpleUploadedFile("approved.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=True,
        )
        Submission.objects.create(
            material=gallery,
            student=other,
            original_filename="pending.sb3",
            file=SimpleUploadedFile("pending.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        self._login_student()

        resp = self.client.get(f"/student/gallery?module_id={self.module.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "approved.sb3")
        self.assertNotContains(resp, "pending.sb3")

    def test_student_can_publish_later_and_wait_for_teacher_approval(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()
        upload = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            },
        )
        self.assertEqual(upload.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)
        self.assertFalse(saved.is_published)
        self.assertFalse(saved.is_gallery_shared)

        publish_resp = self.client.post(
            f"/student/submission/{saved.id}/publish",
            {"publish": "1", "return_to": f"/material/{gallery.id}/upload"},
        )
        self.assertEqual(publish_resp.status_code, 302)
        saved.refresh_from_db()
        self.assertTrue(saved.is_published)
        self.assertFalse(saved.is_gallery_shared)

    def test_student_unpublish_clears_teacher_approval_and_republish_requires_reapproval(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()
        saved = Submission.objects.create(
            material=gallery,
            student=self.student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=True,
            published_at=timezone.now(),
        )

        unpublish = self.client.post(
            f"/student/submission/{saved.id}/publish",
            {"publish": "0", "return_to": f"/material/{gallery.id}/upload"},
        )
        self.assertEqual(unpublish.status_code, 302)
        saved.refresh_from_db()
        self.assertFalse(saved.is_published)
        self.assertFalse(saved.is_gallery_shared)
        self.assertIsNone(saved.published_at)

        republish = self.client.post(
            f"/student/submission/{saved.id}/publish",
            {"publish": "1", "return_to": f"/material/{gallery.id}/upload"},
        )
        self.assertEqual(republish.status_code, 302)
        saved.refresh_from_db()
        self.assertTrue(saved.is_published)
        self.assertFalse(saved.is_gallery_shared)
        self.assertIsNotNone(saved.published_at)

    def test_student_publish_ignores_external_return_to(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()
        upload = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            },
        )
        self.assertEqual(upload.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)

        publish_resp = self.client.post(
            f"/student/submission/{saved.id}/publish",
            {"publish": "1", "return_to": "https://evil.example.org/phish"},
        )
        self.assertEqual(publish_resp.status_code, 302)
        self.assertTrue(publish_resp["Location"].startswith(f"/material/{gallery.id}/upload?notice="))
        self.assertNotIn("evil.example.org", publish_resp["Location"])

    def test_student_publish_allows_student_return_to_path(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()
        upload = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
            },
        )
        self.assertEqual(upload.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)

        publish_resp = self.client.post(
            f"/student/submission/{saved.id}/publish",
            {"publish": "1", "return_to": "/student/gallery?module_id=1"},
        )
        self.assertEqual(publish_resp.status_code, 302)
        self.assertTrue(publish_resp["Location"].startswith("/student/gallery?module_id=1&notice="))

    def test_material_upload_process_note_is_escaped_and_bounded(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self._login_student()

        resp = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
                "process_note": "<script>alert(1)</script> tested with loops",
                "station_label": " Station 3 ",
            },
        )
        self.assertEqual(resp.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.station_label, "Station 3")
        self.assertIn("<script>alert(1)</script>", saved.process_note)

        page = self.client.get(f"/material/{gallery.id}/upload")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)
        self.assertNotContains(page, "<script>alert(1)</script>", html=False)

        too_long = "a" * 2001
        bad = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project2.sb3", _sample_sb3_bytes()),
                "process_note": too_long,
            },
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(Submission.objects.filter(material=gallery, student=self.student).count(), 1)

    def test_student_portfolio_filters_to_current_student_and_query(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        other = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")
        Submission.objects.create(
            material=self.material,
            student=self.student,
            original_filename="mine.sb3",
            file=SimpleUploadedFile("mine.sb3", _sample_sb3_bytes()),
            station_label="Station A",
        )
        Submission.objects.create(
            material=gallery,
            student=other,
            original_filename="other.sb3",
            file=SimpleUploadedFile("other.sb3", _sample_sb3_bytes()),
            station_label="Station A",
            is_published=True,
            is_gallery_shared=True,
        )
        self._login_student()

        all_resp = self.client.get("/student/portfolio")
        self.assertEqual(all_resp.status_code, 200)
        self.assertContains(all_resp, "mine.sb3")
        self.assertNotContains(all_resp, "other.sb3")

        filtered = self.client.get("/student/portfolio?station=Station+A")
        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, "mine.sb3")


class StudentMicroCheckTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Micro Check Class", join_code="MCK12345")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session["class_epoch"] = self.classroom.session_epoch
        session.save()

    def test_student_micro_check_posts_stuck_event(self):
        self._login_student()
        resp = self.client.post(
            "/student/micro-check",
            {"signal": "stuck", "module_id": str(self.module.id)},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/student?checkin_notice="))

        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_MICRO_CHECK_STUCK)
        self.assertEqual(event.classroom_id, self.classroom.id)
        self.assertEqual(event.student_id, self.student.id)
        self.assertEqual((event.details or {}).get("signal"), "stuck")
        self.assertEqual(int((event.details or {}).get("module_id") or 0), self.module.id)

    def test_student_micro_check_requires_student_session(self):
        resp = self.client.post("/student/micro-check", {"signal": "stuck"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/")
        self.assertFalse(StudentEvent.objects.filter(event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK).exists())

    def test_student_micro_check_ignores_module_outside_class(self):
        self._login_student()
        foreign_class = Class.objects.create(name="Other", join_code="OTH12345")
        foreign_module = Module.objects.create(classroom=foreign_class, title="Session X", order_index=0)

        resp = self.client.post(
            "/student/micro-check",
            {"signal": "can_do_this", "module_id": str(foreign_module.id)},
        )
        self.assertEqual(resp.status_code, 302)
        event = StudentEvent.objects.order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, StudentEvent.EVENT_MICRO_CHECK_CAN_DO_THIS)
        self.assertNotIn("module_id", event.details or {})


class StudentChecklistReflectionTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Checklist Reflection Class", join_code="CFR12345")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.checklist = Material.objects.create(
            module=self.module,
            title="Class checklist",
            type=Material.TYPE_CHECKLIST,
            body="I completed the warm-up\nI tested my code",
            order_index=0,
        )
        self.reflection = Material.objects.create(
            module=self.module,
            title="Reflection journal",
            type=Material.TYPE_REFLECTION,
            body="What changed in your code today?",
            order_index=1,
        )
        self.rubric = Material.objects.create(
            module=self.module,
            title="Session rubric",
            type=Material.TYPE_RUBRIC,
            body="Problem solving\nCode quality",
            rubric_scale_max=4,
            order_index=2,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_student_home_renders_checklist_and_reflection_forms(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"/material/{self.checklist.id}/checklist")
        self.assertContains(resp, f"/material/{self.reflection.id}/reflection")
        self.assertContains(resp, f"/material/{self.rubric.id}/rubric")
        self.assertContains(resp, "Class checklist")
        self.assertContains(resp, "Reflection journal")
        self.assertContains(resp, "Session rubric")

    def test_student_home_renders_default_peer_feedback_starters(self):
        self._login_student()
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-starter-target="reflection-')
        self.assertContains(resp, f'data-starter-target="reflection-{self.reflection.id}"')
        self.assertContains(resp, f'data-starter-target="rubric-feedback-{self.rubric.id}"')
        self.assertContains(resp, "I noticed...")
        self.assertContains(resp, "I wonder...")
        self.assertContains(resp, "What if...")

    def test_student_home_renders_peer_feedback_starters_in_spanish(self):
        self._login_student()
        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Noté que...")
        self.assertContains(resp, "Me pregunto...")
        self.assertContains(resp, "¿Qué pasaría si...?")

    def test_student_can_save_checklist_and_emit_completion_milestone(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.checklist.id}/checklist",
            {"checked_item": ["0", "1"]},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/student")

        saved = StudentMaterialResponse.objects.filter(student=self.student, material=self.checklist).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.checklist_checked, [0, 1])

        milestone = StudentOutcomeEvent.objects.filter(
            student=self.student,
            classroom=self.classroom,
            material=self.checklist,
            event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
        ).order_by("-id").first()
        self.assertIsNotNone(milestone)
        self.assertEqual(milestone.details.get("trigger"), "checklist_completed")
        self.assertNotIn("warm-up", json.dumps(milestone.details))

    def test_student_can_save_reflection_without_event_content_leak(self):
        self._login_student()
        reflection_text = "I fixed my loop and tested with a partner."
        resp = self.client.post(
            f"/material/{self.reflection.id}/reflection",
            {"reflection_text": reflection_text},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/student")

        saved = StudentMaterialResponse.objects.filter(student=self.student, material=self.reflection).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.reflection_text, reflection_text)

        milestone = StudentOutcomeEvent.objects.filter(
            student=self.student,
            classroom=self.classroom,
            material=self.reflection,
            event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
        ).order_by("-id").first()
        self.assertIsNotNone(milestone)
        self.assertEqual(milestone.details.get("trigger"), "reflection_submitted")
        self.assertNotIn("loop and tested", json.dumps(milestone.details))

    def test_student_can_save_rubric_without_event_content_leak(self):
        self._login_student()
        resp = self.client.post(
            f"/material/{self.rubric.id}/rubric",
            {
                "criterion_0": "4",
                "criterion_1": "3",
                "rubric_feedback": "I improved my structure today.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/student")

        saved = StudentMaterialResponse.objects.filter(student=self.student, material=self.rubric).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.rubric_scores, [4, 3])
        self.assertEqual(saved.rubric_feedback, "I improved my structure today.")

        milestone = StudentOutcomeEvent.objects.filter(
            student=self.student,
            classroom=self.classroom,
            material=self.rubric,
            event_type=StudentOutcomeEvent.EVENT_MILESTONE_EARNED,
        ).order_by("-id").first()
        self.assertIsNotNone(milestone)
        self.assertEqual(milestone.details.get("trigger"), "rubric_submitted")
        self.assertNotIn("improved my structure", json.dumps(milestone.details))

    def test_checklist_and_reflection_posts_are_blocked_when_lesson_locked(self):
        Material.objects.create(
            module=self.module,
            title="Session 1 lesson",
            type=Material.TYPE_LINK,
            url="/course/piper_scratch_12_session/s01-welcome-private-workflow",
            order_index=99,
        )
        LessonRelease.objects.create(
            classroom=self.classroom,
            course_slug="piper_scratch_12_session",
            lesson_slug="s01-welcome-private-workflow",
            available_on=timezone.localdate() + timedelta(days=2),
        )
        self._login_student()

        checklist_resp = self.client.post(
            f"/material/{self.checklist.id}/checklist",
            {"checked_item": ["0", "1"]},
        )
        self.assertEqual(checklist_resp.status_code, 403)

        reflection_resp = self.client.post(
            f"/material/{self.reflection.id}/reflection",
            {"reflection_text": "Locked write should fail."},
        )
        self.assertEqual(reflection_resp.status_code, 403)
        rubric_resp = self.client.post(
            f"/material/{self.rubric.id}/rubric",
            {"criterion_0": "4", "criterion_1": "3"},
        )
        self.assertEqual(rubric_resp.status_code, 403)
        self.assertEqual(StudentMaterialResponse.objects.filter(student=self.student).count(), 0)


class PeerFeedbackStarterServiceTests(SimpleTestCase):
    def test_language_defaults_are_available(self):
        from ..services.peer_feedback import resolve_peer_feedback_starters

        starters = resolve_peer_feedback_starters(language_code="es", course_manifest={})
        self.assertEqual(starters[0], "Noté que...")
        self.assertIn("Me pregunto...", starters)
        self.assertIn("¿Qué pasaría si...?", starters)

    def test_course_manifest_override_wins(self):
        from ..services.peer_feedback import resolve_peer_feedback_starters

        manifest = {
            "peer_feedback_sentence_starters": {
                "default": ["I notice...", "I am curious about...", "Try this..."],
                "es": ["Veo...", "Me pregunto...", "Intenta..."],
            }
        }
        starters = resolve_peer_feedback_starters(language_code="es-MX", course_manifest=manifest)
        self.assertEqual(starters, ["Veo...", "Me pregunto...", "Intenta..."])


class SubmissionQuotaServiceTests(SimpleTestCase):
    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        }
    )
    def test_quota_cache_scan_invalidate_and_bump(self):
        from ..services.submission_quota import (
            bump_cached_classroom_submission_bytes,
            get_classroom_submission_bytes,
            invalidate_classroom_submission_quota_cache,
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                classroom_id = 41
                class_dir = Path(media_root) / "submissions" / f"class_{classroom_id}"
                class_dir.mkdir(parents=True, exist_ok=True)
                payload = class_dir / "project.bin"
                payload.write_bytes(b"1234")

                invalidate_classroom_submission_quota_cache(classroom_id=classroom_id)
                first = get_classroom_submission_bytes(classroom_id=classroom_id)
                self.assertEqual(first, 4)

                payload.write_bytes(b"123456789")
                second = get_classroom_submission_bytes(classroom_id=classroom_id)
                self.assertEqual(second, 4)

                bump_cached_classroom_submission_bytes(classroom_id=classroom_id, delta_bytes=3)
                third = get_classroom_submission_bytes(classroom_id=classroom_id)
                self.assertEqual(third, 7)

                invalidate_classroom_submission_quota_cache(classroom_id=classroom_id)
                refreshed = get_classroom_submission_bytes(classroom_id=classroom_id)
                self.assertEqual(refreshed, 9)

    @patch("hub.services.submission_quota.cache.get", side_effect=RuntimeError("cache_down"))
    @patch("hub.services.submission_quota.cache.set", side_effect=RuntimeError("cache_down"))
    def test_quota_scan_survives_cache_backend_errors(self, _set_mock, _get_mock):
        from ..services.submission_quota import get_classroom_submission_bytes

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                classroom_id = 88
                class_dir = Path(media_root) / "submissions" / f"class_{classroom_id}"
                class_dir.mkdir(parents=True, exist_ok=True)
                (class_dir / "project.bin").write_bytes(b"1234")
                total = get_classroom_submission_bytes(classroom_id=classroom_id)
                self.assertEqual(total, 4)

    @patch("hub.services.submission_quota.cache.delete", side_effect=RuntimeError("cache_down"))
    @patch("hub.services.submission_quota.cache.get", side_effect=RuntimeError("cache_down"))
    @patch("hub.services.submission_quota.cache.set", side_effect=RuntimeError("cache_down"))
    def test_quota_bump_and_invalidate_survive_cache_backend_errors(self, _set_mock, _get_mock, _delete_mock):
        from ..services.submission_quota import (
            bump_cached_classroom_submission_bytes,
            invalidate_classroom_submission_quota_cache,
        )

        bump_cached_classroom_submission_bytes(classroom_id=22, delta_bytes=50)
        invalidate_classroom_submission_quota_cache(classroom_id=22)


class SubmissionDownloadHardeningTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Download Class", join_code="DL123456")
        self.module = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.material = Material.objects.create(
            module=self.module,
            title="Upload",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.submission = Submission.objects.create(
            material=self.material,
            student=self.student,
            original_filename="../bad\r\nname<script>.sb3",
            file=SimpleUploadedFile("project.sb3", _sample_sb3_bytes()),
        )

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def _login_student_client(self, client: Client, student: StudentIdentity):
        session = client.session
        session["student_id"] = student.id
        session["class_id"] = student.classroom_id
        session.save()

    def test_submission_download_sets_hardening_headers(self):
        self._login_student()
        resp = self.client.get(f"/submission/{self.submission.id}/download")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Content-Security-Policy"], "default-src 'none'; sandbox")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")
        self.assertEqual(resp["Content-Type"], "application/octet-stream")
        self.assertIn("attachment;", resp["Content-Disposition"])

    def test_submission_download_uses_safe_content_disposition_filename(self):
        self._login_student()
        resp = self.client.get(f"/submission/{self.submission.id}/download")
        self.assertEqual(resp.status_code, 200)
        disposition = resp["Content-Disposition"]
        self.assertIn("bad_name_script_.sb3", disposition)
        self.assertNotIn("/", disposition)
        self.assertNotIn("\\", disposition)
        self.assertNotRegex(disposition, r"[\r\n]")

    def test_submission_download_allows_classmate_when_gallery_item_is_shared(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        owner = StudentIdentity.objects.create(classroom=self.classroom, display_name="Owner")
        shared = Submission.objects.create(
            material=gallery,
            student=owner,
            original_filename="shared.sb3",
            file=SimpleUploadedFile("shared.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=True,
        )
        viewer = StudentIdentity.objects.create(classroom=self.classroom, display_name="Viewer")
        peer_client = Client()
        self._login_student_client(peer_client, viewer)

        resp = peer_client.get(f"/submission/{shared.id}/download")
        self.assertEqual(resp.status_code, 200)

    def test_submission_download_blocks_classmate_when_gallery_item_not_shared(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        owner = StudentIdentity.objects.create(classroom=self.classroom, display_name="Owner")
        private_item = Submission.objects.create(
            material=gallery,
            student=owner,
            original_filename="private.sb3",
            file=SimpleUploadedFile("private.sb3", _sample_sb3_bytes()),
            is_gallery_shared=False,
        )
        viewer = StudentIdentity.objects.create(classroom=self.classroom, display_name="Viewer")
        peer_client = Client()
        self._login_student_client(peer_client, viewer)

        resp = peer_client.get(f"/submission/{private_item.id}/download")
        self.assertEqual(resp.status_code, 403)


class FileCleanupSignalTests(TestCase):
    def _build_submission(self):
        classroom = Class.objects.create(name="Cleanup Class", join_code="CLN12345")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        material = Material.objects.create(
            module=module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        submission = Submission.objects.create(
            material=material,
            student=student,
            original_filename="project.sb3",
            file=SimpleUploadedFile("project.sb3", b"dummy"),
        )
        return student, submission

    def test_submission_file_deleted_on_student_cascade_delete(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                student, submission = self._build_submission()
                file_path = Path(submission.file.path)
                self.assertTrue(file_path.exists())

                student.delete()

                self.assertFalse(Submission.objects.filter(id=submission.id).exists())
                self.assertFalse(file_path.exists())

    def test_submission_file_replaced_deletes_old_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                _student, submission = self._build_submission()
                old_path = Path(submission.file.path)
                self.assertTrue(old_path.exists())

                submission.file = SimpleUploadedFile("project_new.sb3", b"new")
                submission.original_filename = "project_new.sb3"
                submission.save()

                new_path = Path(submission.file.path)
                self.assertTrue(new_path.exists())
                self.assertFalse(old_path.exists())

    def test_lesson_asset_delete_removes_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                folder = LessonAssetFolder.objects.create(path="general", display_name="General")
                asset = LessonAsset.objects.create(
                    folder=folder,
                    title="Worksheet",
                    original_filename="worksheet.pdf",
                    file=SimpleUploadedFile("worksheet.pdf", b"%PDF-1.4"),
                )
                file_path = Path(asset.file.path)
                self.assertTrue(file_path.exists())

                asset.delete()
                self.assertFalse(file_path.exists())

    def test_lesson_video_delete_removes_file(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                video = LessonVideo.objects.create(
                    course_slug="piper_scratch_12_session",
                    lesson_slug="01-welcome-private-workflow",
                    title="Welcome video",
                    video_file=SimpleUploadedFile("welcome.mp4", b"\x00\x00\x00\x18ftypmp42"),
                )
                file_path = Path(video.video_file.path)
                self.assertTrue(file_path.exists())

                video.delete()
                self.assertFalse(file_path.exists())


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
