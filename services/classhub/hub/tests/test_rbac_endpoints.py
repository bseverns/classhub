from ._shared import *  # noqa: F401,F403


class EndpointRBACGuardTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="rbac_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.org = Organization.objects.create(name="RBAC Org")
        OrganizationMembership.objects.create(
            organization=self.org,
            user=self.staff,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        self.classroom = Class.objects.create(
            name="RBAC Class",
            join_code="RBAC1234",
            organization=self.org,
        )
        self.module_1 = Module.objects.create(classroom=self.classroom, title="Session 1", order_index=0)
        self.module_2 = Module.objects.create(classroom=self.classroom, title="Session 2", order_index=1)
        self.upload_1 = Material.objects.create(
            module=self.module_1,
            title="Upload 1",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.upload_2 = Material.objects.create(
            module=self.module_2,
            title="Upload 2",
            type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=0,
        )
        self.gallery_1 = Material.objects.create(
            module=self.module_1,
            title="Gallery 1",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self.gallery_2 = Material.objects.create(
            module=self.module_2,
            title="Gallery 2",
            type=Material.TYPE_GALLERY,
            accepted_extensions=".sb3",
            max_upload_mb=50,
            order_index=1,
        )
        self.student = StudentIdentity.objects.create(classroom=self.classroom, display_name="Ada")
        self.upload_submission_1 = Submission.objects.create(
            material=self.upload_1,
            student=self.student,
            original_filename="upload_one.sb3",
            file=SimpleUploadedFile("upload_one.sb3", _sample_sb3_bytes()),
        )
        self.upload_submission_2 = Submission.objects.create(
            material=self.upload_2,
            student=self.student,
            original_filename="upload_two.sb3",
            file=SimpleUploadedFile("upload_two.sb3", _sample_sb3_bytes()),
        )
        self.gallery_submission_1 = Submission.objects.create(
            material=self.gallery_1,
            student=self.student,
            original_filename="gallery_one.sb3",
            file=SimpleUploadedFile("gallery_one.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        self.gallery_submission_2 = Submission.objects.create(
            material=self.gallery_2,
            student=self.student,
            original_filename="gallery_two.sb3",
            file=SimpleUploadedFile("gallery_two.sb3", _sample_sb3_bytes()),
            is_published=True,
            is_gallery_shared=False,
        )
        self.certificate = CertificateIssuance.objects.create(
            classroom=self.classroom,
            student=self.student,
            issued_by=self.staff,
            session_count=1,
            artifact_count=1,
            milestone_count=0,
            min_sessions_required=1,
            min_artifacts_required=1,
        )
        _force_login_staff_verified(self.client, self.staff)

    def test_viewer_can_view_submissions_but_cannot_manage_policy_or_roster(self):
        membership = OrganizationMembership.objects.get(organization=self.org, user=self.staff)
        membership.role = OrganizationMembership.ROLE_VIEWER
        membership.save(update_fields=["role"])

        material_submissions = self.client.get(f"/teach/material/{self.upload_1.id}/submissions")
        self.assertEqual(material_submissions.status_code, 200)

        api_submissions = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/submissions")
        self.assertEqual(api_submissions.status_code, 200)
        summary_export = self.client.get(f"/teach/class/{self.classroom.id}/export-summary-csv")
        self.assertEqual(summary_export.status_code, 200)

        policy_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/set-enrollment-mode",
            {"enrollment_mode": "closed"},
        )
        self.assertEqual(policy_mutation.status_code, 403)
        api_policy_mutation = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        self.assertEqual(api_policy_mutation.status_code, 403)
        api_toggle_lock = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(api_toggle_lock.status_code, 403)
        api_rotate_code = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/rotate-code")
        self.assertEqual(api_rotate_code.status_code, 403)
        rotate_code = self.client.post(f"/teach/class/{self.classroom.id}/rotate-code")
        self.assertEqual(rotate_code.status_code, 403)
        reset_roster = self.client.post(f"/teach/class/{self.classroom.id}/reset-roster")
        self.assertEqual(reset_roster.status_code, 403)

        roster_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/rename-student",
            {
                "student_id": str(self.student.id),
                "display_name": "Renamed Ada",
            },
        )
        self.assertEqual(roster_mutation.status_code, 403)
        certificate_download = self.client.get(
            f"/teach/class/{self.classroom.id}/certificate/{self.student.id}/download"
        )
        self.assertEqual(certificate_download.status_code, 403)

    def test_teacher_can_manage_policy_and_roster_endpoints(self):
        policy_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/set-enrollment-mode",
            {"enrollment_mode": "invite_only"},
        )
        self.assertEqual(policy_mutation.status_code, 302)
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.enrollment_mode, Class.ENROLLMENT_INVITE_ONLY)
        api_policy_mutation = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        self.assertEqual(api_policy_mutation.status_code, 200)
        self.classroom.refresh_from_db()
        self.assertEqual(self.classroom.enrollment_mode, Class.ENROLLMENT_CLOSED)
        rotate_code = self.client.post(f"/teach/class/{self.classroom.id}/rotate-code")
        self.assertEqual(rotate_code.status_code, 302)

        roster_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/rename-student",
            {
                "student_id": str(self.student.id),
                "display_name": "Renamed Ada",
            },
        )
        self.assertEqual(roster_mutation.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.display_name, "Renamed Ada")
        certificate_download = self.client.get(
            f"/teach/class/{self.classroom.id}/certificate/{self.student.id}/download"
        )
        self.assertEqual(certificate_download.status_code, 200)

    def test_teacher_role_template_override_limits_policy_endpoints_in_teach_and_api(self):
        OrganizationRoleCapability.objects.filter(organization=self.org).delete()
        OrganizationRoleCapability.objects.bulk_create(
            [
                OrganizationRoleCapability(
                    organization=self.org,
                    role=OrganizationMembership.ROLE_TEACHER,
                    capability=OrganizationRoleCapability.CAP_CLASS_VIEW,
                    is_active=True,
                ),
                OrganizationRoleCapability(
                    organization=self.org,
                    role=OrganizationMembership.ROLE_TEACHER,
                    capability=OrganizationRoleCapability.CAP_SUBMISSION_VIEW,
                    is_active=True,
                ),
            ]
        )

        material_submissions = self.client.get(f"/teach/material/{self.upload_1.id}/submissions")
        self.assertEqual(material_submissions.status_code, 200)
        api_submissions = self.client.get(f"/api/v1/teacher/class/{self.classroom.id}/submissions")
        self.assertEqual(api_submissions.status_code, 200)

        teach_policy_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/set-enrollment-mode",
            {"enrollment_mode": "closed"},
        )
        self.assertEqual(teach_policy_mutation.status_code, 403)
        api_policy_mutation = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        self.assertEqual(api_policy_mutation.status_code, 403)
        teach_rotate_code = self.client.post(f"/teach/class/{self.classroom.id}/rotate-code")
        self.assertEqual(teach_rotate_code.status_code, 403)
        api_rotate_code = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/rotate-code")
        self.assertEqual(api_rotate_code.status_code, 403)
        teach_toggle_lock = self.client.post(f"/teach/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(teach_toggle_lock.status_code, 403)
        api_toggle_lock = self.client.post(f"/api/v1/teacher/class/{self.classroom.id}/toggle-lock")
        self.assertEqual(api_toggle_lock.status_code, 403)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_submission_view_grant_limits_submission_endpoints(self):
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.classroom,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        material_allowed = self.client.get(f"/teach/material/{self.upload_1.id}/submissions")
        self.assertEqual(material_allowed.status_code, 200)
        material_blocked = self.client.get(f"/teach/material/{self.upload_2.id}/submissions")
        self.assertEqual(material_blocked.status_code, 404)

        download_allowed = self.client.get(f"/submission/{self.upload_submission_1.id}/download")
        self.assertEqual(download_allowed.status_code, 200)
        download_blocked = self.client.get(f"/submission/{self.upload_submission_2.id}/download")
        self.assertEqual(download_blocked.status_code, 403)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_submission_delete_grant_limits_gallery_moderation(self):
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.classroom,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_DELETE,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        approve_allowed = self.client.post(
            f"/teach/material/{self.gallery_1.id}/submission/{self.gallery_submission_1.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(approve_allowed.status_code, 302)
        self.gallery_submission_1.refresh_from_db()
        self.assertTrue(self.gallery_submission_1.is_gallery_shared)

        approve_blocked = self.client.post(
            f"/teach/material/{self.gallery_2.id}/submission/{self.gallery_submission_2.id}/moderate",
            {"approve": "1"},
        )
        self.assertEqual(approve_blocked.status_code, 403)
        self.gallery_submission_2.refresh_from_db()
        self.assertFalse(self.gallery_submission_2.is_gallery_shared)

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_class_scoped_policy_and_roster_grants_can_deny_mutations(self):
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.classroom,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.classroom,
            user=self.staff,
            capability=ClassStaffModuleScopeGrant.CAP_ROSTER_MANAGE,
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )

        policy_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/set-enrollment-mode",
            {"enrollment_mode": "closed"},
        )
        self.assertEqual(policy_mutation.status_code, 403)
        api_policy_mutation = self.client.post(
            f"/api/v1/teacher/class/{self.classroom.id}/set-enrollment-mode",
            data=json.dumps({"enrollment_mode": "closed"}),
            content_type="application/json",
        )
        self.assertEqual(api_policy_mutation.status_code, 403)
        roster_mutation = self.client.post(
            f"/teach/class/{self.classroom.id}/rename-student",
            {"student_id": str(self.student.id), "display_name": "Denied Rename"},
        )
        self.assertEqual(roster_mutation.status_code, 403)
