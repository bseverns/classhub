import importlib
import os
import unittest
from unittest.mock import patch


class HelperSettingsContractTests(unittest.TestCase):
    def _reload_settings(self, overrides: dict[str, str]):
        import config.settings as helper_settings

        baseline_env = dict(os.environ)
        try:
            with patch.dict(os.environ, overrides, clear=True):
                return importlib.reload(helper_settings)
        finally:
            with patch.dict(os.environ, baseline_env, clear=True):
                importlib.reload(helper_settings)

    def test_cookie_transport_flags_are_env_configurable(self):
        settings = self._reload_settings(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "helper-settings-contract-secret-abcdefghijklmnopqrstuvwxyz",
                "DJANGO_SESSION_COOKIE_SECURE": "0",
                "DJANGO_CSRF_COOKIE_SECURE": "0",
            }
        )
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.CSRF_COOKIE_SECURE)

    def test_cookie_domains_follow_shared_env_contract(self):
        settings = self._reload_settings(
            {
                "DJANGO_DEBUG": "0",
                "DJANGO_SECRET_KEY": "helper-settings-contract-secret-abcdefghijklmnopqrstuvwxyz",
                "DJANGO_SESSION_COOKIE_DOMAIN": ".school.example.org",
                "DJANGO_CSRF_COOKIE_DOMAIN": ".school.example.org",
            }
        )
        self.assertEqual(settings.SESSION_COOKIE_DOMAIN, ".school.example.org")
        self.assertEqual(settings.CSRF_COOKIE_DOMAIN, ".school.example.org")


if __name__ == "__main__":
    unittest.main()
