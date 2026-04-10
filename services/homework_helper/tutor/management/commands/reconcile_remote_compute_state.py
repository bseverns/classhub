from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from ...remote_compute_control import reconcile_remote_compute_state


class Command(BaseCommand):
    help = "Reconcile durable remote helper lease state against expiry, idle stop, and optional provider refresh."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-refresh",
            action="store_true",
            help="Skip provider refresh and only apply local expiry/idle reconciliation.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress success output unless JSON is requested.",
        )

    def handle(self, *args, **options):
        lease = reconcile_remote_compute_state(refresh=not bool(options.get("no_refresh")))
        payload = {
            "state": lease.state,
            "class_id": lease.class_id,
            "active": bool(lease.active),
            "use_remote_backend": bool(lease.use_remote_backend),
            "requested_by": str(lease.requested_by or ""),
            "expires_at": str(lease.expires_at or ""),
            "remaining_minutes": int(lease.remaining_minutes or 0),
            "last_error_code": str(lease.last_error_code or ""),
            "status_detail": str(lease.status_detail or ""),
        }
        if options.get("json"):
            self.stdout.write(json.dumps(payload, sort_keys=True))
            return
        if options.get("quiet"):
            return
        self.stdout.write(self.style.SUCCESS(json.dumps(payload, sort_keys=True)))
