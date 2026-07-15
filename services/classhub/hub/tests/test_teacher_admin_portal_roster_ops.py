from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests
from types import SimpleNamespace


class TeacherPortalRosterOpsTests(TeacherPortalBaseTests):
    @patch("hub.views.teacher_parts.roster_students_lifecycle.clear_helper_actor_conversations")
    def test_teach_delete_student_data_removes_submissions_and_detaches_events(self, clear_mock):
        clear_mock.return_value = SimpleNamespace(ok=True, deleted_conversations=1)
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
