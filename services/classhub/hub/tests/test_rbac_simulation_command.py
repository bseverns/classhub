from ._shared import *  # noqa: F401,F403


class SimulateRbacAccessCommandTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.org = Organization.objects.create(name="Sim Org")
        self.classroom = Class.objects.create(name="Sim Class", join_code="SIMCLASS", organization=self.org)
        self.module = Module.objects.create(classroom=self.classroom, title="Module 1", order_index=0)
        self.teacher = self.User.objects.create_user(
            username="sim_teacher",
            password="pw12345",
            is_staff=True,
        )
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )

    def test_errors_when_module_scope_without_class(self):
        with self.assertRaises(CommandError):
            call_command(
                "simulate_rbac_access",
                username=self.teacher.username,
                capability="submission.view",
                module_id=self.module.id,
            )

    def test_json_output_contains_decision(self):
        out = StringIO()
        call_command(
            "simulate_rbac_access",
            username=self.teacher.username,
            capability="submission.view",
            class_id=self.classroom.id,
            module_id=self.module.id,
            json_output=True,
            stdout=out,
        )
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["target_user"]["username"], self.teacher.username)
        self.assertTrue(payload["decision"]["allowed"])
        self.assertEqual(payload["decision"]["capability"], "submission.view")
