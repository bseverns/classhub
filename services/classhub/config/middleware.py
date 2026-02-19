from django.conf import settings


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
