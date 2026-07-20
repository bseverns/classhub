from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class StudentUxPriorityPassTests(TestCase):
    def setUp(self):
        self.classroom = Class.objects.create(name="UX Priority Class", join_code="UXPR1234")
        self.module = Module.objects.create(classroom=self.classroom, title="First Steps", order_index=0)
        self.upload = Material.objects.create(
            module=self.module,
            title="Upload your project",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".txt",
            max_upload_mb=2,
            order_index=0,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Calm Otter 7")

    def _login_student(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session.save()

    def test_join_puts_language_before_instructions_and_collapses_returning_student_controls(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertLess(html.find('class="language-chooser"'), html.find("Enter the class code from your teacher"))
        self.assertContains(response, '<details class="return-code-entry">', html=False)
        self.assertContains(response, "Returning to saved work?")
        self.assertContains(response, 'id="return_code"', html=False)

    def test_student_home_promotes_and_opens_first_module_when_no_course_lesson_exists(self):
        self._login_student()

        response = self.client.get("/student")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["class_landing"]["next_open_module"]["module_id"], self.module.id)
        self.assertContains(response, "Start next task")
        self.assertContains(response, f'href="#module-{self.module.id}"', html=False)
        self.assertContains(response, f'id="module-{self.module.id}" open', html=False)
        self.assertNotContains(response, "No calendar-linked lessons yet")
        self.assertNotContains(response, "Course lesson links will appear here")

    def test_student_home_keeps_secondary_navigation_in_account_section(self):
        self._login_student()

        response = self.client.get("/student")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        top_end = html.find("</div>", html.find('class="student-primary-nav"'))
        top_nav = html[html.find('class="student-primary-nav"'):top_end]
        self.assertNotIn("Join page", top_nav)
        self.assertNotIn("Export my portfolio", top_nav)
        self.assertContains(response, 'class="account-secondary-links"', html=False)
        self.assertContains(response, "Privacy")
        self.assertContains(response, "Trust notes")

    def test_upload_uses_plain_form_without_unsafe_offline_queue(self):
        self._login_student()

        response = self.client.get(f"/material/{self.upload.id}/upload")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form method="post" enctype="multipart/form-data" class="upload-form">', html=False)
        self.assertNotContains(response, "upload-queue-panel")
        self.assertNotContains(response, "student_upload_queue.js")

    def test_my_data_separates_delete_controls_from_account_actions(self):
        self._login_student()

        response = self.client.get("/student/my-data")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="danger-zone"', html=False)
        self.assertContains(response, "Delete my class data")
        self.assertContains(response, "Delete my work now")

    def test_student_helper_uses_capability_copy_without_backend_branding(self):
        self._login_student()

        response = self.client.get("/student")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This helper can coach you through the next step.")
        self.assertNotContains(response, "Day-1 wire-up")
        self.assertNotContains(response, "Local model (Ollama)")


class HelperWidgetFailureCopyTests(SimpleTestCase):
    def test_helper_widget_maps_missing_route_to_one_human_recovery_message(self):
        source = (Path(__file__).resolve().parents[1] / "static/js/helper_widget.js").read_text(encoding="utf-8")

        self.assertIn('if (status === 404) return copy.unavailable;', source)
        self.assertIn("The helper is offline right now. Ask your facilitator or try again later.", source)
        self.assertIn('appendTurn("assistant", errorText);\n          setOutput("");', source)
        self.assertNotIn("`${copy.errorPrefix}: ${errorCode}`", source)


class TeacherUxPriorityPassTests(TeacherPortalBaseTests):
    def test_day_mode_leads_with_activity_and_omits_onboarding_and_duplicate_class_table(self):
        self._build_lesson_with_submission()
        _force_login_staff_verified(self.client, self.staff)

        response = self.client.get("/teach?portal_mode=day")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotContains(response, "Start Here Today")
        self.assertNotContains(response, "Classes available in the teacher portal")
        self.assertLess(html.find("What Changed Since Yesterday"), html.find("Classroom focus"))

    def test_lesson_tracker_defaults_to_first_accessible_class_and_collapses_controls(self):
        first_class, _upload = self._build_lesson_with_submission()
        Class.objects.create(name="Second Class", join_code="SECOND12")
        _force_login_staff_verified(self.client, self.staff)

        response = self.client.get("/teach/lessons")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_class_id"], response.context["classes"][0].id)
        self.assertEqual(len(response.context["class_rows"]), 1)
        self.assertContains(response, '<details class="lesson-controls">', html=False)
        self.assertNotContains(response, '<details class="lesson-controls" open>', html=False)
        self.assertNotContains(response, '<option value="0"', html=False)
        self.assertContains(response, first_class.name)
