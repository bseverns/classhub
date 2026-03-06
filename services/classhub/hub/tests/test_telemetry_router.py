from ._shared import *  # noqa: F401,F403

from config.dbrouters import TelemetryRouter
from hub_telemetry.models import TelemetryStudentEvent


_SQLITE_MEMORY_DB = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}


class TelemetryRouterTests(SimpleTestCase):
    @override_settings(DATABASES={"default": _SQLITE_MEMORY_DB})
    def test_router_leaves_telemetry_models_unrouted_when_db_not_configured(self):
        router = TelemetryRouter()
        self.assertIsNone(router.db_for_read(TelemetryStudentEvent))
        self.assertIsNone(router.db_for_write(TelemetryStudentEvent))
        self.assertFalse(router.allow_migrate("default", "hub_telemetry"))
        self.assertFalse(router.allow_migrate("telemetry", "hub_telemetry"))
        self.assertFalse(router.allow_migrate("telemetry", "hub"))

    @override_settings(DATABASES={"default": _SQLITE_MEMORY_DB, "telemetry": _SQLITE_MEMORY_DB})
    def test_router_routes_telemetry_models_when_db_configured(self):
        router = TelemetryRouter()
        self.assertEqual(router.db_for_read(TelemetryStudentEvent), "telemetry")
        self.assertEqual(router.db_for_write(TelemetryStudentEvent), "telemetry")
        self.assertTrue(router.allow_migrate("telemetry", "hub_telemetry"))
        self.assertFalse(router.allow_migrate("default", "hub_telemetry"))
        self.assertFalse(router.allow_migrate("telemetry", "hub"))
        self.assertIsNone(router.allow_migrate("default", "hub"))

