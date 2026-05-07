import json

from django.conf import settings
from django.core.management.base import BaseCommand

from ...services.remote_compute_operator_snapshot import build_remote_compute_operator_snapshot


class Command(BaseCommand):
    help = "Export the derived remote-compute operator snapshot as JSON."

    def handle(self, *args, **options):
        snapshot = build_remote_compute_operator_snapshot(
            endpoint_url=(
                str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_OPERATOR_SNAPSHOT_URL", "") or "").strip()
            ),
            internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
            timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        )
        self.stdout.write(json.dumps(snapshot, indent=2, sort_keys=True))
