from django.test import SimpleTestCase
from ..services.student_join import _looks_like_phone_number

class StudentJoinUtilsTests(SimpleTestCase):
    """Unit tests for student_join utility functions."""

    def test_looks_like_phone_number_happy_path(self):
        cases = [
            ("555-1234", True),
            ("5558675309", True),
            ("(555) 867-5309", True),
            ("555.867.5309", True),
            ("+1 555-867-5309", True),
            ("00 1 555 867 5309", True),
            ("1234567890", True),
            ("123456789012345", True),
            ("555.1234", True),
            ("555(1234)", True),
            ("555+1234", True),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_looks_like_phone_number(value), expected)

    def test_looks_like_phone_number_edge_cases_false(self):
        cases = [
            ("", False),
            (None, False),
            ("123456", False),
            ("1234567890123456", False),
            ("1234567", False),
            ("12345678", False),
            ("123456789", False),
            ("123-456-7890a", False),
            ("123-456-7890!", False),
            ("phone: 1234567", False),
            ("555 1234", False), # Space is allowed but doesn't count as separator in current implementation
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_looks_like_phone_number(value), expected)

    def test_looks_like_phone_number_whitespace_handling(self):
        self.assertTrue(_looks_like_phone_number("  555-867-5309  "))
