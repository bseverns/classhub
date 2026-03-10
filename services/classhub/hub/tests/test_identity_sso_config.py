import os
import unittest
from unittest.mock import patch

import environ

from config.identity_sso import build_teacher_sso_settings


class TeacherSSOConfigTests(unittest.TestCase):
    def _build(self, overrides: dict[str, str]):
        with patch.dict(os.environ, overrides, clear=True):
            return build_teacher_sso_settings(environ.Env())

    def test_disabled_by_default(self):
        settings = self._build({})
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.enabled_providers, ())
        self.assertEqual(settings.providers, {})

    def test_enabled_requires_provider_list(self):
        with self.assertRaises(RuntimeError):
            self._build(
                {
                    "CLASSHUB_TEACHER_SSO_ENABLED": "1",
                }
            )

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self._build(
                {
                    "CLASSHUB_TEACHER_SSO_ENABLED": "1",
                    "CLASSHUB_TEACHER_SSO_PROVIDERS": "bogus",
                }
            )

    def test_google_provider_minimum_config(self):
        settings = self._build(
            {
                "CLASSHUB_TEACHER_SSO_ENABLED": "1",
                "CLASSHUB_TEACHER_SSO_PROVIDERS": "google",
                "CLASSHUB_SSO_GOOGLE_CLIENT_ID": "google-client-id",
                "CLASSHUB_SSO_GOOGLE_CLIENT_SECRET": "google-client-secret",
                "CLASSHUB_SSO_GOOGLE_HOSTED_DOMAINS": "school.org, district.org",
            }
        )
        self.assertTrue(settings.enabled)
        self.assertEqual(settings.enabled_providers, ("google",))
        google = settings.providers["google"]
        self.assertEqual(google.provider_key, "google")
        self.assertEqual(google.client_id, "google-client-id")
        self.assertEqual(google.allowed_domains, ("school.org", "district.org"))

    def test_custom_provider_requires_issuer_and_discovery(self):
        with self.assertRaises(RuntimeError):
            self._build(
                {
                    "CLASSHUB_TEACHER_SSO_ENABLED": "1",
                    "CLASSHUB_TEACHER_SSO_PROVIDERS": "oidc_custom",
                    "CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_ID": "client-id",
                    "CLASSHUB_SSO_OIDC_CUSTOM_CLIENT_SECRET": "client-secret",
                }
            )


if __name__ == "__main__":
    unittest.main()

