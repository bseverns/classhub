"""Compatibility smoke test for Class Hub student view.

This module can be discovered by test runners for either Django service.
When running under Homework Helper settings (which do not include the
`hub` app), we skip import-time work so unrelated test suites still run.
"""

from __future__ import annotations

import json
import unittest

from django.apps import apps
from django.conf import settings


def _is_hub_installed() -> bool:
    """Support both `hub` and `hub.apps.HubConfig` style app entries."""
    try:
        return apps.is_installed("hub")
    except Exception:
        installed = {str(item).strip() for item in getattr(settings, "INSTALLED_APPS", [])}
        return "hub" in installed or "hub.apps.HubConfig" in installed


if not _is_hub_installed():
    raise unittest.SkipTest("Class Hub smoke test skipped: 'hub' app is not installed in this settings module.")


from django.test import TestCase, override_settings

from hub.models import Class, StudentIdentity


_SMOKE_TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


@override_settings(STORAGES=_SMOKE_TEST_STORAGES)
class StudentHomeSmokeTests(TestCase):
    def test_student_join_then_student_home_returns_200(self):
        classroom = Class.objects.create(name="Smoke Class", join_code="SMOKE123")

        join_response = self.client.post(
            "/join",
            data=json.dumps({"class_code": classroom.join_code, "display_name": "Smoke Student"}),
            content_type="application/json",
        )
        self.assertEqual(join_response.status_code, 200)
        self.assertTrue(join_response.json().get("ok"))

        student_response = self.client.get("/student")
        self.assertEqual(student_response.status_code, 200)

        student = StudentIdentity.objects.filter(classroom=classroom).first()
        self.assertIsNotNone(student)
