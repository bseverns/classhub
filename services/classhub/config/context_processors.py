"""Template context processors for Class Hub."""

from django.conf import settings


def operator_profile(_request):
    profile = getattr(settings, "CLASSHUB_OPERATOR_PROFILE", {}) or {}
    return {"operator_profile": profile}
