from types import SimpleNamespace

from django.core import signing

from common.csp import normalize_csp_mode, resolve_csp_headers
from common.helper_scope import (
    SCOPE_TOKEN_SALT,
    issue_scope_token,
    parse_scope_token,
)
from hub.models import Class
from hub.services.retention_policy import class_event_retention_days, class_submission_retention_days

from ._shared import *  # noqa: F401,F403


class CommonCspTests(SimpleTestCase):
    def test_normalize_csp_mode_accepts_aliases(self):
        self.assertEqual(normalize_csp_mode(" report_only "), "report-only")
        self.assertEqual(normalize_csp_mode("reportonly"), "report-only")

    def test_normalize_csp_mode_rejects_invalid_values(self):
        with self.assertRaisesMessage(ValueError, "invalid CSP mode"):
            normalize_csp_mode("invalid")

    def test_resolve_csp_headers_applies_mode_defaults_and_explicit_overrides(self):
        enforced, report_only = resolve_csp_headers(
            mode="relaxed",
            relaxed_policy="default-src 'self'",
            strict_policy="default-src 'none'",
            explicit_report_only_policy="report-uri /csp",
        )
        self.assertEqual(enforced, "default-src 'self'")
        self.assertEqual(report_only, "report-uri /csp")

        enforced, report_only = resolve_csp_headers(
            mode="strict",
            relaxed_policy="default-src 'self'",
            strict_policy="default-src 'none'",
            explicit_policy="default-src https:",
        )
        self.assertEqual(enforced, "default-src https:")
        self.assertEqual(report_only, "")


class HelperScopeTokenTests(SimpleTestCase):
    def test_issue_and_parse_scope_token_roundtrip_normalizes_fields(self):
        token = issue_scope_token(
            context="  lesson-1  ",
            topics=" algebra | geometry | ",
            allowed_topics=[" equations ", "", "graphs"],
            reference="  ref-123  ",
            signing_key="scope-key",
        )

        parsed = parse_scope_token(token, max_age_seconds=60, signing_key="scope-key")

        self.assertEqual(
            parsed,
            {
                "context": "lesson-1",
                "topics": ["algebra", "geometry"],
                "allowed_topics": ["equations", "graphs"],
                "reference": "ref-123",
            },
        )

    def test_parse_scope_token_rejects_unsupported_version(self):
        token = signing.dumps({"v": 99}, salt=SCOPE_TOKEN_SALT, key="scope-key")

        with self.assertRaisesMessage(ValueError, "unsupported_scope_version"):
            parse_scope_token(token, max_age_seconds=60, signing_key="scope-key")

    def test_parse_scope_token_rejects_non_dict_payload(self):
        token = signing.dumps("bad-payload", salt=SCOPE_TOKEN_SALT, key="scope-key")

        with self.assertRaisesMessage(ValueError, "invalid_scope_payload"):
            parse_scope_token(token, max_age_seconds=60, signing_key="scope-key")


class RetentionPolicyTests(SimpleTestCase):
    @override_settings(
        CLASSHUB_SUBMISSION_RETENTION_DAYS="45",
        CLASSHUB_STUDENT_EVENT_RETENTION_DAYS="120",
    )
    def test_none_classroom_uses_configured_fallbacks(self):
        self.assertEqual(class_submission_retention_days(classroom=None), 45)
        self.assertEqual(class_event_retention_days(classroom=None), 120)

    def test_none_classroom_explicit_fallback_days_are_clamped_non_negative(self):
        self.assertEqual(class_submission_retention_days(classroom=None, fallback_days=-3), 0)
        self.assertEqual(class_event_retention_days(classroom=None, fallback_days=-7), 0)

    @override_settings(
        CLASSHUB_SUBMISSION_RETENTION_DAYS=90,
        CLASSHUB_STUDENT_EVENT_RETENTION_DAYS=180,
    )
    def test_classroom_presets_map_to_expected_retention_days(self):
        cases = [
            (Class.RETENTION_ERASE_7_DAYS, 7, 7),
            (Class.RETENTION_KEEP_SEMESTER, 180, 180),
            (Class.RETENTION_KEEP_UNTIL_STUDENT_DELETES, 0, 0),
            ("unknown", 90, 180),
        ]

        for preset, submission_days, event_days in cases:
            classroom = SimpleNamespace(retention_preset=preset)
            with self.subTest(preset=preset):
                self.assertEqual(class_submission_retention_days(classroom=classroom), submission_days)
                self.assertEqual(class_event_retention_days(classroom=classroom), event_days)
