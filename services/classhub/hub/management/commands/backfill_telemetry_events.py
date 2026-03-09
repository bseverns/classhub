"""Backfill core telemetry events into the telemetry database."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hub.models import StudentEvent, StudentOutcomeEvent
from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent


@dataclass
class BackfillStats:
    stream: str
    scanned: int = 0
    existing: int = 0
    pending: int = 0
    inserted: int = 0
    skipped_or_failed: int = 0
    processed_batches: int = 0
    last_id: int = 0


class Command(BaseCommand):
    help = "Backfill StudentEvent/StudentOutcomeEvent rows into telemetry DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Rows per batch for each telemetry stream.",
        )
        parser.add_argument(
            "--since-id",
            type=int,
            default=0,
            help="Only process core rows where id > since-id.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report progress and summary without writing telemetry rows.",
        )
        parser.add_argument(
            "--max-batches",
            type=int,
            default=0,
            help="Stop after this many batches per stream (0 means unlimited).",
        )

    def handle(self, *args, **opts):
        batch_size = int(opts["batch_size"])
        since_id = int(opts["since_id"])
        dry_run = bool(opts["dry_run"])
        max_batches = int(opts["max_batches"])

        if "telemetry" not in getattr(settings, "DATABASES", {}):
            raise CommandError("Telemetry DB is not configured. Set CLASSHUB_TELEMETRY_DATABASE_URL first.")
        if batch_size <= 0:
            raise CommandError("--batch-size must be a positive integer.")
        if since_id < 0:
            raise CommandError("--since-id must be >= 0.")
        if max_batches < 0:
            raise CommandError("--max-batches must be >= 0.")

        self.stdout.write(
            "Starting telemetry backfill "
            f"(dry_run={dry_run} batch_size={batch_size} since_id={since_id} max_batches={max_batches})"
        )

        event_stats = self._backfill_student_events(
            batch_size=batch_size,
            since_id=since_id,
            dry_run=dry_run,
            max_batches=max_batches,
        )
        outcome_stats = self._backfill_student_outcome_events(
            batch_size=batch_size,
            since_id=since_id,
            dry_run=dry_run,
            max_batches=max_batches,
        )

        summary = {
            "mode": "dry_run" if dry_run else "write",
            "student_events": asdict(event_stats),
            "student_outcome_events": asdict(outcome_stats),
        }
        self.stdout.write("Backfill summary:")
        self.stdout.write(json.dumps(summary, indent=2, sort_keys=True))

        total_inserted = int(event_stats.inserted) + int(outcome_stats.inserted)
        total_pending = int(event_stats.pending) + int(outcome_stats.pending)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] Pending telemetry rows: {total_pending}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Inserted telemetry rows: {total_inserted}"))

    def _backfill_student_events(
        self,
        *,
        batch_size: int,
        since_id: int,
        dry_run: bool,
        max_batches: int,
    ) -> BackfillStats:
        stats = BackfillStats(stream="student_events")
        cursor = int(since_id)

        while True:
            if max_batches and stats.processed_batches >= max_batches:
                break

            batch = list(
                StudentEvent.objects.filter(id__gt=cursor)
                .order_by("id")
                .values(
                    "id",
                    "classroom_id",
                    "student_id",
                    "event_type",
                    "source",
                    "details",
                    "ip_address",
                    "created_at",
                )[:batch_size]
            )
            if not batch:
                break

            stats.processed_batches += 1
            stats.scanned += len(batch)
            cursor = int(batch[-1]["id"])
            stats.last_id = cursor

            core_ids = [int(row["id"]) for row in batch]
            existing_ids = set(
                TelemetryStudentEvent.objects.using("telemetry")
                .filter(core_event_id__in=core_ids)
                .values_list("core_event_id", flat=True)
            )
            stats.existing += len(existing_ids)

            pending_rows = [row for row in batch if int(row["id"]) not in existing_ids]
            stats.pending += len(pending_rows)

            inserted = 0
            if pending_rows and not dry_run:
                try:
                    TelemetryStudentEvent.objects.using("telemetry").bulk_create(
                        [
                            TelemetryStudentEvent(
                                core_event_id=int(row["id"]),
                                classroom_id=row["classroom_id"],
                                student_id=row["student_id"],
                                event_type=row["event_type"],
                                source=row["source"],
                                details=row["details"] or {},
                                ip_address=row["ip_address"],
                                created_at=row["created_at"],
                            )
                            for row in pending_rows
                        ],
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )
                except Exception as exc:
                    raise CommandError(
                        f"Student event backfill failed at core id {cursor}: {exc.__class__.__name__}"
                    ) from exc

                inserted_ids = set(
                    TelemetryStudentEvent.objects.using("telemetry")
                    .filter(core_event_id__in=[int(row["id"]) for row in pending_rows])
                    .values_list("core_event_id", flat=True)
                )
                inserted = len(inserted_ids)

            stats.inserted += inserted
            if not dry_run:
                stats.skipped_or_failed += max(len(pending_rows) - inserted, 0)
            self.stdout.write(
                "[student_events] "
                f"batch={stats.processed_batches} scanned={stats.scanned} pending={stats.pending} "
                f"inserted={stats.inserted} skipped_or_failed={stats.skipped_or_failed} last_id={stats.last_id}"
            )

        return stats

    def _backfill_student_outcome_events(
        self,
        *,
        batch_size: int,
        since_id: int,
        dry_run: bool,
        max_batches: int,
    ) -> BackfillStats:
        stats = BackfillStats(stream="student_outcome_events")
        cursor = int(since_id)

        while True:
            if max_batches and stats.processed_batches >= max_batches:
                break

            batch = list(
                StudentOutcomeEvent.objects.filter(id__gt=cursor)
                .order_by("id")
                .values(
                    "id",
                    "classroom_id",
                    "student_id",
                    "module_id",
                    "material_id",
                    "event_type",
                    "source",
                    "details",
                    "created_at",
                )[:batch_size]
            )
            if not batch:
                break

            stats.processed_batches += 1
            stats.scanned += len(batch)
            cursor = int(batch[-1]["id"])
            stats.last_id = cursor

            core_ids = [int(row["id"]) for row in batch]
            existing_ids = set(
                TelemetryStudentOutcomeEvent.objects.using("telemetry")
                .filter(core_outcome_event_id__in=core_ids)
                .values_list("core_outcome_event_id", flat=True)
            )
            stats.existing += len(existing_ids)

            pending_rows = [row for row in batch if int(row["id"]) not in existing_ids]
            stats.pending += len(pending_rows)

            inserted = 0
            if pending_rows and not dry_run:
                try:
                    TelemetryStudentOutcomeEvent.objects.using("telemetry").bulk_create(
                        [
                            TelemetryStudentOutcomeEvent(
                                core_outcome_event_id=int(row["id"]),
                                classroom_id=row["classroom_id"],
                                student_id=row["student_id"],
                                module_id=row["module_id"],
                                material_id=row["material_id"],
                                event_type=row["event_type"],
                                source=row["source"],
                                details=row["details"] or {},
                                created_at=row["created_at"],
                            )
                            for row in pending_rows
                        ],
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )
                except Exception as exc:
                    raise CommandError(
                        f"Student outcome event backfill failed at core id {cursor}: {exc.__class__.__name__}"
                    ) from exc

                inserted_ids = set(
                    TelemetryStudentOutcomeEvent.objects.using("telemetry")
                    .filter(core_outcome_event_id__in=[int(row["id"]) for row in pending_rows])
                    .values_list("core_outcome_event_id", flat=True)
                )
                inserted = len(inserted_ids)

            stats.inserted += inserted
            if not dry_run:
                stats.skipped_or_failed += max(len(pending_rows) - inserted, 0)
            self.stdout.write(
                "[student_outcome_events] "
                f"batch={stats.processed_batches} scanned={stats.scanned} pending={stats.pending} "
                f"inserted={stats.inserted} skipped_or_failed={stats.skipped_or_failed} last_id={stats.last_id}"
            )

        return stats
