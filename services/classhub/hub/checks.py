from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.db import connection


@register(Tags.database, deploy=True)
def organization_assignment_check(app_configs, **kwargs):
    if not getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False):
        return []
    from .models import Class

    try:
        if Class._meta.db_table not in connection.introspection.table_names():
            return []
        count = Class.objects.filter(organization__isnull=True).count()
    except Exception:
        return []
    if not count:
        return []
    return [
        Warning(
            f"{count} class(es) have no organization while strict multi-org staff access is enabled.",
            hint="Assign every production class to an organization before release; the legacy fallback remains for migration only.",
            id="hub.W001",
        )
    ]
