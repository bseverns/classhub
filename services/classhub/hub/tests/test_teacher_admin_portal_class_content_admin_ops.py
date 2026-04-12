from ._shared import *  # noqa: F401,F403
from ._teacher_admin_portal_base import TeacherPortalBaseTests


class TeacherPortalClassContentAdminOpsTests(TeacherPortalBaseTests):
    @patch("hub.views.teacher_parts.content_home.generate_authoring_templates")
    def test_teach_home_can_generate_authoring_templates(self, mock_generate):
        mock_generate.return_value.output_paths = [
            Path("/uploads/authoring_templates/sample-teacher-plan-template.md"),
            Path("/uploads/authoring_templates/sample-teacher-plan-template.docx"),
            Path("/uploads/authoring_templates/sample-public-overview-template.md"),
            Path("/uploads/authoring_templates/sample-public-overview-template.docx"),
        ]
        _force_login_staff_verified(self.client, self.staff)

        resp = self.client.post(
            "/teach/generate-authoring-templates",
            {
                "template_slug": "sample_slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        self.assertIn("template_slug=sample_slug", resp["Location"])

        mock_generate.assert_called_once()
        kwargs = mock_generate.call_args.kwargs
        self.assertEqual(kwargs["slug"], "sample_slug")
        self.assertEqual(kwargs["title"], "Sample Course")
        self.assertEqual(kwargs["sessions"], 12)
        self.assertEqual(kwargs["duration"], 75)
        self.assertTrue(kwargs["overwrite"])

        event = AuditEvent.objects.filter(action="teacher_templates.generate").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
        self.assertEqual(event.target_id, "sample_slug")

    @patch("hub.views.teacher_parts.content_home.generate_authoring_templates")
    def test_teach_home_template_generator_rejects_invalid_slug(self, mock_generate):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/generate-authoring-templates",
            {
                "template_slug": "Bad Slug",
                "template_title": "Sample Course",
                "template_sessions": "12",
                "template_duration": "75",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        mock_generate.assert_not_called()

    def test_teacher_can_import_markdown_syllabus_source(self):
        _force_login_staff_verified(self.client, self.staff)
        source_md = """# Field Systems Studio

Program Profile: advanced
Grade Band: Grades 11-12
Meeting Time: 90 minutes

Session 01: Signals + Baselines
## Materials
- notebook

Session 02: Drift Tests
## Materials
- laptop
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "field_systems_studio",
                        "import_course_title": "",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("field_systems.md", source_md.encode("utf-8")),
                    },
                )

        self.assertEqual(resp.status_code, 200)
        buffer = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(buffer)) as zf:
            course_yaml = zf.read("field_systems_studio/course.yaml").decode("utf-8")
            self.assertIn('title: "Field Systems Studio"', course_yaml)
            self.assertIn("ui_level: advanced", course_yaml)
            lesson_files = [n for n in zf.namelist() if n.startswith("field_systems_studio/lessons/") and n.endswith(".md")]
            self.assertEqual(len(lesson_files), 2)

        event = AuditEvent.objects.filter(action="teacher_syllabus_import.compile").order_by("-id").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.target_id, "field_systems_studio")

    def test_staff_teacher_syllabus_import_compiles_valid_zip(self):
        teacher = get_user_model().objects.create_user(
            username="staff_teacher_import",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        _force_login_staff_verified(self.client, teacher)
        source_md = """# Course Forge

Session 01: Intro Builds
## Materials
- notebook

Session 02: Final Build
## Materials
- laptop
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "course_forge",
                        "import_course_title": "",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("course_forge.md", source_md.encode("utf-8")),
                    },
                )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/zip")
        self.assertTrue(resp["Content-Disposition"].startswith("attachment;"))

    def test_teacher_can_import_docx_syllabus_source(self):
        from ..services.authoring_templates import generate_authoring_templates

        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            template_dir = Path(temp_dir) / "templates"
            template_result = generate_authoring_templates(
                slug="docx_source",
                title="DOCX Source",
                sessions=2,
                duration=60,
                age_band="Grades 7-8",
                out_dir=template_dir,
                overwrite=True,
            )
            docx_bytes = template_result.teacher_plan_docx_path.read_bytes()
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "docx_source",
                        "import_course_title": "DOCX Source",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "template",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile(
                            "docx_source.docx",
                            docx_bytes,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    },
                )

        self.assertEqual(resp.status_code, 200)
        buffer = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(buffer)) as zf:
            course_yaml = zf.read("docx_source/course.yaml").decode("utf-8")
            self.assertIn('title: "DOCX Source"', course_yaml)
            lesson_files = [n for n in zf.namelist() if n.startswith("docx_source/lessons/") and n.endswith(".md")]
            self.assertEqual(len(lesson_files), 2)

    def test_teacher_can_import_zip_syllabus_source(self):
        _force_login_staff_verified(self.client, self.staff)
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "swarm/COURSE_DESCRIPTION.md",
                "# Swarm Aesthetics\n\nA studio course for drift and systems.",
            )
            archive.writestr(
                "swarm/sessions/session01_swarms_systems.md",
                "# Session 01 - Swarms & Systems\n\n## Materials\n- paper\n",
            )
            archive.writestr(
                "swarm/sessions/session02_drift.md",
                "# Session 02 - Drift Studies\n\n## Materials\n- laptop\n",
            )
            archive.writestr(
                "swarm/media/01-swarm-map.png",
                b"\x89PNG\r\n\x1a\n\x00\x00\x00IHDR",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "swarm_aesthetics",
                        "import_course_title": "",
                        "import_default_ui_level": "advanced",
                        "import_session_parse_mode": "verbose",
                        "import_overwrite": "1",
                        "syllabus_source": SimpleUploadedFile("swarm.zip", zip_buffer.getvalue(), content_type="application/zip"),
                    },
                )

        self.assertEqual(resp.status_code, 200)
        buffer = b"".join(resp.streaming_content)
        with zipfile.ZipFile(BytesIO(buffer)) as zf:
            course_yaml = zf.read("swarm_aesthetics/course.yaml").decode("utf-8")
            self.assertIn('title: "Swarm Aesthetics"', course_yaml)
            self.assertIn("ui_level: advanced", course_yaml)
            lesson_files = [n for n in zf.namelist() if n.startswith("swarm_aesthetics/lessons/") and n.endswith(".md")]
            self.assertEqual(len(lesson_files), 2)

    def test_teacher_syllabus_import_rejects_unsupported_extension(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/teach/import-syllabus-source",
                    {
                        "import_course_slug": "bad_source",
                        "import_default_ui_level": "secondary",
                        "import_session_parse_mode": "auto",
                        "syllabus_source": SimpleUploadedFile("bad_source.txt", b"hello"),
                    },
                )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertEqual(AuditEvent.objects.filter(action="teacher_syllabus_import.compile").count(), 0)

    def test_teach_home_shows_template_download_links_for_selected_slug(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            (template_dir / "sample_slug-teacher-plan-template.md").write_text("hello", encoding="utf-8")
            with override_settings(CLASSHUB_AUTHORING_TEMPLATE_DIR=template_dir):
                resp = self.client.get("/teach?template_slug=sample_slug")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/teach/authoring-template/download?slug=sample_slug&amp;kind=teacher_plan_md")
        self.assertContains(resp, "sample_slug-teacher-plan-template.docx (not generated yet)")

    def test_staff_can_download_generated_authoring_template(self):
        _force_login_staff_verified(self.client, self.staff)
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dir = Path(temp_dir)
            expected_path = template_dir / "sample_slug-teacher-plan-template.md"
            expected_path.write_text("sample-body", encoding="utf-8")
            with override_settings(CLASSHUB_AUTHORING_TEMPLATE_DIR=template_dir):
                resp = self.client.get("/teach/authoring-template/download?slug=sample_slug&kind=teacher_plan_md")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment;", resp["Content-Disposition"])
        self.assertIn("sample_slug-teacher-plan-template.md", resp["Content-Disposition"])
        body = b"".join(resp.streaming_content)
        self.assertEqual(body, b"sample-body")

        event = AuditEvent.objects.filter(action="teacher_templates.download").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_staff_download_authoring_template_rejects_invalid_kind(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/authoring-template/download?slug=sample_slug&kind=unknown_kind")
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Invalid template kind.", status_code=400)

    def test_staff_download_authoring_template_rejects_traversal_slug(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.get("/teach/authoring-template/download?slug=..%2Fetc%2Fpasswd&kind=teacher_plan_md")
        self.assertEqual(resp.status_code, 400)
        self.assertContains(resp, "Invalid template slug.", status_code=400)

    def test_superuser_teach_home_shows_org_admin_controls(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="UI Org Actions")
        teacher = get_user_model().objects.create_user(
            username="ui_membership_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=org,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        resp = self.client.get("/teach?portal_mode=admin&advanced=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Organizations + Staff Memberships")
        self.assertContains(resp, "/teach/create-organization")
        self.assertContains(resp, "/teach/org-membership/upsert")
        self.assertContains(resp, f"/teach/org/{org.id}/rename")
        self.assertContains(resp, "Archive")
        self.assertContains(resp, "Save role")
        self.assertContains(resp, "/teach/class-organization/set")
        self.assertContains(resp, "Move class organization")
        self.assertContains(resp, "/teach/teacher-account/set-active")
        self.assertContains(resp, "/teach/teacher-account/set-superuser")
        self.assertContains(resp, "/teach/teacher-account/reset-password")
        self.assertContains(resp, "/teach/teacher-account/resend-invite")

    def test_superuser_can_create_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        resp = self.client.post(
            "/teach/create-organization",
            {"org_name": "createMPLS Programs"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        created = Organization.objects.filter(name="createMPLS Programs").first()
        self.assertIsNotNone(created)

        event = AuditEvent.objects.filter(action="organization.create", target_id=str(created.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_upsert_organization_membership_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Membership Lab")
        teacher = get_user_model().objects.create_user(
            username="membership_teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

        create_resp = self.client.post(
            "/teach/org-membership/upsert",
            {
                "org_membership_org_id": str(org.id),
                "org_membership_user_id": str(teacher.id),
                "org_membership_role": OrganizationMembership.ROLE_ADMIN,
                "org_membership_active": "1",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        membership = OrganizationMembership.objects.get(organization=org, user=teacher)
        self.assertEqual(membership.role, OrganizationMembership.ROLE_ADMIN)
        self.assertTrue(membership.is_active)

        update_resp = self.client.post(
            "/teach/org-membership/upsert",
            {
                "org_membership_org_id": str(org.id),
                "org_membership_user_id": str(teacher.id),
                "org_membership_role": OrganizationMembership.ROLE_VIEWER,
                # unchecked checkbox -> inactive
            },
        )
        self.assertEqual(update_resp.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.role, OrganizationMembership.ROLE_VIEWER)
        self.assertFalse(membership.is_active)

        event = AuditEvent.objects.filter(action="organization.membership.upsert", target_id=str(membership.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_rename_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Rename Before")

        resp = self.client.post(
            f"/teach/org/{org.id}/rename",
            {"org_rename_name": "Org Rename After"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        org.refresh_from_db()
        self.assertEqual(org.name, "Org Rename After")
        event = AuditEvent.objects.filter(action="organization.rename", target_id=str(org.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_archive_organization_with_classes_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Archive Guard Org", is_active=True)
        Class.objects.create(name="Archive Guard Class", join_code="ARCH0001", organization=org)

        resp = self.client.post(f"/teach/org/{org.id}/set-active", {"is_active": "0"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        org.refresh_from_db()
        self.assertTrue(org.is_active)

    def test_superuser_can_move_class_organization_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org_source = Organization.objects.create(name="Move Source Org", is_active=True)
        org_target = Organization.objects.create(name="Move Target Org", is_active=True)
        classroom = Class.objects.create(name="Move Class Org", join_code="MOVC0001", organization=org_source)

        resp = self.client.post(
            "/teach/class-organization/set",
            {
                "class_move_class_id": str(classroom.id),
                "class_move_org_id": str(org_target.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?notice=", resp["Location"])
        classroom.refresh_from_db()
        self.assertEqual(classroom.organization_id, org_target.id)
        event = AuditEvent.objects.filter(action="class.organization.set", target_id=str(classroom.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
        self.assertEqual(event.metadata.get("organization_id"), org_target.id)

    def test_superuser_can_upsert_org_role_capability_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Role Capability Lab")

        resp = self.client.post(
            "/teach/org-role-capability/upsert",
            {
                "org_rolecap_org_id": str(org.id),
                "org_rolecap_role": OrganizationMembership.ROLE_TEACHER,
                "org_rolecap_capability": OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
                "org_rolecap_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        row = OrganizationRoleCapability.objects.filter(
            organization=org,
            role=OrganizationMembership.ROLE_TEACHER,
            capability=OrganizationRoleCapability.CAP_SYLLABUS_EXPORT,
        ).first()
        self.assertIsNotNone(row)
        self.assertTrue(row.is_active)
        event = AuditEvent.objects.filter(action="organization.role_capability.upsert", target_id=str(row.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_can_upsert_class_staff_assignment_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Class Assignment Lab", join_code="ASGN0001")
        target_staff = get_user_model().objects.create_user(
            username="class_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )

        create_resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_staff.id),
                "class_assignment_active": "1",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        assignment = ClassStaffAssignment.objects.get(classroom=classroom, user=target_staff)
        self.assertTrue(assignment.is_active)

        update_resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_staff.id),
                "class_assignment_active": "0",
            },
        )
        self.assertEqual(update_resp.status_code, 302)
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)

        event = AuditEvent.objects.filter(action="class.staff_assignment.upsert", target_id=str(assignment.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_cannot_assign_superuser_account_to_class(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Class Assignment Guard", join_code="ASGN0009")
        target_superuser = get_user_model().objects.create_user(
            username="class_assign_superuser_target",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )

        resp = self.client.post(
            "/teach/class-staff-assignment/upsert",
            {
                "class_assignment_class_id": str(classroom.id),
                "class_assignment_user_id": str(target_superuser.id),
                "class_assignment_active": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/teach?error=", resp["Location"])
        self.assertFalse(
            ClassStaffAssignment.objects.filter(
                classroom=classroom,
                user=target_superuser,
            ).exists()
        )

    def test_superuser_can_bulk_set_class_staff_assignments_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        class_a = Class.objects.create(name="Bulk Assign A", join_code="BULK0001")
        class_b = Class.objects.create(name="Bulk Assign B", join_code="BULK0002")
        class_c = Class.objects.create(name="Bulk Assign C", join_code="BULK0003")
        target_staff = get_user_model().objects.create_user(
            username="class_bulk_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        ClassStaffAssignment.objects.create(classroom=class_a, user=target_staff, is_active=True)
        ClassStaffAssignment.objects.create(classroom=class_b, user=target_staff, is_active=True)

        resp = self.client.post(
            "/teach/class-staff-assignment/bulk-set",
            {
                "class_assignment_bulk_user_id": str(target_staff.id),
                "class_assignment_bulk_class_ids": [str(class_b.id), str(class_c.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            ClassStaffAssignment.objects.get(classroom=class_a, user=target_staff).is_active
        )
        self.assertTrue(
            ClassStaffAssignment.objects.get(classroom=class_b, user=target_staff).is_active
        )
        self.assertTrue(
            ClassStaffAssignment.objects.get(classroom=class_c, user=target_staff).is_active
        )
        event = AuditEvent.objects.filter(action="class.staff_assignment.bulk_set", target_id=str(target_staff.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)

    def test_superuser_teach_home_shows_assign_teacher_link_per_class(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Per Class Assign Link", join_code="ASGN0002")

        resp = self.client.get("/teach?portal_mode=day")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"/teach?org_admin=1&class_assignment_class_id={classroom.id}")

    def test_superuser_teach_class_dashboard_shows_teaching_staff_assignments_panel(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Dashboard Assignment Lab", join_code="ASGN0004")
        target_staff = get_user_model().objects.create_user(
            username="dashboard_assign_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        ClassStaffAssignment.objects.create(classroom=classroom, user=target_staff, is_active=True)

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Teaching Staff Assignments")
        self.assertContains(resp, "dashboard_assign_target")
        self.assertContains(resp, "/teach/class-staff-assignment/upsert")

    def test_teach_class_assignment_picker_only_lists_teacher_accounts(self):
        _force_login_staff_verified(self.client, self.staff)
        classroom = Class.objects.create(name="Dashboard Assignment Filter", join_code="ASGN0010")
        teacher_user = get_user_model().objects.create_user(
            username="dashboard_teacher_target",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )
        superuser_user = get_user_model().objects.create_user(
            username="dashboard_superuser_target",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        resp = self.client.get(f"/teach/class/{classroom.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Select teacher account")
        self.assertContains(resp, f'value="{teacher_user.id}"', html=False)
        self.assertNotContains(resp, f'value="{superuser_user.id}"', html=False)

    def test_superuser_can_toggle_organization_active_from_teach(self):
        _force_login_staff_verified(self.client, self.staff)
        org = Organization.objects.create(name="Org Toggle Lab", is_active=True)

        resp = self.client.post(f"/teach/org/{org.id}/set-active", {"is_active": "0"})
        self.assertEqual(resp.status_code, 302)
        org.refresh_from_db()
        self.assertFalse(org.is_active)

        event = AuditEvent.objects.filter(action="organization.set_active", target_id=str(org.id)).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.staff.id)
