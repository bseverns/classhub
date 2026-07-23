from ._shared import *  # noqa: F401,F403


class TeacherOrganizationBoundaryAccessTests(TestCase):
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

    def _promote_staff_to_superuser(self):
        self.staff.is_superuser = True
        self.staff.save(update_fields=["is_superuser"])

    def test_teach_home_lists_only_accessible_org_classes(self):
        resp = self.client.get("/teach")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha Cohort")
        self.assertNotContains(resp, "Beta Cohort")

    def test_teach_home_hides_syllabus_exports_for_teacher_role(self):
        resp = self.client.get("/teach?portal_mode=setup")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Start Here Today")
        self.assertContains(resp, "Daily teaching workflows (tasks 1-8)")
        self.assertNotContains(resp, "Operator + policy workflows (tasks 9-10)")
        self.assertNotContains(resp, "Syllabus Exports")
        self.assertNotContains(resp, "RBAC tools")
        self.assertNotContains(resp, "Operator config snapshot")

    def test_non_superuser_invalid_portal_mode_falls_back_to_day_for_returning_teacher(self):
        resp = self.client.get("/teach?portal_mode=admin")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Classroom focus")
        self.assertContains(resp, "Class setup")
        self.assertNotContains(resp, "All panels")
        self.assertNotContains(resp, "Portal setup + account tools")
        self.assertNotContains(resp, "Operator config snapshot")
        self.assertNotContains(resp, "Organizations + Staff Memberships")

    def test_teacher_role_cannot_export_syllabus(self):
        resp = self.client.get("/teach/syllabus-export?kind=catalog_csv")
        self.assertEqual(resp.status_code, 403)

    def test_org_admin_membership_can_export_syllabus(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_ADMIN
        membership.save(update_fields=["role"])

        home_resp = self.client.get("/teach?portal_mode=setup")
        self.assertEqual(home_resp.status_code, 200)
        self.assertContains(home_resp, "Syllabus Exports")
        self.assertNotContains(home_resp, "RBAC tools")
        self.assertNotContains(home_resp, "/teach/rbac/module-scope-grant/upsert")
        self.assertNotContains(home_resp, "/teach/rbac/simulate")

        resp = self.client.get("/teach/syllabus-export?kind=catalog_csv")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])

    def test_teach_class_dashboard_blocks_other_org(self):
        resp = self.client.get(f"/teach/class/{self.class_b.id}")
        self.assertEqual(resp.status_code, 404)

    def test_viewer_membership_cannot_mutate_class(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])

        resp = self.client.post(f"/teach/class/{self.class_a.id}/toggle-lock")
        self.assertEqual(resp.status_code, 403)

    def test_viewer_dashboard_keeps_class_data_but_hides_mutation_controls(self):
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])
        module = Module.objects.create(classroom=self.class_a, title="Session 1", order_index=0)
        Material.objects.create(
            module=module,
            title="Session 1 lesson",
            type=Material.TYPE_LINK,
            url="/course/demo/session-1",
        )
        student = StudentIdentity.objects.create(classroom=self.class_a, display_name="Ada")
        StudentEvent.objects.create(
            classroom=self.class_a,
            student=student,
            event_type=StudentEvent.EVENT_MICRO_CHECK_STUCK,
            source="test",
            details={"module_id": module.id},
        )
        StudentEvent.objects.create(
            classroom=self.class_a,
            student=student,
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            source="test",
            details={},
        )

        dashboard = self.client.get(f"/teach/class/{self.class_a.id}")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Alpha Cohort")
        self.assertContains(dashboard, "Session 1")
        self.assertContains(dashboard, "Ada")
        self.assertNotContains(dashboard, f"/teach/module/{module.id}")
        self.assertNotContains(dashboard, f"/teach/class/{self.class_a.id}/toggle-lock")
        self.assertNotContains(dashboard, f"/teach/class/{self.class_a.id}/reset-roster")
        self.assertNotContains(dashboard, f"/teach/class/{self.class_a.id}/resolve-stuck")
        self.assertNotContains(dashboard, f"/teach/class/{self.class_a.id}/resolve-delete-request")
        self.assertNotContains(dashboard, "/teach/lessons/release")

        home = self.client.get("/teach?portal_mode=setup")
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "Your organization role does not allow you to create a class.")
        self.assertNotContains(home, "You need an active organization membership before you can create a class.")
        self.assertNotContains(home, 'action="/teach/create-class"')

        lessons = self.client.get(f"/teach/lessons?class_id={self.class_a.id}")
        self.assertEqual(lessons.status_code, 200)
        self.assertContains(lessons, "Alpha Cohort")
        self.assertContains(lessons, "Session 1")
        self.assertContains(lessons, 'class="release-status"')
        self.assertNotContains(lessons, "/teach/lessons/release")

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

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=False)
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

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_strict_membership_without_membership_shows_create_class_guidance(self):
        legacy_staff = get_user_model().objects.create_user(
            username="legacy_staff_create_guidance",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, legacy_staff)

        resp = self.client.get("/teach")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "You need an active organization membership before you can create a class.")
        self.assertNotContains(resp, 'action="/teach/create-class"')

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
