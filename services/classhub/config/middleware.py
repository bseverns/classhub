from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect


class SecurityHeadersMiddleware:
    """Attach optional security headers configured via settings."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        csp_report_only = (getattr(settings, "CSP_REPORT_ONLY_POLICY", "") or "").strip()
        if csp_report_only and "Content-Security-Policy-Report-Only" not in response:
            response["Content-Security-Policy-Report-Only"] = csp_report_only
        return response


class TeacherOTPRequiredMiddleware:
    """Require OTP-verified staff sessions for /teach routes."""

    _EXEMPT_PREFIXES = (
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
