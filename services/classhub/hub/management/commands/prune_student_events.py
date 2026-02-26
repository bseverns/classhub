"""Delete old student telemetry events by retention policy."""

from __future__ import annotations

import csv
import json
import os
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hub.models import StudentEvent


class Command(BaseCommand):
    help = "Prune old StudentEvent rows (append-only telemetry retention)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=int(os.getenv("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", "0")),
            help="Delete events older than this many days (0 disables by default).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report candidate count without deleting.",
        )
        parser.add_argument(
            "--export-csv",
            default="",
            help="Optional path to write matched rows as CSV before delete.",
        )

    def handle(self, *args, **opts):
        days = int(opts["older_than_days"])
        dry_run = bool(opts["dry_run"])
        export_csv = str(opts.get("export_csv") or "").strip()
        if days <= 0:
            raise CommandError(
                "Set --older-than-days to a positive integer (or set CLASSHUB_STUDENT_EVENT_RETENTION_DAYS)."
            )

        cutoff = timezone.now() - timedelta(days=days)
        qs = (
            StudentEvent.objects.filter(created_at__lt=cutoff)
            .select_related("classroom", "student")
            .order_by("id")
        )
        count = qs.count()
        self.stdout.write(f"Cutoff: {cutoff.isoformat()}")
        self.stdout.write(f"Matched events: {count}")

        if export_csv:
            export_path = Path(export_csv)
            try:
                export_path.parent.mkdir(parents=True, exist_ok=True)
                fields = [
                    "id",
                    "created_at",
                    "event_type",
                    "source",
                    "classroom_id",
                    "classroom_join_code",
                    "student_id",
                    "student_display_name",
                    "ip_address",
                    "details_json",
                ]
                exported_rows = 0
                with export_path.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=fields)
                    writer.writeheader()
                    for row in qs.iterator(chunk_size=500):
                        writer.writerow(
                            {
                                "id": row.id,
                                "created_at": row.created_at.isoformat(),
                                "event_type": row.event_type,
                                "source": row.source,
                                "classroom_id": row.classroom_id or "",
                                "classroom_join_code": (
                                    row.classroom.join_code if row.classroom_id and row.classroom else ""
                                ),
                                "student_id": row.student_id or "",
                                "student_display_name": (
                                    row.student.display_name if row.student_id and row.student else ""
                                ),
                                "ip_address": row.ip_address or "",
                                "details_json": json.dumps(row.details or {}, ensure_ascii=False, sort_keys=True),
                            }
                        )
                        exported_rows += 1
            except OSError as exc:
                raise CommandError(f"Failed to write CSV export to '{export_path}': {exc}") from exc

            self.stdout.write(self.style.SUCCESS(f"CSV export written: {export_path} ({exported_rows} rows)"))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] Would delete events: {count}"))
            return
        with StudentEvent.allow_retention_delete():
            deleted, _details = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted rows: {deleted}"))
