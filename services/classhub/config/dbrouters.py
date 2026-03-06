"""Database routers for ClassHub."""

from __future__ import annotations

from django.conf import settings

_TELEMETRY_DB_ALIAS = "telemetry"
_TELEMETRY_APP_LABELS = {"hub_telemetry"}


def _telemetry_db_configured() -> bool:
    return _TELEMETRY_DB_ALIAS in getattr(settings, "DATABASES", {})


class TelemetryRouter:
    """Route hub_telemetry app reads/writes/migrations to telemetry DB."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label in _TELEMETRY_APP_LABELS and _telemetry_db_configured():
            return _TELEMETRY_DB_ALIAS
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in _TELEMETRY_APP_LABELS and _telemetry_db_configured():
            return _TELEMETRY_DB_ALIAS
        return None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if labels & _TELEMETRY_APP_LABELS:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in _TELEMETRY_APP_LABELS:
            return _telemetry_db_configured() and db == _TELEMETRY_DB_ALIAS
        if db == _TELEMETRY_DB_ALIAS:
            return False
        return None

