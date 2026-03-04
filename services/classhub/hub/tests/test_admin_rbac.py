from ._shared import *  # noqa: F401,F403

from django.contrib import admin


class AdminRBACRegistrationTests(SimpleTestCase):
    def test_class_staff_module_scope_grant_registered(self):
        self.assertIn(ClassStaffModuleScopeGrant, admin.site._registry)
