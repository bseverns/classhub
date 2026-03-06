"""HTTP session client for the ClassHub teacher API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Any

from .errors import (
    EXIT_AUTH,
    EXIT_NETWORK,
    EXIT_USAGE,
    APIError,
    HubctlError,
    api_error_from_response,
)


@dataclass
class RawResponse:
    """Normalized HTTP response payload for non-JSON endpoints."""

    status_code: int
    url: str
    headers: dict[str, str]
    body: bytes


class HubClient:
    """Cookie-backed session client for teacher-authenticated API calls."""

    def __init__(self, *, base_url: str, session_file: Path, timeout_seconds: float = 15.0) -> None:
        parsed = urllib.parse.urlsplit(base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HubctlError(
                "--base-url must include scheme and host, for example http://localhost",
                exit_code=EXIT_USAGE,
            )
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.host = parsed.hostname or ""
        self.session_file = session_file.expanduser()
        self.timeout_seconds = timeout_seconds
        self.cookie_jar = LWPCookieJar(str(self.session_file))
        self._load_cookies()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def _load_cookies(self) -> None:
        if not self.session_file.exists():
            return
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except OSError:
            # Corrupt or unreadable cookie files should not hard-fail command parsing.
            self.cookie_jar.clear()

    def save_session(self) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.cookie_jar.save(ignore_discard=True, ignore_expires=True)

    def clear_local_session(self) -> None:
        self.cookie_jar.clear()
        if self.session_file.exists():
            self.session_file.unlink()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def _cookie_matches_host(self, cookie_domain: str) -> bool:
        domain = (cookie_domain or "").lstrip(".")
        if not domain or not self.host:
            return False
        return self.host == domain or self.host.endswith("." + domain)

    def csrf_token(self) -> str:
        token = ""
        for cookie in self.cookie_jar:
            if cookie.name == "csrftoken" and self._cookie_matches_host(cookie.domain):
                token = cookie.value
        return token

    def _parse_json_bytes(self, raw: bytes) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HubctlError("Server returned non-JSON response where JSON was expected.")

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
        add_csrf: bool = False,
    ) -> RawResponse:
        request_headers = dict(headers or {})
        request_headers.setdefault("User-Agent", "hubctl/0.1")
        request_headers.setdefault("Accept", "application/json")

        encoded_query = ""
        if query:
            encoded_query = urllib.parse.urlencode(query)
        target_path = path if path.startswith("/") else "/" + path
        if encoded_query:
            target_path = f"{target_path}?{encoded_query}"
        url = self._url(target_path)

        data: bytes | None = None
        if json_body is not None and form_body is not None:
            raise HubctlError("Cannot send both JSON and form body in the same request.")

        if add_csrf:
            token = self.csrf_token()
            if not token:
                raise HubctlError(
                    "Session is missing CSRF state. Run `hubctl auth login` first.",
                    exit_code=EXIT_AUTH,
                )
            request_headers.setdefault("X-CSRFToken", token)
            request_headers.setdefault("Referer", self._url("/teach"))
            if form_body is not None and "csrfmiddlewaretoken" not in form_body:
                form_body = dict(form_body)
                form_body["csrfmiddlewaretoken"] = token

        if json_body is not None:
            request_headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")
        elif form_body is not None:
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urllib.parse.urlencode(form_body).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                body = response.read()
                return RawResponse(
                    status_code=int(getattr(response, "status", 200)),
                    url=response.geturl(),
                    headers=dict(response.headers.items()),
                    body=body,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            payload: dict[str, Any] | None = None
            try:
                parsed = self._parse_json_bytes(body)
                if isinstance(parsed, dict):
                    payload = parsed
            except HubctlError:
                payload = None
            raise api_error_from_response(int(exc.code), payload) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise HubctlError(f"Network error while contacting {self.base_url}: {reason}", exit_code=EXIT_NETWORK) from exc

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        add_csrf: bool = False,
    ) -> dict[str, Any]:
        response = self._request_raw(
            method,
            path,
            query=query,
            json_body=json_body,
            add_csrf=add_csrf,
        )
        payload = self._parse_json_bytes(response.body)
        if not isinstance(payload, dict):
            raise HubctlError("Server returned unexpected JSON payload shape.")
        return payload

    def request_form(self, method: str, path: str, *, form_body: dict[str, Any], add_csrf: bool) -> RawResponse:
        return self._request_raw(
            method,
            path,
            form_body=form_body,
            add_csrf=add_csrf,
            headers={"Accept": "text/html,application/xhtml+xml"},
        )

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def login_teacher(self, *, username: str, password: str) -> None:
        self._request_raw("GET", "/teach/login", headers={"Accept": "text/html,application/xhtml+xml"})
        self.request_form(
            "POST",
            "/teach/login",
            form_body={"username": username, "password": password, "next": "/teach"},
            add_csrf=True,
        )

    def verify_teacher_otp(self, *, otp_token: str) -> None:
        self._request_raw("GET", "/teach/2fa/setup", headers={"Accept": "text/html,application/xhtml+xml"})
        self.request_form(
            "POST",
            "/teach/2fa/setup",
            form_body={"otp_token": otp_token, "next": "/teach"},
            add_csrf=True,
        )

    def logout_teacher(self) -> None:
        self._request_raw("GET", "/teach/logout", headers={"Accept": "text/html,application/xhtml+xml"})

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    def teacher_classes(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/v1/teacher/classes")

    def teacher_class_roster(self, class_id: int) -> dict[str, Any]:
        return self.request_json("GET", f"/api/v1/teacher/class/{class_id}/roster")

    def teacher_class_submissions(self, class_id: int, *, limit: int, offset: int) -> dict[str, Any]:
        return self.request_json(
            "GET",
            f"/api/v1/teacher/class/{class_id}/submissions",
            query={"limit": int(limit), "offset": int(offset)},
        )

    def teacher_toggle_lock(self, class_id: int) -> dict[str, Any]:
        return self.request_json(
            "POST",
            f"/api/v1/teacher/class/{class_id}/toggle-lock",
            add_csrf=True,
        )

    def teacher_rotate_code(self, class_id: int) -> dict[str, Any]:
        return self.request_json(
            "POST",
            f"/api/v1/teacher/class/{class_id}/rotate-code",
            add_csrf=True,
        )

    def teacher_set_enrollment_mode(self, class_id: int, enrollment_mode: str) -> dict[str, Any]:
        return self.request_json(
            "POST",
            f"/api/v1/teacher/class/{class_id}/set-enrollment-mode",
            json_body={"enrollment_mode": enrollment_mode},
            add_csrf=True,
        )
