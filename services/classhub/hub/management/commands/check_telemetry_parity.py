"""Compare core and telemetry event aggregates for split-rollout parity."""

from __future__ import annotations

import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from hub.models import StudentEvent, StudentOutcomeEvent
from hub_telemetry.models import TelemetryStudentEvent, TelemetryStudentOutcomeEvent


class Command(BaseCommand):
    help = "Check parity between core and telemetry event/outcome aggregates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-days",
            type=int,
            default=7,
            help="Compare rows where created_at is within the trailing N days.",
        )
        parser.add_argument(
            "--max-deltas",
            type=int,
            default=50,
            help="Maximum number of delta rows to print in the final report.",
        )
        parser.add_argument(
            "--allow-drift",
            action="store_true",
            help="Exit successfully even when parity deltas are detected.",
        )

    def handle(self, *args, **opts):
        window_days = int(opts["window_days"])
        max_deltas = int(opts["max_deltas"])
        allow_drift = bool(opts["allow_drift"])

        if "telemetry" not in getattr(settings, "DATABASES", {}):
            raise CommandError("Telemetry DB is not configured. Set CLASSHUB_TELEMETRY_DATABASE_URL first.")
        if window_days <= 0:
            raise CommandError("--window-days must be a positive integer.")
        if max_deltas <= 0:
            raise CommandError("--max-deltas must be a positive integer.")

        window_start = timezone.now() - timedelta(days=window_days)
        self.stdout.write(
            f"Checking telemetry parity (window_days={window_days}, window_start={window_start.isoformat()})"
        )

        report = self._build_parity_report(window_start=window_start, window_days=window_days, max_deltas=max_deltas)
        self.stdout.write(json.dumps(report, indent=2, sort_keys=True))

        deltas_total = int(report.get("delta_count", 0))
        if deltas_total > 0 and not allow_drift:
            raise CommandError(
                f"Telemetry parity drift detected ({deltas_total} delta(s)); "
                "re-run with --allow-drift to inspect without failing."
            )
        if deltas_total > 0:
            self.stdout.write(self.style.WARNING(f"Parity drift detected: {deltas_total} delta(s)"))
            return
        self.stdout.write(self.style.SUCCESS("Telemetry parity check passed (no deltas detected)."))

    def _build_parity_report(self, *, window_start, window_days: int, max_deltas: int) -> dict:
        core_sections = self._collect_section_counts(db_alias="default", window_start=window_start, is_telemetry=False)
        telemetry_sections = self._collect_section_counts(db_alias="telemetry", window_start=window_start, is_telemetry=True)

        section_names = sorted(set(core_sections.keys()) | set(telemetry_sections.keys()))
        section_summaries: list[dict] = []
        deltas: list[dict] = []

        for section in section_names:
            core_map = core_sections.get(section, {})
            telemetry_map = telemetry_sections.get(section, {})
            section_deltas = self._diff_counts(section=section, core_map=core_map, telemetry_map=telemetry_map)
            section_summaries.append(
                {
                    "section": section,
                    "core_total": int(sum(core_map.values())),
                    "telemetry_total": int(sum(telemetry_map.values())),
                    "key_count": int(len(set(core_map.keys()) | set(telemetry_map.keys()))),
                    "delta_count": int(len(section_deltas)),
                }
            )
            deltas.extend(section_deltas)

        return {
            "generated_at": timezone.now().isoformat(),
            "window_days": int(window_days),
            "window_start": window_start.isoformat(),
            "section_summaries": section_summaries,
            "delta_count": int(len(deltas)),
            "deltas": deltas[:max_deltas],
            "truncated_deltas": max(int(len(deltas) - max_deltas), 0),
        }

    def _collect_section_counts(self, *, db_alias: str, window_start, is_telemetry: bool) -> dict[str, dict[str, int]]:
        event_model = TelemetryStudentEvent if is_telemetry else StudentEvent
        outcome_model = TelemetryStudentOutcomeEvent if is_telemetry else StudentOutcomeEvent

        return {
            "student_events_by_day_type": self._student_events_by_day_type(
                model=event_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
            "student_outcomes_by_day_type": self._student_outcomes_by_day_type(
                model=outcome_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
            "outcome_rollups_by_class_type": self._outcome_rollups_by_class_type(
                model=outcome_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
            "outcome_active_students_by_class": self._outcome_active_students_by_class(
                model=outcome_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
            "support_unresolved_stuck_by_class": self._support_unresolved_stuck_by_class(
                model=event_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
            "support_unresolved_delete_requests_by_class": self._support_unresolved_delete_requests_by_class(
                model=event_model,
                db_alias=db_alias,
                window_start=window_start,
            ),
        }

    def _student_events_by_day_type(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        rows = (
            model.objects.using(db_alias)
            .filter(created_at__gte=window_start)
            .annotate(day=TruncDate("created_at"))
            .values("day", "event_type")
            .annotate(total=Count("id"))
        )
        result: dict[str, int] = {}
        for row in rows:
            day = str(row["day"])
            event_type = str(row["event_type"] or "")
            result[f"{day}|{event_type}"] = int(row["total"] or 0)
        return result

    def _student_outcomes_by_day_type(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        rows = (
            model.objects.using(db_alias)
            .filter(created_at__gte=window_start)
            .annotate(day=TruncDate("created_at"))
            .values("day", "event_type")
            .annotate(total=Count("id"))
        )
        result: dict[str, int] = {}
        for row in rows:
            day = str(row["day"])
            event_type = str(row["event_type"] or "")
            result[f"{day}|{event_type}"] = int(row["total"] or 0)
        return result

    def _outcome_rollups_by_class_type(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        rows = (
            model.objects.using(db_alias)
            .filter(created_at__gte=window_start)
            .values("classroom_id", "event_type")
            .annotate(total=Count("id"))
        )
        result: dict[str, int] = {}
        for row in rows:
            classroom_id = int(row["classroom_id"] or 0)
            event_type = str(row["event_type"] or "")
            result[f"{classroom_id}|{event_type}"] = int(row["total"] or 0)
        return result

    def _outcome_active_students_by_class(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        rows = (
            model.objects.using(db_alias)
            .filter(created_at__gte=window_start, student_id__isnull=False)
            .values("classroom_id")
            .annotate(total=Count("student_id", distinct=True))
        )
        result: dict[str, int] = {}
        for row in rows:
            classroom_id = int(row["classroom_id"] or 0)
            result[str(classroom_id)] = int(row["total"] or 0)
        return result

    def _support_unresolved_stuck_by_class(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        tracked_types = [
            StudentEvent.EVENT_MICRO_CHECK_CAN_DO_THIS,
            StudentEvent.EVENT_MICRO_CHECK_STUCK,
            StudentEvent.EVENT_MICRO_CHECK_TAUGHT_SOMEONE,
            StudentEvent.EVENT_MICRO_CHECK_STUCK_RESOLVED,
        ]
        latest_by_student = self._latest_event_type_by_student_and_class(
            model=model,
            db_alias=db_alias,
            window_start=window_start,
            event_types=tracked_types,
        )
        counts: dict[str, int] = {}
        for (classroom_id, _student_id), event_type in latest_by_student.items():
            if event_type != StudentEvent.EVENT_MICRO_CHECK_STUCK:
                continue
            key = str(classroom_id)
            counts[key] = int(counts.get(key, 0)) + 1
        return counts

    def _support_unresolved_delete_requests_by_class(self, *, model, db_alias: str, window_start) -> dict[str, int]:
        tracked_types = [
            StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED,
        ]
        latest_by_student = self._latest_event_type_by_student_and_class(
            model=model,
            db_alias=db_alias,
            window_start=window_start,
            event_types=tracked_types,
        )
        counts: dict[str, int] = {}
        for (classroom_id, _student_id), event_type in latest_by_student.items():
            if event_type != StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST:
                continue
            key = str(classroom_id)
            counts[key] = int(counts.get(key, 0)) + 1
        return counts

    def _latest_event_type_by_student_and_class(
        self,
        *,
        model,
        db_alias: str,
        window_start,
        event_types: list[str],
    ) -> dict[tuple[int, int], str]:
        rows = (
            model.objects.using(db_alias)
            .filter(
                created_at__gte=window_start,
                student_id__isnull=False,
                event_type__in=event_types,
            )
            .values("classroom_id", "student_id", "event_type", "created_at", "id")
            .order_by("classroom_id", "student_id", "-created_at", "-id")
        )
        latest: dict[tuple[int, int], str] = {}
        for row in rows:
            classroom_id = int(row["classroom_id"] or 0)
            student_id = int(row["student_id"] or 0)
            if student_id <= 0:
                continue
            key = (classroom_id, student_id)
            if key in latest:
                continue
            latest[key] = str(row["event_type"] or "")
        return latest

    def _diff_counts(self, *, section: str, core_map: dict[str, int], telemetry_map: dict[str, int]) -> list[dict]:
        deltas: list[dict] = []
        for key in sorted(set(core_map.keys()) | set(telemetry_map.keys())):
            core_value = int(core_map.get(key, 0))
            telemetry_value = int(telemetry_map.get(key, 0))
            if core_value == telemetry_value:
                continue
            deltas.append(
                {
                    "section": section,
                    "key": key,
                    "core": core_value,
                    "telemetry": telemetry_value,
                    "difference": telemetry_value - core_value,
                }
            )
        return deltas
