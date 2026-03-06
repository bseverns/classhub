"""Unit tests for hubctl CLI argument parsing and error contracts."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from hubctl.cli import main
from hubctl.errors import EXIT_AUTH, EXIT_OK, EXIT_USAGE, APIError


class _FakeClient:
    def __init__(self, **_kwargs):
        self._teacher_classes_responses = []

    def save_session(self):
        return None

    def clear_local_session(self):
        return None

    def login_teacher(self, *, username: str, password: str):
        _ = (username, password)

    def verify_teacher_otp(self, *, otp_token: str):
        _ = otp_token

    def logout_teacher(self):
        return None

    def teacher_classes(self):
        if self._teacher_classes_responses:
            value = self._teacher_classes_responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return {"classes": []}

    def teacher_class_roster(self, class_id: int):
        return {"classroom": {"id": class_id, "name": "Demo"}, "students": [], "student_count": 0}

    def teacher_class_submissions(self, class_id: int, *, limit: int, offset: int):
        return {
            "submissions": [],
            "pagination": {"total": 0, "limit": limit, "offset": offset},
            "classroom_id": class_id,
        }

    def teacher_toggle_lock(self, class_id: int):
        return {"classroom_id": class_id, "is_locked": True}

    def teacher_rotate_code(self, class_id: int):
        return {"classroom_id": class_id, "join_code": "NEWCODE1"}

    def teacher_set_enrollment_mode(self, class_id: int, enrollment_mode: str):
        return {"classroom_id": class_id, "enrollment_mode": enrollment_mode}


class HubctlCliTests(unittest.TestCase):
    def _run(self, argv: list[str], fake_client: _FakeClient | None = None):
        if fake_client is None:
            fake_client = _FakeClient()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = str(Path(tmpdir) / "hubctl.cookies")
            full_argv = ["--session-file", session_file, *argv]
            with patch("hubctl.cli.HubClient", return_value=fake_client):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = main(full_argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_classes_list_human_output(self):
        fake = _FakeClient()
        fake._teacher_classes_responses = [
            {
                "classes": [
                    {
                        "id": 7,
                        "name": "Robotics",
                        "join_code": "ABC12345",
                        "is_locked": False,
                        "enrollment_mode": "open",
                        "student_count": 12,
                        "submissions_24h": 4,
                        "is_assigned": True,
                    }
                ]
            }
        ]
        code, out, err = self._run(["classes", "list"], fake)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Robotics", out)
        self.assertEqual(err, "")

    def test_invalid_enrollment_mode_fails_parser(self):
        with redirect_stderr(io.StringIO()):
            code = main(["class", "set-enrollment", "1", "invalid-mode"])
        self.assertEqual(code, EXIT_USAGE)

    def test_teacher_api_401_maps_to_auth_exit(self):
        fake = _FakeClient()
        fake._teacher_classes_responses = [
            APIError(
                message="unauthorized",
                exit_code=EXIT_AUTH,
                status_code=401,
                error_code="unauthorized",
                payload={"error": "unauthorized"},
            )
        ]
        code, _out, err = self._run(["classes", "list"], fake)
        self.assertEqual(code, EXIT_AUTH)
        self.assertIn("ERROR", err)

    def test_auth_login_requires_otp_token_when_server_requests_it(self):
        fake = _FakeClient()
        fake._teacher_classes_responses = [
            APIError(
                message="otp required",
                exit_code=EXIT_AUTH,
                status_code=401,
                error_code="otp_required",
                payload={"error": "otp_required"},
            )
        ]
        code, _out, err = self._run([
            "auth",
            "login",
            "--username",
            "teacher1",
            "--password",
            "secret",
        ], fake)
        self.assertEqual(code, EXIT_AUTH)
        self.assertIn("--otp-token", err)

    def test_auth_login_with_otp_can_complete(self):
        fake = _FakeClient()
        fake._teacher_classes_responses = [
            APIError(
                message="otp required",
                exit_code=EXIT_AUTH,
                status_code=401,
                error_code="otp_required",
                payload={"error": "otp_required"},
            ),
            {"classes": [{"id": 1}]},
        ]
        code, out, err = self._run([
            "auth",
            "login",
            "--username",
            "teacher1",
            "--password",
            "secret",
            "--otp-token",
            "123456",
        ], fake)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Session established", out)
        self.assertEqual(err, "")

    def test_submissions_negative_offset_rejected(self):
        fake = _FakeClient()
        code, _out, err = self._run([
            "class",
            "submissions",
            "12",
            "--offset",
            "-1",
        ], fake)
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("offset", err.lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
