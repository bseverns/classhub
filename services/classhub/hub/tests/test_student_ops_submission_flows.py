from ._shared import *  # noqa: F401,F403


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

    def test_material_upload_page_simple_reading_level_uses_simpler_privacy_copy(self):
        self._login_student()
        resp = self.client.get(f"/material/{self.material.id}/upload?reading_level=simple")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reading level: Simple")
        self.assertContains(resp, "Need to remove your work?")

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

    def test_material_upload_records_remix_lineage(self):
        gallery = Material.objects.create(
            module=self.module,
            title="Share to gallery",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".png,.jpg,.jpeg,.pdf,.sb3",
            max_upload_mb=50,
            order_index=1,
        )
        owner = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ben")
        source = Submission.objects.create(
            material=gallery,
            student=owner,
            original_filename="starter.sb3",
            file=SimpleUploadedFile("starter.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=True,
        )
        self._login_student()

        page = self.client.get(f"/material/{gallery.id}/upload?remix_of={source.id}")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Remix source:")
        self.assertContains(page, "starter.sb3")

        resp = self.client.post(
            f"/material/{gallery.id}/upload",
            {
                "file": SimpleUploadedFile("project-remix.sb3", _sample_sb3_bytes()),
                "remix_of_submission_id": str(source.id),
                "process_note": "I changed the score rules.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        saved = Submission.objects.filter(material=gallery, student=self.student).order_by("-id").first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.remix_of_id, source.id)

        portfolio = self.client.get("/student/portfolio")
        self.assertEqual(portfolio.status_code, 200)
        self.assertContains(portfolio, "Remix of:")
        self.assertContains(portfolio, "starter.sb3")

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

    def test_student_home_renders_peer_feedback_starters_in_somali(self):
        self._login_student()
        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Waxaan arkay in...")
        self.assertContains(resp, "Waxaan is weydiinayaa...")
        self.assertContains(resp, "Maxaa dhici lahaa haddii...?")

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

    def test_language_defaults_are_available_for_somali(self):
        from ..services.peer_feedback import resolve_peer_feedback_starters

        starters = resolve_peer_feedback_starters(language_code="so", course_manifest={})
        self.assertEqual(starters[0], "Waxaan arkay in...")
        self.assertIn("Waxaan is weydiinayaa...", starters)
        self.assertIn("Maxaa dhici lahaa haddii...?", starters)

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
