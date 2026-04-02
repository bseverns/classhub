"""Template context processors for Class Hub."""

from django.conf import settings
from config.localization import localization_from_request

from hub.services.ui_density import default_ui_density_mode


def operator_profile(_request):
    profile = dict(getattr(settings, "CLASSHUB_OPERATOR_PROFILE", {}) or {})
    operator_name = str(
        getattr(
            settings,
            "CLASSHUB_OPERATOR_NAME",
            profile.get("operator_name", "createMPLS"),
        )
        or "createMPLS"
    )
    operator_descriptor = str(
        getattr(
            settings,
            "CLASSHUB_OPERATOR_DESCRIPTOR",
            profile.get("operator_descriptor", "a nonprofit educational group"),
        )
        or "a nonprofit educational group"
    )
    profile["operator_name"] = operator_name
    profile["operator_descriptor"] = operator_descriptor
    profile["product_name"] = str(
        getattr(
            settings,
            "CLASSHUB_PRODUCT_NAME",
            profile.get("product_name", "Class Hub"),
        )
        or "Class Hub"
    )
    profile["storage_location_text"] = str(
        getattr(
            settings,
            "CLASSHUB_STORAGE_LOCATION_TEXT",
            profile.get(
                "storage_location_text",
                f"this server is hosted by {operator_name}, {operator_descriptor}.",
            ),
        )
        or f"this server is hosted by {operator_name}, {operator_descriptor}."
    )
    profile["privacy_promise_text"] = str(
        getattr(
            settings,
            "CLASSHUB_PRIVACY_PROMISE_TEXT",
            profile.get("privacy_promise_text", "No tracking. No ads. No data broker sharing."),
        )
        or "No tracking. No ads. No data broker sharing."
    )
    profile["admin_label"] = str(
        getattr(
            settings,
            "CLASSHUB_ADMIN_LABEL",
            profile.get("admin_label", f"{operator_name} Course Admin"),
        )
        or f"{operator_name} Course Admin"
    )
    return {"operator_profile": profile}


def program_ui(_request):
    program_profile = str(getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary") or "secondary")
    return {
        "program_profile": program_profile,
        "ui_density_mode": default_ui_density_mode(program_profile),
        "student_kiosk_pwa_enabled": bool(getattr(settings, "CLASSHUB_STUDENT_KIOSK_PWA_ENABLED", False)),
        "student_kiosk_default": bool(getattr(settings, "CLASSHUB_STUDENT_KIOSK_DEFAULT", False)),
    }


def localization(request):
    context = localization_from_request(request)
    return {
        "localization": context,
        "html_lang": context.html_lang,
        "helper_language_code": context.helper_code,
        "is_rtl": context.is_rtl,
    }
