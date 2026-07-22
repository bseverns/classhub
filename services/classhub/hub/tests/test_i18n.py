from ._shared import *  # noqa: F401,F403
from django.utils import translation
from django.utils.translation import gettext as _


class I18nSmokeTests(TestCase):
    """Integration tests for i18n scaffolding."""

    def _set_student_session(self) -> tuple[Class, StudentIdentity]:
        classroom = Class.objects.create(name="I18N Class", join_code="I18N1234")
        student = StudentIdentity.objects.create(classroom=classroom, display_name="Ada")
        session = self.client.session
        session["class_id"] = classroom.id
        session["student_id"] = student.id
        session.save()
        return classroom, student

    def _set_student_session_with_course_link(self) -> tuple[Class, StudentIdentity]:
        classroom, student = self._set_student_session()
        module = Module.objects.create(classroom=classroom, title="I18N lesson")
        Material.objects.create(
            module=module,
            title="I18N course lesson",
            type=Material.TYPE_LINK,
            url="/course/demo-course/demo-lesson",
        )
        return classroom, student

    def _write_lesson_locale_fixture(self, content_root: Path) -> None:
        manifest = """
title: "Neighborhood Circuits"
lessons:
  - slug: s01-neighborhood-circuits
    title: "Neighborhood Circuits"
    file: "lessons/01-neighborhood-circuits.md"
"""
        lesson = """---
title: Neighborhood Circuits
makes: "A small circuit plan you can explain."
offline_handout:
  subtitle: "Build, explain, and upload one circuit idea."
  do_now:
    - Sketch one circuit idea.
  reading_levels:
    simple:
      do_now:
        - Draw one circuit.
      submit:
        - Upload one PDF page.
---
## Build

Draw, test, and explain one loop.
"""
        course_dir = content_root / "courses" / "neighborhood_circuits"
        lesson_dir = course_dir / "lessons"
        lesson_dir.mkdir(parents=True, exist_ok=True)
        (course_dir / "course.yaml").write_text(manifest, encoding="utf-8")
        (lesson_dir / "01-neighborhood-circuits.md").write_text(lesson, encoding="utf-8")

    def _assert_lesson_route_i18n(
        self,
        *,
        route: str,
        language: str,
        expected_reading_label: str,
        expected_reading_value: str,
        expected_section_label: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(route, HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, expected_reading_label)
        self.assertContains(resp, expected_reading_value)
        self.assertContains(resp, expected_section_label)

    def test_join_page_english_by_default(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Join your class")

    def test_join_page_with_spanish_accept_language(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Únete a tu clase")

    def test_join_page_with_somali_accept_language(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ku biir fasalkaaga")

    def test_join_page_with_sgaw_karen_accept_language(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="ksw">')

    def test_join_page_spanish_shows_translated_label(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp, "Código de clase")

    def test_join_page_sgaw_karen_shows_translated_label(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertContains(resp, "တီၤအကီၢ်")

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

    def test_set_language_persists_across_requests_for_sgaw_karen(self):
        resp = self.client.post(
            "/i18n/setlang/",
            {"language": "ksw", "next": "/"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        resp2 = self.client.get("/")
        self.assertContains(resp2, '<html lang="ksw">')
        self.assertEqual(resp2.wsgi_request.localization.code, "ksw")
        self.assertEqual(resp2.context["localization"].helper_code, "ksw")

    def test_teach_login_english_by_default(self):
        resp = self.client.get("/teach/login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Teacher Login")

    def test_teach_login_with_spanish_accept_language(self):
        resp = self.client.get("/teach/login", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Inicio de sesión del maestro")

    def test_teach_login_with_somali_accept_language(self):
        resp = self.client.get("/teach/login", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Gelitaanka Macallinka")

    def test_teach_login_with_sgaw_karen_accept_language(self):
        resp = self.client.get("/teach/login", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ဆရာ/မ အတၢ်နုာ်လီၤ")

    def test_language_chooser_visible_on_join_page(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'action="/i18n/setlang/"')
        self.assertContains(resp, 'name="language"')

    def test_language_chooser_visible_on_login_page(self):
        resp = self.client.get("/teach/login")
        self.assertContains(resp, 'action="/i18n/setlang/"')

    def test_language_chooser_lists_sgaw_karen(self):
        resp = self.client.get("/")
        self.assertContains(resp, '<option value="ksw"')

    def test_html_lang_attribute_english(self):
        resp = self.client.get("/")
        self.assertContains(resp, '<html lang="en">')

    def test_html_lang_attribute_spanish(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp, '<html lang="es">')

    def test_html_lang_attribute_somali(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="so")
        self.assertContains(resp, '<html lang="so">')

    def test_html_lang_attribute_sgaw_karen(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertContains(resp, '<html lang="ksw">')

    def test_request_localization_context_uses_active_language(self):
        resp = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.wsgi_request.localization.code, "es")
        self.assertEqual(resp.wsgi_request.localization.helper_code, "es")
        self.assertEqual(resp.context["localization"].code, "es")

    def test_handout_service_labels_translate_in_shipped_languages(self):
        expectations = {
            "es": {
                "choose_language": "Elige un idioma",
                "handout_language": "Idioma de la guía",
                "submit": "Qué entregar",
                "peer_feedback": "Comentarios entre compañeros",
                "download_pdf": "Descargar PDF de la guía",
                "simple_language_help": "Usa estos enlaces para abrir la misma guía en el idioma que tu clase lee mejor.",
                "standard_language_help": "Usa estos botones para cambiar la guía imprimible a otro idioma antes de imprimirla o compartirla.",
            },
            "so": {
                "choose_language": "Dooro luqad",
                "handout_language": "Luqadda warqadda casharka",
                "submit": "Waxa la gudbinayo",
                "peer_feedback": "Faallooyinka ardayda kale",
                "download_pdf": "Soo dejiso PDF-ka warqadda casharka",
                "simple_language_help": "Isticmaal xiriirradan si aad isla warqadda casharka ugu furto luqadda ay fasalkaagu sida fiican ugu akhriyaan.",
                "standard_language_help": "Isticmaal badhamadan si aad warqadda casharka la daabici karo ugu beddesho luqad kale ka hor intaadan daabicin ama wadaagin.",
            },
            "ksw": {
                "choose_language": "ဃုထၢ ကျိာ်",
                "handout_language": "handout အကျိာ်",
                "submit": "ပာ်ဃုာ်တၢ်မနုၤလဲၣ်",
                "peer_feedback": "တီၤဖိအတၢ်စံးဆၢ",
                "download_pdf": "ဒုးလီၤကလ့ၣ် handout PDF",
                "simple_language_help": "သူၣ်ထီၣ် link တဖၣ်အံၤ ဒ်သိးနကအိးထီၣ် handout တပုာ်ဃီ လၢကျိာ်လၢနတီၤဖိဖးတၢ်အဂ့ၤကတၢၢ်တခါ.",
                "standard_language_help": "သူၣ်ထီၣ် button တဖၣ်အံၤ ဒ်သိးနကလဲၤလိာ် printable handout ဆူကျိာ်အဂၤတခါ ဖဲနတချုး print မ့တမ့ၢ် share တချုး.",
            },
        }

        for language_code, labels in expectations.items():
            with self.subTest(language_code=language_code), translation.override(language_code):
                self.assertEqual(_("Choose a language"), labels["choose_language"])
                self.assertEqual(_("Handout language"), labels["handout_language"])
                self.assertEqual(_("What to submit"), labels["submit"])
                self.assertEqual(_("Peer feedback"), labels["peer_feedback"])
                self.assertEqual(_("Download handout PDF"), labels["download_pdf"])
                self.assertEqual(
                    _("Use these links to open the same handout in the language your class reads best."),
                    labels["simple_language_help"],
                )
                self.assertEqual(
                    _("Use these buttons to switch the printable handout into another language before you print or share it."),
                    labels["standard_language_help"],
                )

    def test_student_helper_widget_uses_request_localization(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-helper-language-code="ksw"')

    def test_student_helper_widget_chrome_uses_spanish_template_i18n(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-i18n-summary-open="Abrir ayudante"')
        self.assertContains(resp, 'data-i18n-reset-button="Reiniciar chat"')

    def test_student_helper_widget_chrome_uses_somali_template_i18n(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-i18n-summary-open="Fur caawiye"')
        self.assertContains(resp, 'data-i18n-reset-button="Dib u deji chat-ka"')

    def test_student_helper_widget_chrome_uses_sgaw_karen_template_i18n(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-i18n-summary-open="အိးထီၣ် တၢ်မၤစၢၤ"')
        self.assertContains(resp, 'data-i18n-reset-button="ဒုးက့ၤ chat"')

    def test_student_helper_widget_quick_prompts_use_spanish_template_payload(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '"label": "Salto no funciona"')
        self.assertContains(resp, '"prompt": "En StoryMode, izquierda y derecha funcionan pero saltar no funciona en Cheeseteroid. Ayudame a revisar un paso a la vez."')

    def test_student_helper_widget_quick_prompts_use_somali_template_payload(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '"label": "Jump ma shaqeeyo"')
        self.assertContains(resp, '"prompt": "StoryMode gudaheeda, bidix iyo midig way shaqeeyaan laakiin jump-ku kama shaqeeyo Cheeseteroid. Iga caawi hal talaabo markiiba."')

    def test_student_helper_widget_quick_prompts_use_sgaw_karen_template_payload(self):
        self._set_student_session()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '"label": "Jump တမၤဘၣ်"')
        self.assertContains(resp, '"prompt": "StoryMode အပူၤ left/right မၤတၢ် ဘၣ်ဆၣ် jump တမၤဘၣ်လၢ Cheeseteroid အပူၤ. မၤစၢၤယၤ လၢတဆီဘၣ်တဆီ."')

    def test_i18n_url_allowed_in_join_only_site_mode(self):
        """Language switching should work even in join-only site mode."""
        with self.settings(SITE_MODE="join-only"):
            resp = self.client.post(
                "/i18n/setlang/",
                {"language": "es", "next": "/"},
                follow=True,
            )
            self.assertEqual(resp.status_code, 200)

    def test_student_class_page_spanish_renders_translated_core_copy(self):
        self._set_student_session_with_course_link()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Enlaces del curso")

    def test_student_class_page_somali_renders_translated_core_copy(self):
        self._set_student_session_with_course_link()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Xiriirrada koorsada")

    def test_student_class_page_sgaw_karen_renders_translated_core_copy(self):
        self._set_student_session_with_course_link()

        resp = self.client.get("/student", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Course link တဖၣ်")

    def test_course_lesson_page_spanish_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple",
            language="es",
            expected_reading_label="Nivel de lectura:",
            expected_reading_value="Sencillo",
            expected_section_label="Empieza aquí",
        )

    def test_course_lesson_page_somali_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple",
            language="so",
            expected_reading_label="Heerka akhriska:",
            expected_reading_value="Fudud",
            expected_section_label="Halkan ka bilow",
        )

    def test_course_lesson_page_sgaw_karen_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple",
            language="ksw",
            expected_reading_label="တၢ်ဖးအပတီၢ်:",
            expected_reading_value="ဖးလီၤစှၤ",
            expected_section_label="စးထီၣ်ဖဲအံၤ",
        )

    def test_course_lesson_page_sets_html_lang_to_active_language(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple",
                    HTTP_ACCEPT_LANGUAGE="so",
                )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="so">')

    def test_course_lesson_page_query_lang_override_sets_active_language(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple&lang=es",
                    HTTP_ACCEPT_LANGUAGE="en",
                )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="es">')
        self.assertContains(resp, "Nivel de lectura:")

    def test_course_lesson_page_hides_unavailable_handout_languages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple",
                    HTTP_ACCEPT_LANGUAGE="en",
                )

        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Choose a language")
        self.assertNotContains(resp, "/handout?reading_level=simple&amp;lang=es")
        self.assertNotContains(resp, "/handout?reading_level=simple&amp;lang=so")
        self.assertNotContains(resp, "/handout?reading_level=simple&amp;lang=ksw")

    def test_course_lesson_handout_spanish_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple",
            language="es",
            expected_reading_label="Nivel de lectura:",
            expected_reading_value="Sencillo",
            expected_section_label="Empieza aquí",
        )

    def test_course_lesson_handout_somali_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple",
            language="so",
            expected_reading_label="Heerka akhriska:",
            expected_reading_value="Fudud",
            expected_section_label="Halkan ka bilow",
        )

    def test_course_lesson_handout_sgaw_karen_renders_translated_reading_level_label(self):
        self._assert_lesson_route_i18n(
            route="/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple",
            language="ksw",
            expected_reading_label="တၢ်ဖးအပတီၢ်:",
            expected_reading_value="ဖးလီၤစှၤ",
            expected_section_label="စးထီၣ်ဖဲအံၤ",
        )

    def test_sgaw_karen_handout_disables_lossy_pdf_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                lesson = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple&lang=ksw"
                )
                handout = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple&lang=ksw"
                )
                pdf = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout.pdf?reading_level=simple&lang=ksw"
                )

        self.assertEqual(lesson.status_code, 200)
        self.assertEqual(handout.status_code, 200)
        self.assertNotContains(lesson, "/handout.pdf")
        self.assertNotContains(handout, "/handout.pdf")
        self.assertEqual(pdf.status_code, 404)

    def test_course_lesson_handout_sets_html_lang_to_active_language(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple",
                    HTTP_ACCEPT_LANGUAGE="so",
                )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="so">')

    def test_course_lesson_handout_query_lang_override_renders_requested_language(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            self._write_lesson_locale_fixture(content_root)
            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple&lang=es",
                    HTTP_ACCEPT_LANGUAGE="en",
                )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="es">')
        self.assertContains(resp, "Nivel de lectura:")
        self.assertContains(
            resp,
            "/course/neighborhood_circuits/s01-neighborhood-circuits/handout.pdf?reading_level=simple&amp;lang=es",
        )

    def test_teach_home_day_mode_spanish_renders_translated_core_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_day_mode",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach?portal_mode=day", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "¿Qué cambió desde ayer?")

    def test_teach_home_day_mode_somali_renders_translated_core_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_day_mode_so",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach?portal_mode=day", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Maxaa Isbeddelay Ilaa Shalay")

    def test_teach_home_day_mode_sgaw_karen_renders_translated_core_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_day_mode_ksw",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach?portal_mode=day", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "လၢမဟါတနံၤလၢခံ တၢ်လဲၤလိာ်မနုၤတဖၣ်")

    def test_teach_home_uses_active_html_lang(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_home_lang",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="es">')

    def test_teach_lessons_uses_active_html_lang(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_lessons_lang",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach/lessons", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<html lang="so">')

    def test_teach_home_setup_console_spanish_renders_translated_setup_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_setup_es",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Configuración del portal y herramientas de cuenta")
        self.assertContains(resp, "Crear un espacio de clase")

    def test_teach_home_setup_console_somali_renders_translated_setup_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_setup_so",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dejinta portalka iyo qalabka akoonka")
        self.assertContains(resp, "Samee goob fasal")

    def test_teach_home_setup_console_sgaw_karen_renders_translated_setup_copy(self):
        teacher = get_user_model().objects.create_user(
            username="teacher_i18n_setup_ksw",
            password="testpass123",
            is_staff=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "တၢ်တဲာ်တဲာ် portal ဒီး account tool တဖၣ်")
        self.assertContains(resp, "တီၤအတၢ်မၤတၢ်လီၢ် မၤတ့ၢ်")

    def _assert_teach_home_setup_audit_i18n(self, *, language: str, expected_label: str) -> None:
        teacher = get_user_model().objects.create_user(
            username=f"teacher_i18n_audit_{language}",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        _force_login_staff_verified(self.client, teacher)

        resp = self.client.get("/teach?portal_mode=setup&advanced=1", HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, expected_label)

    def test_teach_home_setup_audit_spanish_renders_translated_copy(self):
        self._assert_teach_home_setup_audit_i18n(
            language="es",
            expected_label="Auditoría de importación de contenido",
        )

    def test_teach_home_setup_audit_somali_renders_translated_copy(self):
        self._assert_teach_home_setup_audit_i18n(
            language="so",
            expected_label="Dabagalka gelinta macluumaadka",
        )

    def test_teach_home_setup_audit_sgaw_karen_renders_translated_copy(self):
        self._assert_teach_home_setup_audit_i18n(
            language="ksw",
            expected_label="content/import audit",
        )

    def test_student_my_data_page_spanish_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/my-data", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Privacidad en resumen")
        self.assertContains(resp, "Sin rastreo. Sin anuncios. Sin intercambio con corredores de datos.")

    def test_student_my_data_page_somali_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/my-data", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dulmar Asturnaanta")
        self.assertContains(resp, "Ma jiro raadraac. Ma jiro xayeysiis. Lama wadaago dilaaliinta xogta.")

    def test_student_my_data_page_sgaw_karen_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/my-data", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "တၢ်ခူသူၣ် တၢ်ကွၢ်ဖျါတဘျီ")
        self.assertContains(resp, "tracking တအိၣ်ဘၣ်. ads တအိၣ်ဘၣ်. data broker sharing တအိၣ်ဘၣ်.")

    def test_student_portfolio_page_spanish_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/portfolio", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Filtros")

    def test_student_portfolio_page_somali_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/portfolio", HTTP_ACCEPT_LANGUAGE="so")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Shaandheeyayaal")

    def test_student_portfolio_page_sgaw_karen_renders_translated_core_copy(self):
        self._set_student_session()

        resp = self.client.get("/student/portfolio", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "filter တဖၣ်")

    def test_privacy_page_sgaw_karen_renders_translated_core_copy(self):
        resp = self.client.get("/trust", HTTP_ACCEPT_LANGUAGE="ksw")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "တၢ်လၢပသိမ်းဆည်း / တၢ်လၢပတသိမ်းဆည်းနီတဘျီဘၣ်")

    def _assert_standard_privacy_i18n(
        self,
        *,
        language,
        expected_level,
        expected_data_copy,
        expected_warning_heading,
        expected_warning_copy,
    ):
        resp = self.client.get("/privacy?reading_level=standard", HTTP_ACCEPT_LANGUAGE=language)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, expected_level)
        self.assertContains(resp, expected_data_copy)
        self.assertContains(resp, expected_warning_heading)
        self.assertContains(resp, expected_warning_copy)
        self.assertNotContains(resp, "No Accounts:")

    def test_privacy_page_retains_sensitive_document_warning(self):
        resp = self.client.get("/privacy?reading_level=standard")

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Don't upload sensitive documents")
        self.assertContains(resp, "medical records")
        self.assertContains(resp, "government IDs")
        self.assertContains(resp, "passwords")
        self.assertContains(resp, "financial information")

    def test_standard_privacy_page_spanish_uses_existing_translated_copy(self):
        self._assert_standard_privacy_i18n(
            language="es",
            expected_level="Nivel de lectura: Estándar",
            expected_data_copy="Guardamos tu nombre para mostrar de la clase para que tu maestro pueda identificar tu trabajo.",
            expected_warning_heading="No subas documentos confidenciales",
            expected_warning_copy="Nunca subas expedientes médicos, identificaciones gubernamentales, contraseñas ni información financiera.",
        )

    def test_standard_privacy_page_somali_uses_existing_translated_copy(self):
        self._assert_standard_privacy_i18n(
            language="so",
            expected_level="Heerka akhriska: Caadi",
            expected_data_copy="Waxaan kaydinnaa magacaaga muuqda ee fasalka si macallinkaagu u garto shaqadaada.",
            expected_warning_heading="Ha soo gelin dukumiintiyo xasaasi ah",
            expected_warning_copy="Waligaa ha soo gelin diiwaanno caafimaad, aqoonsiyo dowladeed, furaha sirta ah, ama macluumaad maaliyadeed.",
        )

    def test_standard_privacy_page_sgaw_karen_uses_existing_translated_copy(self):
        self._assert_standard_privacy_i18n(
            language="ksw",
            expected_level="တၢ်ဖးအပတီၢ်: ပတီၢ်ညီ",
            expected_data_copy="ပသိမ်းဆည်း နတီၤအ display name ဒ်သိး နဆရာ/မ ကသ့ၣ်ညါ နတၢ်မၤ.",
            expected_warning_heading="တ upload sensitive document တဂ့ၤ",
            expected_warning_copy="Never upload medical records, government IDs, passwords, or financial information.",
        )
