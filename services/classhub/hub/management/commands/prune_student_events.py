"""Delete old student telemetry events by retention policy."""

from __future__ import annotations

import csv
import json
import os
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hub.models import AuditEvent, StudentEvent
from hub.services.retention_policy import class_event_retention_days


class Command(BaseCommand):
    help = "Prune old StudentEvent rows (append-only telemetry retention)."

    def _record_prune_audit(
        self,
        *,
        older_than_days: int,
        ignore_class_presets: bool,
        matched_rows: int,
        deleted_rows: int,
        exported_rows: int,
        export_csv: str,
        skipped_policy_rows: int,
    ) -> None:
        try:
            AuditEvent.objects.create(
                action="retention.prune_student_events",
                target_type="RetentionJob",
                target_id="student_events",
                summary=f"Pruned student events (deleted {deleted_rows} rows)",
                metadata={
                    "older_than_days": int(older_than_days),
                    "ignore_class_presets": bool(ignore_class_presets),
                    "matched_rows": int(matched_rows),
                    "deleted_rows": int(deleted_rows),
                    "exported_rows": int(exported_rows),
                    "export_csv": str(export_csv or ""),
                    "skipped_policy_rows": int(skipped_policy_rows),
                },
            )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Failed to record prune audit event: {exc}"))

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
        parser.add_argument(
            "--ignore-class-presets",
            action="store_true",
            help="Use one global --older-than-days cutoff for all classes.",
        )

    def handle(self, *args, **opts):
        days = int(opts["older_than_days"])
        dry_run = bool(opts["dry_run"])
        export_csv = str(opts.get("export_csv") or "").strip()
        ignore_class_presets = bool(opts["ignore_class_presets"])
        if days < 0:
            raise CommandError(
                "Set --older-than-days to a non-negative integer."
            )
        if ignore_class_presets and days <= 0:
            raise CommandError("When --ignore-class-presets is set, --older-than-days must be positive.")

        now = timezone.now()
        qs = StudentEvent.objects.select_related("classroom", "student").order_by("id")
        total_rows = qs.count()
        self.stdout.write(f"Matched events (pre-policy scan): {total_rows}")
        if ignore_class_presets:
            self.stdout.write(f"Global cutoff mode: {days} day(s)")
        else:
            self.stdout.write("Per-class retention preset mode: enabled")

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
        export_path = Path(export_csv) if export_csv else None
        writer = None
        export_fh = None
        if export_path is not None:
            export_path = Path(export_csv)
            try:
                export_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise CommandError(f"Failed to write CSV export to '{export_path}': {exc}") from exc
            export_fh = export_path.open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(export_fh, fieldnames=fields)
            writer.writeheader()

        candidate_ids: list[int] = []
        count = 0
        exported_rows = 0
        skipped_policy_rows = 0
        start_id = 0
        chunk_size = 500

        try:
            while True:
                batch = list(qs.filter(id__gt=start_id).order_by("id")[:chunk_size])
                if not batch:
                    break
                for row in batch:
                    start_id = row.id
                    retention_days = days
                    if not ignore_class_presets:
                        retention_days = class_event_retention_days(
                            classroom=row.classroom,
                            fallback_days=days,
                        )
                    if retention_days <= 0:
                        skipped_policy_rows += 1
                        continue
                    cutoff = now - timedelta(days=retention_days)
                    if row.created_at >= cutoff:
                        continue

                    candidate_ids.append(row.id)
                    count += 1
                    if writer is not None:
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
        finally:
            if export_fh is not None:
                export_fh.close()

        self.stdout.write(f"Matched events (after policy): {count}")
        if skipped_policy_rows:
            self.stdout.write(f"Skipped by policy (retention disabled): {skipped_policy_rows}")
        if export_path is not None:
            self.stdout.write(self.style.SUCCESS(f"CSV export written: {export_path} ({exported_rows} rows)"))

        if count == 0:
            self._record_prune_audit(
                older_than_days=days,
                ignore_class_presets=ignore_class_presets,
                matched_rows=0,
                deleted_rows=0,
                exported_rows=exported_rows,
                export_csv=str(export_path or ""),
                skipped_policy_rows=skipped_policy_rows,
            )
            self.stdout.write(self.style.SUCCESS("Nothing to prune."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] Would delete events: {count}"))
            return

        with StudentEvent.allow_retention_delete():
            deleted, _details = StudentEvent.objects.filter(id__in=candidate_ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted rows: {deleted}"))
        self._record_prune_audit(
            older_than_days=days,
            ignore_class_presets=ignore_class_presets,
            matched_rows=count,
            deleted_rows=deleted,
            exported_rows=exported_rows,
            export_csv=str(export_path or ""),
            skipped_policy_rows=skipped_policy_rows,
        )
