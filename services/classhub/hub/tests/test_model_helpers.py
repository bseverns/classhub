from ._shared import *  # noqa: F401,F403

from hub.model_helpers import (
    gen_certificate_code,
    gen_class_code,
    gen_student_invite_token,
    gen_student_return_code,
)


class ModelHelperGeneratorTests(SimpleTestCase):
    def test_class_code_uses_expected_alphabet_and_length(self):
        alphabet = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(20):
            value = gen_class_code()
            self.assertEqual(len(value), 8)
            self.assertTrue(set(value) <= alphabet)

    def test_student_return_code_uses_expected_alphabet_and_length(self):
        alphabet = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(20):
            value = gen_student_return_code()
            self.assertEqual(len(value), 6)
            self.assertTrue(set(value) <= alphabet)

    def test_student_invite_token_uses_expected_alphabet_and_length(self):
        alphabet = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        for _ in range(20):
            value = gen_student_invite_token()
            self.assertEqual(len(value), 24)
            self.assertTrue(set(value) <= alphabet)

    def test_certificate_code_uses_expected_alphabet_and_length(self):
        alphabet = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        for _ in range(20):
            value = gen_certificate_code()
            self.assertEqual(len(value), 12)
            self.assertTrue(set(value) <= alphabet)

