"""Command-line interface for teacher/operator ClassHub actions."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .client import HubClient
from .errors import (
    EXIT_AUTH,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_USAGE,
    EXIT_UNEXPECTED,
    APIError,
    HubctlError,
)

DEFAULT_BASE_URL = os.environ.get("CLASSHUB_BASE_URL", "http://localhost")
DEFAULT_SESSION_FILE = Path(os.environ.get("HUBCTL_SESSION_FILE", "~/.classhub/hubctl.cookies"))
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("HUBCTL_TIMEOUT_SECONDS", "15"))


@dataclass
class CommandResult:
    payload: dict[str, Any]
    save_session: bool = True


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    header_line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    separator_line = "  ".join("-" * widths[i] for i in range(len(headers)))
    row_lines = ["  ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in rows]
    return "\n".join([header_line, separator_line, *row_lines])


def _resolve_class_from_classes_payload(payload: dict[str, Any], class_id: int) -> dict[str, Any]:
    classes = payload.get("classes") or []
    for item in classes:
        if int(item.get("id", -1)) == int(class_id):
            return item
    raise HubctlError(
        f"Class {class_id} is not visible to this account.",
        exit_code=EXIT_NOT_FOUND,
    )


def _read_password_arg(raw_password: str | None) -> str:
    if raw_password:
        return raw_password
    env_password = os.environ.get("HUBCTL_PASSWORD", "")
    if env_password:
        return env_password
    return getpass.getpass("Password: ")


def _auth_login(args: argparse.Namespace, client: HubClient) -> CommandResult:
    password = _read_password_arg(args.password)
    client.login_teacher(username=args.username, password=password)
    otp_verified = False

    try:
        classes_payload = client.teacher_classes()
    except APIError as exc:
        if exc.status_code == 401 and exc.error_code == "otp_required":
            if not args.otp_token:
                raise HubctlError(
                    "2FA is required. Re-run with --otp-token <6-digit code>.",
                    exit_code=EXIT_AUTH,
                ) from exc
            client.verify_teacher_otp(otp_token=args.otp_token)
            classes_payload = client.teacher_classes()
            otp_verified = True
        else:
            raise

    return CommandResult(
        payload={
            "kind": "auth.login",
            "ok": True,
            "class_count": len(classes_payload.get("classes") or []),
            "otp_used": otp_verified,
        }
    )


def _auth_check(_args: argparse.Namespace, client: HubClient) -> CommandResult:
    classes_payload = client.teacher_classes()
    return CommandResult(
        payload={
            "kind": "auth.check",
            "ok": True,
            "class_count": len(classes_payload.get("classes") or []),
        }
    )


def _auth_logout(_args: argparse.Namespace, client: HubClient) -> CommandResult:
    try:
        client.logout_teacher()
    except APIError:
        # Local logout should still clear local cookies even if server session already expired.
        pass
    client.clear_local_session()
    return CommandResult(
        payload={"kind": "auth.logout", "ok": True},
        save_session=False,
    )


def _classes_list(_args: argparse.Namespace, client: HubClient) -> CommandResult:
    payload = client.teacher_classes()
    payload["kind"] = "classes.list"
    return CommandResult(payload=payload)


def _class_lock_state(class_id: int, desired_locked: bool, client: HubClient) -> dict[str, Any]:
    classes_payload = client.teacher_classes()
    target = _resolve_class_from_classes_payload(classes_payload, class_id)
    is_locked = bool(target.get("is_locked"))
    if is_locked == desired_locked:
        return {
            "kind": "class.lock-state",
            "classroom_id": class_id,
            "is_locked": is_locked,
            "changed": False,
        }
    response = client.teacher_toggle_lock(class_id)
    response["kind"] = "class.lock-state"
    response["changed"] = True
    return response


def _class_lock(args: argparse.Namespace, client: HubClient) -> CommandResult:
    return CommandResult(payload=_class_lock_state(args.class_id, True, client))


def _class_unlock(args: argparse.Namespace, client: HubClient) -> CommandResult:
    return CommandResult(payload=_class_lock_state(args.class_id, False, client))


def _class_rotate_code(args: argparse.Namespace, client: HubClient) -> CommandResult:
    payload = client.teacher_rotate_code(args.class_id)
    payload["kind"] = "class.rotate-code"
    return CommandResult(payload=payload)


def _class_set_enrollment(args: argparse.Namespace, client: HubClient) -> CommandResult:
    payload = client.teacher_set_enrollment_mode(args.class_id, args.enrollment_mode)
    payload["kind"] = "class.set-enrollment"
    return CommandResult(payload=payload)


def _class_roster(args: argparse.Namespace, client: HubClient) -> CommandResult:
    payload = client.teacher_class_roster(args.class_id)
    payload["kind"] = "class.roster"
    return CommandResult(payload=payload)


def _class_submissions(args: argparse.Namespace, client: HubClient) -> CommandResult:
    payload = client.teacher_class_submissions(args.class_id, limit=args.limit, offset=args.offset)
    payload["kind"] = "class.submissions"
    return CommandResult(payload=payload)


def _print_human(payload: dict[str, Any]) -> None:
    kind = payload.get("kind")

    if kind == "auth.login":
        otp_note = " (2FA verified)" if payload.get("otp_used") else ""
        print(f"Session established{otp_note}. Accessible classes: {payload.get('class_count', 0)}")
        return

    if kind == "auth.check":
        print(f"Session is valid. Accessible classes: {payload.get('class_count', 0)}")
        return

    if kind == "auth.logout":
        print("Session cleared.")
        return

    if kind == "classes.list":
        classes = payload.get("classes") or []
        if not classes:
            print("No classes are visible to this account.")
            return
        rows: list[list[str]] = []
        for cls in classes:
            rows.append(
                [
                    str(cls.get("id", "")),
                    str(cls.get("name", "")),
                    "yes" if cls.get("is_assigned") else "no",
                    "locked" if cls.get("is_locked") else "open",
                    str(cls.get("enrollment_mode", "")),
                    str(cls.get("student_count", 0)),
                    str(cls.get("submissions_24h", 0)),
                    str(cls.get("join_code", "")),
                ]
            )
        print(
            _format_table(
                ["id", "name", "assigned", "lock", "enrollment", "students", "sub24h", "join_code"],
                rows,
            )
        )
        return

    if kind == "class.lock-state":
        changed = "changed" if payload.get("changed") else "unchanged"
        state = "locked" if payload.get("is_locked") else "unlocked"
        print(f"Class {payload.get('classroom_id')}: {state} ({changed}).")
        return

    if kind == "class.rotate-code":
        print(f"Class {payload.get('classroom_id')} new join code: {payload.get('join_code')}")
        return

    if kind == "class.set-enrollment":
        print(
            "Class "
            f"{payload.get('classroom_id')} enrollment mode set to {payload.get('enrollment_mode')}"
        )
        return

    if kind == "class.roster":
        classroom = payload.get("classroom") or {}
        print(
            f"Class {classroom.get('id')}: {classroom.get('name')}\n"
            f"Join code: {classroom.get('join_code')}\n"
            f"Lock: {'locked' if classroom.get('is_locked') else 'open'}\n"
            f"Enrollment: {classroom.get('enrollment_mode')}\n"
            f"Students: {payload.get('student_count', 0)}"
        )
        students = payload.get("students") or []
        if students:
            rows = [
                [
                    str(student.get("id", "")),
                    str(student.get("display_name", "")),
                    str(student.get("submission_count", 0)),
                    str(student.get("last_seen_at", "")),
                ]
                for student in students
            ]
            print("\nStudents")
            print(_format_table(["id", "name", "submissions", "last_seen"], rows))
        return

    if kind == "class.submissions":
        submissions = payload.get("submissions") or []
        pagination = payload.get("pagination") or {}
        print(
            "Submissions: "
            f"{len(submissions)} of total {pagination.get('total', 0)} "
            f"(limit={pagination.get('limit')}, offset={pagination.get('offset')})"
        )
        if submissions:
            rows = [
                [
                    str(item.get("id", "")),
                    str((item.get("student") or {}).get("display_name", "")),
                    str((item.get("material") or {}).get("title", "")),
                    str(item.get("original_filename", "")),
                    str(item.get("uploaded_at", "")),
                ]
                for item in submissions
            ]
            print(_format_table(["id", "student", "material", "filename", "uploaded_at"], rows))
        return

    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_error(message: str, *, as_json: bool, exit_code: int, status_code: int | None = None) -> None:
    if as_json:
        payload: dict[str, Any] = {
            "ok": False,
            "error": message,
            "exit_code": exit_code,
        }
        if status_code is not None:
            payload["status_code"] = status_code
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return
    print(f"ERROR: {message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ClassHub facilitator CLI (hubctl)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ClassHub base URL (default: %(default)s)")
    parser.add_argument(
        "--session-file",
        type=Path,
        default=DEFAULT_SESSION_FILE,
        help="Cookie session file path (default: ~/.classhub/hubctl.cookies)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit JSON output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_parser = subparsers.add_parser("auth", help="Session bootstrap and lifecycle commands")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", required=True)

    auth_login = auth_subparsers.add_parser("login", help="Create a teacher/admin session")
    auth_login.add_argument("--username", required=True, help="Staff username")
    auth_login.add_argument("--password", help="Staff password (or set HUBCTL_PASSWORD)")
    auth_login.add_argument("--otp-token", help="TOTP code if 2FA is required")
    auth_login.set_defaults(handler=_auth_login)

    auth_check = auth_subparsers.add_parser("check", help="Verify current session by calling teacher API")
    auth_check.set_defaults(handler=_auth_check)

    auth_logout = auth_subparsers.add_parser("logout", help="Clear server and local session state")
    auth_logout.set_defaults(handler=_auth_logout)

    classes_parser = subparsers.add_parser("classes", help="Class collection operations")
    classes_subparsers = classes_parser.add_subparsers(dest="classes_command", required=True)

    classes_list = classes_subparsers.add_parser("list", help="List classes visible to this account")
    classes_list.set_defaults(handler=_classes_list)

    class_parser = subparsers.add_parser("class", help="Single-class operations")
    class_subparsers = class_parser.add_subparsers(dest="class_command", required=True)

    class_lock = class_subparsers.add_parser("lock", help="Lock class join access")
    class_lock.add_argument("class_id", type=int)
    class_lock.set_defaults(handler=_class_lock)

    class_unlock = class_subparsers.add_parser("unlock", help="Unlock class join access")
    class_unlock.add_argument("class_id", type=int)
    class_unlock.set_defaults(handler=_class_unlock)

    class_rotate = class_subparsers.add_parser("rotate-code", help="Rotate class join code")
    class_rotate.add_argument("class_id", type=int)
    class_rotate.set_defaults(handler=_class_rotate_code)

    class_set_enrollment = class_subparsers.add_parser("set-enrollment", help="Set enrollment mode")
    class_set_enrollment.add_argument("class_id", type=int)
    class_set_enrollment.add_argument("enrollment_mode", choices=["open", "invite_only", "closed"])
    class_set_enrollment.set_defaults(handler=_class_set_enrollment)

    class_roster = class_subparsers.add_parser("roster", help="Show class roster and module summary")
    class_roster.add_argument("class_id", type=int)
    class_roster.set_defaults(handler=_class_roster)

    class_submissions = class_subparsers.add_parser("submissions", help="List class submissions")
    class_submissions.add_argument("class_id", type=int)
    class_submissions.add_argument("--limit", type=int, default=50)
    class_submissions.add_argument("--offset", type=int, default=0)
    class_submissions.set_defaults(handler=_class_submissions)

    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if hasattr(args, "limit") and args.limit is not None and args.limit < 1:
        raise HubctlError("--limit must be >= 1", exit_code=EXIT_USAGE)
    if hasattr(args, "offset") and args.offset is not None and args.offset < 0:
        raise HubctlError("--offset must be >= 0", exit_code=EXIT_USAGE)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        _validate_args(args)
        client = HubClient(
            base_url=args.base_url,
            session_file=args.session_file,
            timeout_seconds=args.timeout,
        )
        result: CommandResult = args.handler(args, client)
        if result.save_session:
            client.save_session()

        if args.json_output:
            print(json.dumps(result.payload, indent=2, sort_keys=True))
        else:
            _print_human(result.payload)
        return EXIT_OK
    except APIError as exc:
        _print_error(
            exc.message,
            as_json=bool(getattr(args, "json_output", False)),
            exit_code=exc.exit_code,
            status_code=exc.status_code,
        )
        return exc.exit_code
    except HubctlError as exc:
        _print_error(
            exc.message,
            as_json=bool(getattr(args, "json_output", False)),
            exit_code=exc.exit_code,
        )
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive catch-all
        _print_error(
            f"Unexpected error: {exc}",
            as_json=bool(getattr(args, "json_output", False)),
            exit_code=EXIT_UNEXPECTED,
        )
        return EXIT_UNEXPECTED
