from django.conf import settings
from django_otp.admin import OTPAdminSite


def _admin_label() -> str:
    configured = (getattr(settings, "CLASSHUB_ADMIN_LABEL", "") or "").strip()
    return configured or "Class Hub Admin"


class ClassHubAdminSite(OTPAdminSite):
    enable_nav_sidebar = False

    @property
    def site_header(self) -> str:
        return _admin_label()

    @property
    def site_title(self) -> str:
        return _admin_label()

    @property
    def index_title(self) -> str:
        return _admin_label()

    def has_permission(self, request) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_active or not user.is_superuser:
            return False
        if not bool(getattr(settings, "ADMIN_2FA_REQUIRED", True)):
            return True
        is_verified = getattr(user, "is_verified", None)
        return bool(is_verified() if callable(is_verified) else False)
