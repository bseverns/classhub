from ._shared import *  # noqa: F401,F403


class PseudonymGeneratorTests(SimpleTestCase):
    """Unit tests for common.pseudonyms.generate_pseudonym."""

    def test_format_matches_adjective_noun_number(self):
        from common.pseudonyms import generate_pseudonym

        for _ in range(20):
            name = generate_pseudonym()
            parts = name.split()
            self.assertEqual(len(parts), 3, f"Expected 3 parts, got {parts}")
            self.assertTrue(parts[0][0].isupper(), f"Adjective not title-cased: {parts[0]}")
            self.assertTrue(parts[1][0].isupper(), f"Noun not title-cased: {parts[1]}")
            self.assertTrue(parts[2].isdigit(), f"Number part not digits: {parts[2]}")
            self.assertEqual(len(parts[2]), 2, f"Number should be 2 digits: {parts[2]}")

    def test_length_bounds(self):
        from common.pseudonyms import generate_pseudonym

        for _ in range(50):
            name = generate_pseudonym()
            self.assertGreaterEqual(len(name), 3)
            self.assertLessEqual(len(name), 32)

    def test_ascii_safe(self):
        from common.pseudonyms import generate_pseudonym

        for _ in range(50):
            name = generate_pseudonym()
            self.assertTrue(name.isascii(), f"Non-ASCII character in: {name}")

    def test_no_denylist_terms(self):
        from common.pseudonyms import DENYLIST, generate_pseudonym

        for _ in range(500):
            name = generate_pseudonym()
            lower = name.lower()
            for term in DENYLIST:
                self.assertNotIn(term, lower, f"Denylist term '{term}' found in: {name}")

    def test_deterministic_with_seeded_rng(self):
        import random

        from common.pseudonyms import generate_pseudonym

        rng = random.Random(42)
        names = [generate_pseudonym(_rng=rng) for _ in range(5)]
        rng2 = random.Random(42)
        names2 = [generate_pseudonym(_rng=rng2) for _ in range(5)]
        self.assertEqual(names, names2)


class NameSafetyValidationTests(SimpleTestCase):
    """Unit tests for validate_display_name_safety."""

    def test_email_detected(self):
        from ..services.student_join import validate_display_name_safety

        flagged, reason = validate_display_name_safety("user@example.com")
        self.assertTrue(flagged)
        self.assertEqual(reason, "email_pattern")

    def test_email_with_subdomain_detected(self):
        from ..services.student_join import validate_display_name_safety

        flagged, reason = validate_display_name_safety("kid@school.edu.au")
        self.assertTrue(flagged)
        self.assertEqual(reason, "email_pattern")

    def test_phone_detected(self):
        from ..services.student_join import validate_display_name_safety

        cases = ["555-867-5309", "(612) 555-1234", "6125551234", "555 867 5309"]
        for phone in cases:
            with self.subTest(phone=phone):
                flagged, reason = validate_display_name_safety(phone)
                self.assertTrue(flagged, f"Phone not detected: {phone}")
                self.assertEqual(reason, "phone_pattern")

    def test_normal_name_passes(self):
        from ..services.student_join import validate_display_name_safety

        safe_names = [
            "Curious Otter 17",
            "Ada",
            "Cool Kid",
            "student_42",
            "X",
            "Dr Pixel",
        ]
        for name in safe_names:
            with self.subTest(name=name):
                flagged, reason = validate_display_name_safety(name)
                self.assertFalse(flagged, f"False positive on: {name}")
                self.assertEqual(reason, "")

    def test_short_number_not_flagged(self):
        from ..services.student_join import validate_display_name_safety

        # Short digit sequences (e.g. "Player 42") should NOT be flagged as phone
        flagged, _ = validate_display_name_safety("Player 42")
        self.assertFalse(flagged)


class PseudonymAndNameSafetyViewTests(TestCase):
    """Integration tests for pseudonym prefill and name-safety in the join flow."""

    def setUp(self):
        self.classroom = Class.objects.create(name="Pseudonym Test", join_code="PSE12345")

    def test_join_page_prefills_pseudonym(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("default_display_name", resp.context)
        pseudonym = resp.context["default_display_name"]
        self.assertTrue(len(pseudonym) >= 3)
        # Pseudonym should be prefilled in the input value
        self.assertContains(resp, f'value="{pseudonym}"')

    @override_settings(NAME_PSEUDONYM_DEFAULT=False)
    def test_join_page_no_prefill_when_disabled(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context.get("default_display_name"), "")

    @override_settings(NAME_SAFETY_MODE="warn")
    def test_join_email_warn_mode_allows_but_warns(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "kid@school.com"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("name_warning", data)
        self.assertIn("email", data["name_warning"].lower())

    @override_settings(NAME_SAFETY_MODE="strict")
    def test_join_email_strict_mode_rejects(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "kid@school.com"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get("error"), "name_rejected")
        self.assertIn("email", data.get("message", "").lower())
        # Should NOT have created a student
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    @override_settings(NAME_SAFETY_MODE="warn")
    def test_join_phone_warn_mode_allows_but_warns(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "555-867-5309"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("name_warning", data)
        self.assertIn("phone", data["name_warning"].lower())

    @override_settings(NAME_SAFETY_MODE="strict")
    def test_join_phone_strict_mode_rejects(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "555-867-5309"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data.get("error"), "name_rejected")
        self.assertEqual(StudentIdentity.objects.filter(classroom=self.classroom).count(), 0)

    @override_settings(NAME_SAFETY_MODE="strict")
    def test_join_normal_name_in_strict_mode_succeeds(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        self.assertNotIn("name_warning", resp.json())

    @override_settings(NAME_SAFETY_MODE="off")
    def test_join_safety_off_allows_email(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": self.classroom.join_code, "display_name": "kid@school.com"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        self.assertNotIn("name_warning", resp.json())

    def test_join_page_shows_help_text(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "nickname or made-up name is fine")

    def test_join_page_label_says_display_name(self):
        resp = self.client.get("/")
        self.assertContains(resp, "Your display name")
