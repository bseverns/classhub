"""Error contracts and exit codes for the hubctl CLI."""

from __future__ import annotations

from dataclasses import dataclass

EXIT_OK = 0
EXIT_UNEXPECTED = 1
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_FORBIDDEN = 4
EXIT_NOT_FOUND = 5
EXIT_RATE_LIMITED = 6
EXIT_NETWORK = 7


@dataclass
class HubctlError(Exception):
    """User-facing CLI error with an explicit process exit code."""

    message: str
    exit_code: int = EXIT_UNEXPECTED

    def __str__(self) -> str:
        return self.message


@dataclass
class APIError(HubctlError):
    """Structured error returned from a ClassHub API endpoint."""

    status_code: int = 0
    error_code: str = ""
    payload: dict | None = None

    def __post_init__(self) -> None:
        if not self.exit_code:
            self.exit_code = exit_code_for_status(self.status_code)


def exit_code_for_status(status_code: int) -> int:
    """Map HTTP status classes to stable automation-friendly exit codes."""
    if status_code in (400, 405):
        return EXIT_USAGE
    if status_code == 401:
        return EXIT_AUTH
    if status_code == 403:
        return EXIT_FORBIDDEN
    if status_code == 404:
        return EXIT_NOT_FOUND
    if status_code == 429:
        return EXIT_RATE_LIMITED
    if status_code >= 500:
        return EXIT_NETWORK
    return EXIT_UNEXPECTED


def api_error_from_response(status_code: int, payload: dict | None) -> APIError:
    """Build a consistent APIError from a JSON error payload."""
    payload = payload or {}
    error_code = str(payload.get("error") or "")
    message = str(payload.get("message") or error_code or f"request failed ({status_code})")

    # Teacher endpoints explicitly use otp_required for unverified staff sessions.
    if status_code == 401 and error_code == "otp_required":
        message = "2FA verification is required for this staff session."

    return APIError(
        message=message,
        exit_code=exit_code_for_status(status_code),
        status_code=status_code,
        error_code=error_code,
        payload=payload,
    )
