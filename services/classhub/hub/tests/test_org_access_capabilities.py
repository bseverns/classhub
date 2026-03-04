from ._shared import *  # noqa: F401,F403

from ..models import ClassStaffModuleScopeGrant
from ..services.org_access import (
    CAP_CLASS_CREATE,
    CAP_CLASS_MANAGE,
    CAP_POLICY_MANAGE,
    CAP_ROSTER_MANAGE,
    CAP_SUBMISSION_DELETE,
    CAP_SUBMISSION_VIEW,
    CAP_SYLLABUS_EXPORT,
    evaluate_staff_capability,
    staff_can,
    staff_can_access_classroom,
    staff_can_create_classes,
    staff_can_export_syllabi,
    staff_can_manage_classroom,
)


class StaffCapabilityEvaluatorTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.org_a = Organization.objects.create(name="Org A")
        self.org_b = Organization.objects.create(name="Org B")
        self.class_a = Class.objects.create(name="Class A", join_code="ORGA1234", organization=self.org_a)
        self.class_b = Class.objects.create(name="Class B", join_code="ORGB1234", organization=self.org_b)
        self.module_a = Module.objects.create(classroom=self.class_a, title="Module 1", order_index=0)
        self.module_a_2 = Module.objects.create(classroom=self.class_a, title="Module 2", order_index=1)
        self.module_a_3 = Module.objects.create(classroom=self.class_a, title="Module 3", order_index=2)
        self.module_b = Module.objects.create(classroom=self.class_b, title="Module 1", order_index=0)

    def test_superuser_allows_known_capabilities(self):
        superuser = self.User.objects.create_user(
            username="root",
            password="pw12345",
            is_staff=True,
            is_superuser=True,
        )
        self.assertTrue(staff_can(superuser, CAP_CLASS_MANAGE, classroom=self.class_a))
        self.assertTrue(
            staff_can(
                superuser,
                CAP_SUBMISSION_DELETE,
                classroom=self.class_a,
                module_id=self.module_a.id,
            )
        )
        self.assertFalse(
            staff_can(
                superuser,
                CAP_SUBMISSION_DELETE,
                classroom=self.class_a,
                module_id=self.module_b.id,
            )
        )

    def test_unknown_capability_denied(self):
        staff = self.User.objects.create_user(
            username="staff",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        decision = evaluate_staff_capability(staff, "not.real", classroom=self.class_a)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "unknown_capability")

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=False)
    def test_legacy_no_membership_fallback_keeps_class_management(self):
        staff = self.User.objects.create_user(
            username="legacy",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.assertTrue(staff_can_create_classes(staff))
        self.assertTrue(staff_can_manage_classroom(staff, self.class_a))
        self.assertTrue(staff_can_access_classroom(staff, self.class_a))
        self.assertTrue(staff_can(staff, CAP_ROSTER_MANAGE, classroom=self.class_a))
        self.assertTrue(staff_can(staff, CAP_POLICY_MANAGE, classroom=self.class_a))
        self.assertTrue(staff_can(staff, CAP_SUBMISSION_VIEW, classroom=self.class_a))
        self.assertTrue(staff_can(staff, CAP_SUBMISSION_DELETE, classroom=self.class_a))
        self.assertFalse(staff_can_export_syllabi(staff))

    @override_settings(REQUIRE_ORG_MEMBERSHIP_FOR_STAFF=True)
    def test_membership_required_mode_denies_staff_without_membership(self):
        staff = self.User.objects.create_user(
            username="locked_out",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        self.assertFalse(staff_can_create_classes(staff))
        self.assertFalse(staff_can_manage_classroom(staff, self.class_a))
        self.assertFalse(staff_can_access_classroom(staff, self.class_a))
        self.assertFalse(staff_can(staff, CAP_SUBMISSION_VIEW, classroom=self.class_a))
        self.assertFalse(staff_can(staff, CAP_SUBMISSION_DELETE, classroom=self.class_a))
        self.assertFalse(staff_can_export_syllabi(staff))

    def test_viewer_role_is_read_only(self):
        viewer = self.User.objects.create_user(
            username="viewer",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=viewer,
            role=OrganizationMembership.ROLE_VIEWER,
            is_active=True,
        )
        self.assertTrue(staff_can_access_classroom(viewer, self.class_a))
        self.assertFalse(staff_can_manage_classroom(viewer, self.class_a))
        self.assertFalse(staff_can_create_classes(viewer))
        self.assertFalse(staff_can_export_syllabi(viewer))
        self.assertTrue(staff_can(viewer, CAP_SUBMISSION_VIEW, classroom=self.class_a))
        self.assertFalse(staff_can(viewer, CAP_SUBMISSION_DELETE, classroom=self.class_a))
        self.assertFalse(staff_can_access_classroom(viewer, self.class_b))

    def test_teacher_role_can_manage_but_not_export(self):
        teacher = self.User.objects.create_user(
            username="teacher-role",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        self.assertTrue(staff_can_create_classes(teacher))
        self.assertTrue(staff_can_manage_classroom(teacher, self.class_a))
        self.assertTrue(staff_can(teacher, CAP_SUBMISSION_DELETE, classroom=self.class_a))
        self.assertFalse(staff_can_export_syllabi(teacher))

    def test_admin_role_can_export_syllabus(self):
        admin = self.User.objects.create_user(
            username="admin-role",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=admin,
            role=OrganizationMembership.ROLE_ADMIN,
            is_active=True,
        )
        self.assertTrue(staff_can(admin, CAP_SYLLABUS_EXPORT))
        self.assertTrue(staff_can_export_syllabi(admin))

    def test_module_scope_requires_module_belongs_to_classroom(self):
        teacher = self.User.objects.create_user(
            username="scoped-teacher",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        self.assertTrue(
            staff_can(
                teacher,
                CAP_SUBMISSION_VIEW,
                classroom=self.class_a,
                module_id=self.module_a.id,
            )
        )
        self.assertFalse(
            staff_can(
                teacher,
                CAP_SUBMISSION_VIEW,
                classroom=self.class_a,
                module_id=self.module_b.id,
            )
        )

    def test_unscoped_membership_denies_module_scope(self):
        teacher = self.User.objects.create_user(
            username="module-only",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        decision = evaluate_staff_capability(
            teacher,
            CAP_CLASS_CREATE,
            module_id=self.module_a.id,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "invalid_module_scope")

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_grants_enabled_without_rows_preserves_role_allow(self):
        teacher = self.User.objects.create_user(
            username="scoped-fallback",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        decision = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a_2.id,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "role_allows_capability_no_scoped_grants")

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_module_range_grant_allows_only_configured_range(self):
        teacher = self.User.objects.create_user(
            username="module-range",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=teacher,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            module_order_start=0,
            module_order_end=1,
            is_active=True,
        )

        inside = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a_2.id,
        )
        self.assertTrue(inside.allowed)
        self.assertEqual(inside.reason, "scoped_grant_allows")

        outside = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a_3.id,
        )
        self.assertFalse(outside.allowed)
        self.assertEqual(outside.reason, "scoped_grant_denied")

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=True)
    def test_scoped_explicit_deny_overrides_allow_when_ranges_overlap(self):
        teacher = self.User.objects.create_user(
            username="module-range-deny",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=teacher,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            effect=ClassStaffModuleScopeGrant.EFFECT_ALLOW,
            module_order_start=0,
            module_order_end=2,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=teacher,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            effect=ClassStaffModuleScopeGrant.EFFECT_DENY,
            module_order_start=1,
            module_order_end=1,
            is_active=True,
        )

        denied = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a_2.id,
        )
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason, "scoped_grant_explicit_deny")

        allowed = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a.id,
        )
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.reason, "scoped_grant_allows")

    @override_settings(CLASSHUB_RBAC_SCOPED_GRANTS_ENABLED=False)
    def test_scoped_module_range_grant_disabled_ignores_rows(self):
        teacher = self.User.objects.create_user(
            username="module-range-off",
            password="pw12345",
            is_staff=True,
            is_superuser=False,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=teacher,
            role=OrganizationMembership.ROLE_TEACHER,
            is_active=True,
        )
        ClassStaffModuleScopeGrant.objects.create(
            classroom=self.class_a,
            user=teacher,
            capability=ClassStaffModuleScopeGrant.CAP_SUBMISSION_VIEW,
            module_order_start=0,
            module_order_end=0,
            is_active=True,
        )
        decision = evaluate_staff_capability(
            teacher,
            CAP_SUBMISSION_VIEW,
            classroom=self.class_a,
            module_id=self.module_a_3.id,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "role_allows_capability")
