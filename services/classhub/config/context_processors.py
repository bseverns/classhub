"""Template context processors for Class Hub."""

from django.conf import settings

from hub.services.ui_density import default_ui_density_mode


def operator_profile(_request):
    profile = getattr(settings, "CLASSHUB_OPERATOR_PROFILE", {}) or {}
    return {"operator_profile": profile}


def program_ui(_request):
    program_profile = str(getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary") or "secondary")
    return {
        "program_profile": program_profile,
        "ui_density_mode": default_ui_density_mode(program_profile),
    }
