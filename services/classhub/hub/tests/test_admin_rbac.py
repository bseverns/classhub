from ._shared import *  # noqa: F401,F403

from django.contrib import admin
from django.test import RequestFactory

from ..admin import ClassStaffModuleScopeGrantAdmin


class AdminRBACRegistrationTests(SimpleTestCase):
    def test_class_staff_module_scope_grant_registered(self):
        self.assertIn(ClassStaffModuleScopeGrant, admin.site._registry)


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
        self.model_admin = ClassStaffModuleScopeGrantAdmin(ClassStaffModuleScopeGrant, admin.site)

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
