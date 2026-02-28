from ._shared import *  # noqa: F401,F403


class I18nSmokeTests(TestCase):
    """Integration tests for i18n scaffolding."""

    def test_join_page_english_by_default(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Join your class")

    def test_join_page_with_spanish_accept_language(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Únete a tu clase")

    def test_join_page_spanish_shows_translated_label(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp, "Código de clase")

    def test_join_page_spanish_shows_translated_help_text(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp, "no necesitas usar tu nombre real")

    def test_set_language_persists_across_requests(self):
        # POST to set_language to switch to Spanish
        resp = self.client.post(
            "/i18n/setlang/",
            {"language": "es", "next": "/"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        # Now subsequent GET should be in Spanish
        resp2 = self.client.get("/")
        self.assertContains(resp2, "Únete a tu clase")

    def test_teach_login_english_by_default(self):
        resp = self.client.get("/teach/login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Teacher Login")

    def test_teach_login_with_spanish_accept_language(self):
        resp = self.client.get("/teach/login", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Inicio de sesión del maestro")

    def test_language_chooser_visible_on_join_page(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'action="/i18n/setlang/"')
        self.assertContains(resp, 'name="language"')

    def test_language_chooser_visible_on_login_page(self):
        resp = self.client.get("/teach/login")
        self.assertContains(resp, 'action="/i18n/setlang/"')

    def test_html_lang_attribute_english(self):
        resp = self.client.get("/")
        self.assertContains(resp, '<html lang="en">')

    def test_html_lang_attribute_spanish(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp, '<html lang="es">')

    def test_i18n_url_allowed_in_join_only_site_mode(self):
        """Language switching should work even in join-only site mode."""
        with self.settings(SITE_MODE="join-only"):
            resp = self.client.post(
                "/i18n/setlang/",
                {"language": "es", "next": "/"},
                follow=True,
            )
            self.assertEqual(resp.status_code, 200)
