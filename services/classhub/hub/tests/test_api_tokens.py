"""Tests for the API token utility and bearer token middleware resolution."""

from ._shared import *  # noqa: F401,F403


class IssueAndVerifyTokenTests(TestCase):
    """Unit tests for hub.services.api_tokens."""

    def setUp(self):
        from ..services.api_tokens import issue_student_token, verify_student_token
        self.issue = issue_student_token
        self.verify = verify_student_token

    def test_round_trip(self):
        token = self.issue(student_id=1, class_id=2, epoch=3)
        payload = self.verify(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sid"], 1)
        self.assertEqual(payload["cid"], 2)
        self.assertEqual(payload["epoch"], 3)

    def test_tampered_token_is_rejected(self):
        token = self.issue(student_id=1, class_id=2, epoch=1)
        self.assertIsNone(self.verify(token + "TAMPERED"))

    def test_completely_invalid_token_is_rejected(self):
        self.assertIsNone(self.verify("not-a-real-token"))

    def test_empty_string_is_rejected(self):
        self.assertIsNone(self.verify(""))

    def test_different_epoch_still_verifies(self):
        """Token signature is valid regardless of epoch — epoch check is in middleware."""
        token = self.issue(student_id=1, class_id=2, epoch=1)
        payload = self.verify(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["epoch"], 1)


class BearerTokenMiddlewareTests(TestCase):
    """Integration tests for bearer token resolution in StudentSessionMiddleware."""

    def setUp(self):
        self.classroom = Class.objects.create(
            name="Bearer Test Class", join_code="BRR12345", session_epoch=1,
        )
        self.student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ada",
        )
        self.module = Module.objects.create(
            classroom=self.classroom, title="Session 1", order_index=0,
        )
        self.material = Material.objects.create(
            module=self.module, title="Upload task", type=Material.TYPE_UPLOAD,
            accepted_extensions=".sb3", max_upload_mb=50, order_index=0,
        )
        from ..services.api_tokens import issue_student_token
        self.token = issue_student_token(
            student_id=self.student.id,
            class_id=self.classroom.id,
            epoch=1,
        )

    def test_bearer_token_authenticates_on_api_path(self):
        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["student"]["display_name"], "Ada")

    def test_missing_bearer_header_returns_401(self):
        resp = self.client.get("/api/v1/student/session")
        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_returns_401_with_invalid_token_error(self):
        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION="Bearer garbage-token",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "invalid_token")

    def test_tampered_token_returns_401_with_invalid_token_error(self):
        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {self.token}TAMPERED",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "invalid_token")

    def test_epoch_mismatch_rejects_token_fail_closed(self):
        """When teacher resets roster (bumps epoch), old tokens should fail-closed."""
        self.classroom.session_epoch = 2
        self.classroom.save(update_fields=["session_epoch"])
        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "invalid_token")

    def test_deleted_student_rejects_token_fail_closed(self):
        self.student.delete()
        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "invalid_token")

    def test_session_auth_still_works_on_api_paths(self):
        session = self.client.session
        session["student_id"] = self.student.id
        session["class_id"] = self.classroom.id
        session["class_epoch"] = 1
        session.save()
        resp = self.client.get("/api/v1/student/session")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["student"]["display_name"], "Ada")

    def test_bearer_takes_priority_over_session(self):
        """If both bearer and session are present, bearer is used (since it's checked first)."""
        # Set up a different student in the session
        other_student = StudentIdentity.objects.create(
            classroom=self.classroom, display_name="Ben",
        )
        session = self.client.session
        session["student_id"] = other_student.id
        session["class_id"] = self.classroom.id
        session["class_epoch"] = 1
        session.save()

        resp = self.client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Bearer token is for Ada, session is for Ben — Ada should win.
        self.assertEqual(data["student"]["display_name"], "Ada")


class JoinResponseIncludesTokenTests(TestCase):
    """Verify that POST /join returns an api_token field."""

    def setUp(self):
        self.classroom = Class.objects.create(
            name="Join Token Class", join_code="JTK12345",
        )

    def test_join_response_contains_api_token(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": "JTK12345", "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("api_token", data)
        self.assertTrue(len(data["api_token"]) > 20)

    def test_join_token_can_authenticate(self):
        resp = self.client.post(
            "/join",
            data=json.dumps({"class_code": "JTK12345", "display_name": "Ada"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["api_token"]

        # Use the token to hit the API (with a fresh client to avoid session)
        fresh_client = Client()
        api_resp = fresh_client.get(
            "/api/v1/student/session",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(api_resp.status_code, 200)
        self.assertEqual(api_resp.json()["student"]["display_name"], "Ada")
