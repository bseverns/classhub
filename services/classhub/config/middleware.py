import logging
import re
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from common.csp import resolve_csp_headers
from common.request_safety import build_staff_actor_key, client_ip_from_request, fixed_window_allow

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Attach optional security headers configured via settings."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        csp_policy, csp_report_only = resolve_csp_headers(
            mode=getattr(settings, "CSP_MODE", "relaxed"),
            relaxed_policy=getattr(settings, "CSP_POLICY_RELAXED", ""),
            strict_policy=getattr(settings, "CSP_POLICY_STRICT", ""),
            explicit_policy=getattr(settings, "CSP_POLICY", ""),
            explicit_report_only_policy=getattr(settings, "CSP_REPORT_ONLY_POLICY", ""),
            mode_defaults_enabled=bool(getattr(settings, "CSP_MODE_DEFAULTS_ENABLED", True)),
        )
        if csp_policy and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = csp_policy
        if csp_report_only and "Content-Security-Policy-Report-Only" not in response:
            response["Content-Security-Policy-Report-Only"] = csp_report_only
        permissions_policy = (getattr(settings, "PERMISSIONS_POLICY", "") or "").strip()
        if permissions_policy and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = permissions_policy
        referrer_policy = (
            getattr(settings, "SECURITY_REFERRER_POLICY", None)
            or getattr(settings, "SECURE_REFERRER_POLICY", "")
            or ""
        ).strip()
        if referrer_policy and "Referrer-Policy" not in response:
            response["Referrer-Policy"] = referrer_policy
        x_frame_options = (getattr(settings, "X_FRAME_OPTIONS", "") or "").strip()
        if x_frame_options and "X-Frame-Options" not in response:
            response["X-Frame-Options"] = x_frame_options
        return response


