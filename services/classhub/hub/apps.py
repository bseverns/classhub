from django.apps import AppConfig


class HubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hub"

    def ready(self):
        # Register file-cleanup signal handlers.
        from . import signals  # noqa: F401
