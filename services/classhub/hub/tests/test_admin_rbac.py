from ._shared import *  # noqa: F401,F403

from django.contrib import admin
from django.test import RequestFactory

from ..admin import (
    ClassAdmin,
    ClassStaffModuleScopeGrantAdmin,
    OrganizationCustomRoleAdmin,
    OrganizationCustomRoleAssignmentAdmin,
)


class AdminRBACRegistrationTests(SimpleTestCase):
    def test_class_staff_module_scope_grant_registered(self):
        self.assertIn(ClassStaffModuleScopeGrant, admin.site._registry)

    def test_custom_role_models_registered(self):
        self.assertIn(OrganizationCustomRole, admin.site._registry)
        self.assertIn(OrganizationCustomRoleCapability, admin.site._registry)
        self.assertIn(OrganizationCustomRoleAssignment, admin.site._registry)
        self.assertIn(RbacPolicyChangeRequest, admin.site._registry)


class AdminRBACAuditTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = get_user_model().objects.create_user(
            username="rbac_admin",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )
        self.classroom = Class.objects.create(name="RBAC Audit Class", join_code="RBACAU01")
        self.staff_user = get_user_model().objects.create_user(
            username="rbac_staff",
            password="pw12345",
            is_staff=True,
        )
        self.org = Organization.objects.create(name="RBAC Admin Org")
        self.model_admin = ClassStaffModuleScopeGrantAdmin(ClassStaffModuleScopeGrant, admin.site)
        self.custom_role_admin = OrganizationCustomRoleAdmin(OrganizationCustomRole, admin.site)
        self.custom_role_assignment_admin = OrganizationCustomRoleAssignmentAdmin(
            OrganizationCustomRoleAssignment,
            admin.site,
        )

    def _request(self):
        request = self.factory.post("/admin/hub/classstaffmodulescopegrant/")
        request.user = self.admin_user
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        return request

    def test_create_update_delete_scoped_grant_writes_audit_events(self):
        request = self._request()
        grant = ClassStaffModuleScopeGrant(
            classroom=self.classroom,
            user=self.staff_user,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=1,
            is_active=True,
        )
        self.model_admin.save_model(request, grant, form=None, change=False)

        create_event = AuditEvent.objects.filter(action="rbac.scope_grant.create", target_id=str(grant.id)).first()
        self.assertIsNotNone(create_event)
        self.assertEqual(create_event.metadata.get("effect"), ClassStaffModuleScopeGrant.EFFECT_ALLOW)

        grant.effect = ClassStaffModuleScopeGrant.EFFECT_DENY
        self.model_admin.save_model(request, grant, form=None, change=True)

        update_event = AuditEvent.objects.filter(action="rbac.scope_grant.update", target_id=str(grant.id)).first()
        self.assertIsNotNone(update_event)
        self.assertEqual(update_event.metadata.get("effect"), ClassStaffModuleScopeGrant.EFFECT_DENY)

        grant_id = grant.id
        self.model_admin.delete_model(request, grant)
        delete_event = AuditEvent.objects.filter(action="rbac.scope_grant.delete", target_id=str(grant_id)).first()
        self.assertIsNotNone(delete_event)


    def test_custom_role_create_update_delete_writes_audit_events(self):
        request = self._request()
        role = OrganizationCustomRole(
            organization=self.org,
            slug="district_exporter",
            name="District Exporter",
            is_active=True,
        )
        self.custom_role_admin.save_model(request, role, form=None, change=False)

        create_event = AuditEvent.objects.filter(action="organization.custom_role.create", target_id=str(role.id)).first()
        self.assertIsNotNone(create_event)

        role.name = "District Export + Policy"
        self.custom_role_admin.save_model(request, role, form=None, change=True)
        update_event = AuditEvent.objects.filter(action="organization.custom_role.update", target_id=str(role.id)).first()
        self.assertIsNotNone(update_event)

        role_id = role.id
        self.custom_role_admin.delete_model(request, role)
        delete_event = AuditEvent.objects.filter(action="organization.custom_role.delete", target_id=str(role_id)).first()
        self.assertIsNotNone(delete_event)

    def test_custom_role_assignment_create_delete_writes_audit_events(self):
        request = self._request()
        role = OrganizationCustomRole.objects.create(
            organization=self.org,
            slug="ops_observer",
            name="Ops Observer",
            is_active=True,
        )
        assignment = OrganizationCustomRoleAssignment(
            organization=self.org,
            user=self.staff_user,
            role=role,
            is_active=True,
        )
        self.custom_role_assignment_admin.save_model(request, assignment, form=None, change=False)

        create_event = AuditEvent.objects.filter(
            action="organization.custom_role_assignment.create",
            target_id=str(assignment.id),
        ).first()
        self.assertIsNotNone(create_event)

        assignment_id = assignment.id
        self.custom_role_assignment_admin.delete_model(request, assignment)
        delete_event = AuditEvent.objects.filter(
            action="organization.custom_role_assignment.delete",
            target_id=str(assignment_id),
        ).first()
        self.assertIsNotNone(delete_event)


class AdminCoursepackZipImportTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="coursepack_admin",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )

    def _coursepack_zip(self, *, slug: str = "admin_zip_course") -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                f"{slug}/course.yaml",
                f"""slug: {slug}
title: "Admin ZIP Course"
sessions: 2
default_duration_minutes: 75
lessons:
  - session: 1
    slug: s01-first-build
    title: "First Build"
    file: lessons/01-first-build.md
  - session: 2
    slug: s02-second-build
    title: "Second Build"
    file: lessons/02-second-build.md
""",
            )
            archive.writestr(
                f"{slug}/lessons/01-first-build.md",
                """---
course: admin_zip_course
session: 1
slug: s01-first-build
title: "First Build"
makes: "A first prototype"
submission:
  type: file
  naming: first_build.sb3
  accepted:
    - .sb3
---
# First Build
""",
            )
            archive.writestr(
                f"{slug}/lessons/02-second-build.md",
                """---
course: admin_zip_course
session: 2
slug: s02-second-build
title: "Second Build"
---
# Second Build
""",
            )
        return buffer.getvalue()

    def test_class_changelist_links_coursepack_import_tool(self):
        _force_login_staff_verified(self.client, self.admin_user)

        resp = self.client.get("/admin/hub/class/")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Import course content")
        self.assertContains(resp, "/admin/hub/class/import-coursepack/")

    def test_non_superuser_cannot_use_live_course_import_tool(self):
        staff_user = get_user_model().objects.create_user(
            username="coursepack_staff",
            password="pw12345",
            is_staff=True,
        )
        request = RequestFactory().get("/admin/hub/class/import-coursepack/")
        request.user = staff_user
        model_admin = ClassAdmin(Class, admin.site)

        resp = model_admin.import_coursepack_view(request)

        self.assertEqual(resp.status_code, 403)

    def test_superuser_can_import_coursepack_zip_from_admin(self):
        _force_login_staff_verified(self.client, self.admin_user)
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir) / "content"
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.post(
                    "/admin/hub/class/import-coursepack/",
                    {
                        "class_name": "Admin ZIP Cohort",
                        "create_class": "on",
                        "coursepack_zip": SimpleUploadedFile(
                            "admin_zip_course.zip",
                            self._coursepack_zip(),
                            content_type="application/zip",
                        ),
                    },
                    follow=True,
                )

                self.assertEqual(resp.status_code, 200)
                self.assertTrue((content_root / "courses" / "admin_zip_course" / "course.yaml").exists())

        classroom = Class.objects.get(name="Admin ZIP Cohort")
        self.assertEqual(classroom.modules.count(), 2)
        self.assertEqual(
            Material.objects.filter(module__classroom=classroom, title="Open lesson").count(),
            2,
        )
        self.assertTrue(Material.objects.filter(module__classroom=classroom, title="Homework dropbox").exists())

        event = AuditEvent.objects.filter(action="admin.coursepack_zip.import").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_user_id, self.admin_user.id)
        self.assertEqual(event.target_id, "admin_zip_course")
        self.assertEqual(event.metadata["created_modules"], 2)

    def test_course_content_import_rejects_unsupported_upload(self):
        _force_login_staff_verified(self.client, self.admin_user)

        resp = self.client.post(
            "/admin/hub/class/import-coursepack/",
            {
                "class_name": "Bad Upload",
                "create_class": "on",
                "coursepack_zip": SimpleUploadedFile("coursepack.txt", b"not a zip"),
            },
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Upload a .zip, .docx, or .md source file.")
        self.assertFalse(Class.objects.filter(name="Bad Upload").exists())
