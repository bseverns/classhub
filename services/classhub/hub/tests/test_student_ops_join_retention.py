from ._shared import *  # noqa: F401,F403


class JoinClassTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="Join Test", join_code="JOIN1234")

    def test_join_accepts_standard_form_post_without_javascript(self):
        resp = self.client.post(
            "/join",
            {"class_code": self.classroom.join_code, "display_name": "Form Student"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/student")
        self.assertIsNotNone(self.client.session.get("student_id"))

    def test_join_json_path_remains_json(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "JSON Student"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @override_settings(DEBUG=False, SESSION_COOKIE_SECURE=False)
    def test_device_hint_cookie_follows_local_http_session_transport(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Local HTTP Student"}),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.cookies["classhub_student_hint"]["secure"], "")

        logout_resp = self.client.get("/logout")
        self.assertEqual(logout_resp.status_code, 302)
        self.assertEqual(logout_resp.cookies["classhub_student_hint"]["secure"], "")

    @override_settings(DEBUG=True, SESSION_COOKIE_SECURE=True)
    def test_device_hint_cookie_follows_secure_session_transport(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "HTTPS Student"}),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.cookies["classhub_student_hint"]["secure"])

        logout_resp = self.client.get("/logout")
        self.assertEqual(logout_resp.status_code, 302)
        self.assertTrue(logout_resp.cookies["classhub_student_hint"]["secure"])

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
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "return_code_required")
        self.assertIsNone(self.client.session.get("student_id"))

    @override_settings(CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=False)
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

    def test_explicit_logout_requires_return_code_despite_same_browser(self):
        payload = {"class_code": self.classroom.join_code, "display_name": "Ada"}
        r1 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r1.status_code, 200)

        # Student logs out, then re-joins from the same browser/device.
        self.client.get("/logout")
        r2 = self.client.post("/join", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.json().get("error"), "return_code_required")
        self.assertIsNone(self.client.session.get("student_id"))
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 1)

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

    @override_settings(CLASSHUB_REQUIRE_RETURN_CODE_FOR_REJOIN=False)
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
        return_code = first.json().get("return_code")
        self.client.get("/logout")

        second = self.client.post(
            "/join",
            data=json.dumps(
                {"display_name": "Ada", "invite_token": invite.token, "return_code": return_code}
            ),
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