class TeacherOTPRequiredMiddleware:
    """Require OTP-verified staff sessions for /teach routes."""

    _EXEMPT_PREFIXES = (
        "/teach/login",
        "/teach/2fa/setup",
        "/teach/logout",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "TEACHER_2FA_REQUIRED", True):
            return self.get_response(request)

        path = request.path or ""
        if not path.startswith("/teach"):
            return self.get_response(request)
        if any(path.startswith(prefix) for prefix in self._EXEMPT_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_staff:
            return self.get_response(request)

        is_verified_attr = getattr(user, "is_verified", None)
        is_verified = bool(is_verified_attr() if callable(is_verified_attr) else is_verified_attr)
        if is_verified:
            return self.get_response(request)

        next_path = request.get_full_path()
        params = urlencode({"next": next_path}) if next_path else ""
        destination = "/teach/2fa/setup"
        if params:
            destination = f"{destination}?{params}"
        return HttpResponseRedirect(destination)


class AuthRateLimitMiddleware:
    """Throttle sensitive staff-auth POST endpoints."""

    _ADMIN_LOGIN_PATH = "/admin/login/"
    _TEACHER_LOGIN_PATH = "/teach/login"
    _TEACHER_SETUP_PATH = "/teach/2fa/setup"

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _key_part(raw: str, *, fallback: str = "unknown") -> str:
        value = (raw or "").strip().lower()
        if not value:
            return fallback
        return re.sub(r"[^a-z0-9_.@+-]", "_", value)[:96] or fallback

    @staticmethod
    def _rate_limited_response(*, path: str, window_seconds: int):
        if path == "/admin/login/":
            message = "Too many admin login attempts. Wait a minute and try again."
        elif path == "/teach/login":
            message = "Too many teacher login attempts. Wait a minute and try again."
        else:
            message = "Too many 2FA verification attempts. Wait a minute and try again."
        response = HttpResponse(message, status=429, content_type="text/plain; charset=utf-8")
        response["Retry-After"] = str(max(int(window_seconds), 1))
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response

    def __call__(self, request):
        if (request.method or "").upper() != "POST":
            return self.get_response(request)

        path = request.path or ""
        if path not in {self._ADMIN_LOGIN_PATH, self._TEACHER_LOGIN_PATH, self._TEACHER_SETUP_PATH}:
            return self.get_response(request)

        window_seconds = max(int(getattr(settings, "CLASSHUB_AUTH_RATE_LIMIT_WINDOW_SECONDS", 60) or 60), 1)
        if path == self._ADMIN_LOGIN_PATH:
            limit = int(getattr(settings, "CLASSHUB_ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE", 20) or 0)
            namespace = "admin_login"
        elif path == self._TEACHER_LOGIN_PATH:
            limit = int(getattr(settings, "CLASSHUB_TEACHER_LOGIN_RATE_LIMIT_PER_MINUTE", 20) or 0)
            namespace = "teacher_login"
        else:
            limit = int(getattr(settings, "CLASSHUB_TEACHER_2FA_RATE_LIMIT_PER_MINUTE", 10) or 0)
            namespace = "teacher_2fa_setup"
        if limit <= 0:
            return self.get_response(request)

        request_id = (request.headers.get("X-Request-ID") or request.META.get("HTTP_X_REQUEST_ID") or "").strip()
        client_ip = client_ip_from_request(
            request,
            trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
            xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
        )
        keys = [f"auth_rate:{namespace}:ip:{client_ip}"]
        if path == self._ADMIN_LOGIN_PATH:
            username = self._key_part(request.POST.get("username") or "", fallback="")
            if username:
                keys.append(f"auth_rate:{namespace}:username:{username}")
        else:
            actor = build_staff_actor_key(request, prefix="staff")
            if actor:
                keys.append(f"auth_rate:{namespace}:actor:{actor}")

        for key in keys:
            if fixed_window_allow(
                key,
                limit=limit,
                window_seconds=window_seconds,
                request_id=request_id,
            ):
                continue
            logger.warning(
                "auth_rate_limited request_id=%s path=%s key=%s",
                request_id or "unknown",
                path,
                key,
            )
            return self._rate_limited_response(path=path, window_seconds=window_seconds)

        return self.get_response(request)


class SiteModeMiddleware:
    """Gate high-impact routes when operator enables a degraded site mode."""

    _SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    _JOIN_ONLY_ALLOWED_EXACT = {"/", "/join", "/student", "/logout", "/healthz"}
    _JOIN_ONLY_ALLOWED_PREFIXES = ("/course/", "/lesson-video/", "/lesson-asset/", "/static/")
    _MAINTENANCE_ALLOWED_EXACT = {"/healthz"}
    _MAINTENANCE_ALLOWED_PREFIXES = ("/admin/", "/teach", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _site_mode() -> str:
        mode = (getattr(settings, "SITE_MODE", "normal") or "normal").strip().lower()
        return mode if mode else "normal"

    @staticmethod
    def _mode_message(mode: str) -> str:
        override = (getattr(settings, "SITE_MODE_MESSAGE", "") or "").strip()
        if override:
            return override
        product_name = (getattr(settings, "CLASSHUB_PRODUCT_NAME", "Class Hub") or "Class Hub").strip() or "Class Hub"
        if mode == "read-only":
            return f"{product_name} is in read-only mode. Uploads and write actions are temporarily disabled."
        if mode == "join-only":
            return f"{product_name} is in join-only mode. Class entry is available; teaching and upload actions are paused."
        if mode == "maintenance":
            return f"{product_name} is in maintenance mode. Please try again shortly."
        return ""

    @staticmethod
    def _wants_json(request) -> bool:
        path = (request.path or "").strip()
        accept = (request.headers.get("Accept", "") or "").lower()
        content_type = (request.headers.get("Content-Type", "") or "").lower()
        return (
            path == "/join"
            or "application/json" in accept
            or "application/json" in content_type
            or (request.headers.get("X-Requested-With", "") or "").lower() == "xmlhttprequest"
        )

    @classmethod
    def _join_only_allows(cls, path: str) -> bool:
        if path in cls._JOIN_ONLY_ALLOWED_EXACT:
            return True
        return any(path.startswith(prefix) for prefix in cls._JOIN_ONLY_ALLOWED_PREFIXES)

    @classmethod
    def _maintenance_allows(cls, path: str) -> bool:
        if path in cls._MAINTENANCE_ALLOWED_EXACT:
            return True
        return any(path.startswith(prefix) for prefix in cls._MAINTENANCE_ALLOWED_PREFIXES)

    @classmethod
    def _read_only_blocks(cls, request) -> bool:
        path = (request.path or "").strip()
        method = (request.method or "GET").upper()
        if path.startswith("/admin/"):
            return False
        if path.startswith("/internal/events/"):
            return False
        if path.startswith("/teach/2fa/setup"):
            return False
        if path.startswith("/material/") and path.endswith("/upload"):
            return True
        if method not in cls._SAFE_METHODS and path != "/join":
            return True
        return False

    def _blocked_response(self, request, *, mode: str):
        message = self._mode_message(mode)
        if self._wants_json(request):
            response = JsonResponse(
                {
                    "error": "site_mode_restricted",
                    "site_mode": mode,
                    "message": message,
                },
                status=503,
            )
        else:
            response = HttpResponse(message, status=503, content_type="text/plain; charset=utf-8")
        response["Retry-After"] = "120"
        response["Cache-Control"] = "no-store"
        return response

    def __call__(self, request):
        mode = self._site_mode()
        if mode == "normal":
            return self.get_response(request)

        path = (request.path or "").strip()
        if mode == "read-only" and self._read_only_blocks(request):
            return self._blocked_response(request, mode=mode)
        if mode == "join-only" and not self._join_only_allows(path):
            return self._blocked_response(request, mode=mode)
        if mode == "maintenance" and not self._maintenance_allows(path):
            return self._blocked_response(request, mode=mode)
        return self.get_response(request)
