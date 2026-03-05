"""Delete old student submissions according to retention policy."""

from __future__ import annotations

import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from hub.models import AuditEvent, Submission
from hub.services.retention_policy import class_submission_retention_days


class Command(BaseCommand):
    help = "Prune old student submissions and optionally remove files from disk."

    def _record_prune_audit(
        self,
        *,
        older_than_days: int,
        ignore_class_presets: bool,
        matched_rows: int,
        deleted_rows: int,
        deleted_files: int,
        file_errors: int,
        skipped_policy_rows: int,
    ) -> None:
        try:
            AuditEvent.objects.create(
                action="retention.prune_submissions",
                target_type="RetentionJob",
                target_id="submissions",
                summary=f"Pruned submissions (deleted {deleted_rows} rows)",
                metadata={
                    "older_than_days": int(older_than_days),
                    "ignore_class_presets": bool(ignore_class_presets),
                    "matched_rows": int(matched_rows),
                    "deleted_rows": int(deleted_rows),
                    "deleted_files": int(deleted_files),
                    "file_errors": int(file_errors),
                    "skipped_policy_rows": int(skipped_policy_rows),
                },
            )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Failed to record prune audit event: {exc}"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than-days",
            type=int,
            default=int(os.getenv("CLASSHUB_SUBMISSION_RETENTION_DAYS", "0")),
            help="Delete submissions older than this many days (0 disables by default).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=500,
            help="Batch size for scanning/deleting rows.",
        )
        parser.add_argument(
            "--ignore-class-presets",
            action="store_true",
            help="Use one global --older-than-days cutoff for all classes.",
        )

    def handle(self, *args, **opts):
        days = int(opts["older_than_days"])
        dry_run = bool(opts["dry_run"])
        chunk_size = max(int(opts["chunk_size"]), 1)
        ignore_class_presets = bool(opts["ignore_class_presets"])

        if days < 0:
            raise CommandError("Set --older-than-days to a non-negative integer.")
        if ignore_class_presets and days <= 0:
            raise CommandError("When --ignore-class-presets is set, --older-than-days must be positive.")

        now = timezone.now()
        qs = (
            Submission.objects.select_related("material__module__classroom")
            .only("id", "file", "uploaded_at", "material__module__classroom__retention_preset")
            .order_by("id")
        )
        self.stdout.write(f"Matched submissions (pre-policy scan): {qs.count()}")
        if ignore_class_presets:
            self.stdout.write(f"Global cutoff mode: {days} day(s)")
        else:
            self.stdout.write("Per-class retention preset mode: enabled")

        deleted_rows = 0
        deleted_files = 0
        file_errors = 0
        skipped_policy_rows = 0

        start_id = 0
        matched_rows = 0
        while True:
            batch = list(
                qs.filter(id__gt=start_id)
                .order_by("id")[:chunk_size]
            )
            if not batch:
                break

            for row in batch:
                start_id = row.id

                retention_days = days
                if not ignore_class_presets:
                    retention_days = class_submission_retention_days(
                        classroom=getattr(row.material.module, "classroom", None),
                        fallback_days=days,
                    )
                if retention_days <= 0:
                    skipped_policy_rows += 1
                    continue
                cutoff = now - timedelta(days=retention_days)
                if row.uploaded_at >= cutoff:
                    continue
                matched_rows += 1

                if dry_run:
                    deleted_rows += 1
                    continue

                try:
                    if row.file:
                        row.file.delete(save=False)
                        deleted_files += 1
                except Exception:
                    file_errors += 1

                row.delete()
                deleted_rows += 1

        self.stdout.write(f"Matched submissions (after policy): {matched_rows}")
        if skipped_policy_rows:
            self.stdout.write(f"Skipped by policy (retention disabled): {skipped_policy_rows}")

        if matched_rows == 0:
            self._record_prune_audit(
                older_than_days=days,
                ignore_class_presets=ignore_class_presets,
                matched_rows=0,
                deleted_rows=0,
                deleted_files=0,
                file_errors=0,
                skipped_policy_rows=skipped_policy_rows,
            )
            self.stdout.write(self.style.SUCCESS("Nothing to prune."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] Would delete rows: {deleted_rows}"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted rows: {deleted_rows}; files deleted: {deleted_files}; file delete errors: {file_errors}"
            )
        )
        self._record_prune_audit(
            older_than_days=days,
            ignore_class_presets=ignore_class_presets,
            matched_rows=matched_rows,
            deleted_rows=deleted_rows,
            deleted_files=deleted_files,
            file_errors=file_errors,
            skipped_policy_rows=skipped_policy_rows,
        )
