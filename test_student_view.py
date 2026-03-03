"""Compatibility smoke test for Class Hub student view.

This module can be discovered by test runners for either Django service.
When running under Homework Helper settings (which do not include the
`hub` app), we skip import-time work so unrelated test suites still run.
"""

from __future__ import annotations

import unittest

from django.conf import settings


if "hub" not in settings.INSTALLED_APPS:
    raise unittest.SkipTest("Class Hub smoke test skipped: 'hub' app is not installed in this settings module.")


from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from hub.models import Class, StudentIdentity
from hub.views.student import student_home


class StudentHomeSmokeTests(TestCase):
    def test_student_home_returns_http_response(self):
        classroom = Class.objects.first()
        student = StudentIdentity.objects.first()
        if classroom is None or student is None:
            self.skipTest("Requires seeded Class and StudentIdentity rows.")

        request = RequestFactory().get("/student")
        request.user = AnonymousUser()
        request.classroom = classroom
        request.student = student

        response = student_home(request)
        self.assertIsNotNone(response)
        self.assertTrue(hasattr(response, "status_code"))
