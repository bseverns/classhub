"""Read-only retention/lifecycle metrics for operator visibility."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO

from django.utils import timezone

from ..models import AuditEvent, Class, Submission
from .telemetry_reads import student_events_queryset
from .retention_policy import class_event_retention_days, class_submission_retention_days

_PRUNE_ACTION_SUBMISSIONS = "retention.prune_submissions"
_PRUNE_ACTION_EVENTS = "retention.prune_student_events"
_PRUNE_ACTIONS = (_PRUNE_ACTION_SUBMISSIONS, _PRUNE_ACTION_EVENTS)
_PRUNE_TREND_WINDOW_DAYS = 7


@dataclass(frozen=True)
class _RetentionPreset:
    retention_preset: str


def _group_class_ids_by_days(
    class_rows: list[tuple[int, str]],
    *,
    resolve_days,
) -> tuple[dict[int, list[int]], int]:
    grouped: dict[int, list[int]] = {}
    disabled_count = 0
    for class_id, preset in class_rows:
        days = int(resolve_days(classroom=_RetentionPreset(preset)))
        if days <= 0:
            disabled_count += 1
            continue
        grouped.setdefault(days, []).append(int(class_id))
    return grouped, disabled_count


def _count_submission_policy_overdue_rows(
    *,
    grouped_submission_days: dict[int, list[int]],
    now,
) -> int:
    total = 0
    for days, class_ids in grouped_submission_days.items():
        cutoff = now - timedelta(days=int(days))
        total += Submission.objects.filter(
            material__module__classroom_id__in=class_ids,
            uploaded_at__lt=cutoff,
        ).count()
    return total


def _count_event_policy_overdue_rows(
    *,
    grouped_event_days: dict[int, list[int]],
    fallback_event_days: int,
    now,
) -> int:
    total = 0
    for days, class_ids in grouped_event_days.items():
        cutoff = now - timedelta(days=int(days))
        total += student_events_queryset().filter(
            classroom_id__in=class_ids,
            created_at__lt=cutoff,
        ).count()
    if fallback_event_days > 0:
        fallback_cutoff = now - timedelta(days=fallback_event_days)
        total += student_events_queryset().filter(
            classroom_id__isnull=True,
            created_at__lt=fallback_cutoff,
        ).count()
    return total


def _latest_audit_by_action(action: str):
    return AuditEvent.objects.filter(action=action).only("id", "created_at", "action", "summary", "metadata").first()


def _metadata_int(row, key: str) -> int:
    metadata = getattr(row, "metadata", {}) or {}
    try:
        return max(int(metadata.get(key) or 0), 0)
    except Exception:
        return 0


def _build_prune_trend_rows(*, prune_runs: list, now) -> list[dict]:
    bucket: dict[str, dict] = {}
    for offset in range(_PRUNE_TREND_WINDOW_DAYS):
        day = (now - timedelta(days=offset)).date().isoformat()
        bucket[day] = {
            "date": day,
            "run_count": 0,
            "deleted_rows": 0,
            "matched_rows": 0,
        }
    for run in prune_runs:
        day = timezone.localtime(run.created_at).date().isoformat()
        row = bucket.get(day)
        if not row:
            continue
        row["run_count"] += 1
        row["deleted_rows"] += _metadata_int(run, "deleted_rows")
        row["matched_rows"] += _metadata_int(run, "matched_rows")
    return [bucket[key] for key in sorted(bucket.keys())]


def _iso_or_empty(value) -> str:
    if not value:
        return ""
    try:
        return value.isoformat()
    except Exception:
        return ""


def _serialize_prune_run(row) -> dict:
    return {
        "created_at": _iso_or_empty(getattr(row, "created_at", None)),
        "action": str(getattr(row, "action", "") or ""),
        "summary": str(getattr(row, "summary", "") or ""),
        "deleted_rows": _metadata_int(row, "deleted_rows"),
        "matched_rows": _metadata_int(row, "matched_rows"),
    }


def build_data_lifespan_snapshot() -> dict:
    now = timezone.now()
    class_rows = list(Class.objects.values_list("id", "retention_preset"))
    grouped_submission_days, submission_retention_disabled_classes = _group_class_ids_by_days(
        class_rows,
        resolve_days=class_submission_retention_days,
    )
    grouped_event_days, event_retention_disabled_classes = _group_class_ids_by_days(
        class_rows,
        resolve_days=class_event_retention_days,
    )
    fallback_submission_days = int(class_submission_retention_days(classroom=None))
    fallback_event_days = int(class_event_retention_days(classroom=None))

    events_total = student_events_queryset().count()
    submissions_total = Submission.objects.count()
    oldest_event = student_events_queryset().order_by("created_at").values_list("created_at", flat=True).first()
    oldest_submission = Submission.objects.order_by("uploaded_at").values_list("uploaded_at", flat=True).first()

    overdue_submissions = _count_submission_policy_overdue_rows(
        grouped_submission_days=grouped_submission_days,
        now=now,
    )
    overdue_events = _count_event_policy_overdue_rows(
        grouped_event_days=grouped_event_days,
        fallback_event_days=fallback_event_days,
        now=now,
    )

    submissions_within_policy = max(submissions_total - overdue_submissions, 0)
    events_within_policy = max(events_total - overdue_events, 0)

    prune_runs_recent = list(
        AuditEvent.objects.filter(action__in=_PRUNE_ACTIONS)
        .only("id", "created_at", "action", "summary", "metadata")
        .order_by("-created_at", "-id")[:200]
    )
    prune_runs = prune_runs_recent[:25]
    last_prune_run = prune_runs[0] if prune_runs else None
    last_submission_prune = _latest_audit_by_action(_PRUNE_ACTION_SUBMISSIONS)
    last_event_prune = _latest_audit_by_action(_PRUNE_ACTION_EVENTS)

    return {
        "captured_at": now,
        "events_total": events_total,
        "submissions_total": submissions_total,
        "oldest_event": oldest_event,
        "oldest_submission": oldest_submission,
        "overdue_events": overdue_events,
        "overdue_submissions": overdue_submissions,
        "events_within_policy": events_within_policy,
        "submissions_within_policy": submissions_within_policy,
        "fallback_event_days": fallback_event_days,
        "fallback_submission_days": fallback_submission_days,
        "event_retention_disabled_classes": event_retention_disabled_classes,
        "submission_retention_disabled_classes": submission_retention_disabled_classes,
        "class_count": len(class_rows),
        "last_prune_run": last_prune_run,
        "last_submission_prune": last_submission_prune,
        "last_event_prune": last_event_prune,
        "prune_runs": prune_runs,
        "prune_trend_rows": _build_prune_trend_rows(prune_runs=prune_runs_recent, now=now),
        "overdue_rows": [
            {
                "label": "Student events",
                "total_rows": int(events_total),
                "overdue_rows": int(overdue_events),
                "within_policy_rows": int(events_within_policy),
            },
            {
                "label": "Submissions",
                "total_rows": int(submissions_total),
                "overdue_rows": int(overdue_submissions),
                "within_policy_rows": int(submissions_within_policy),
            },
        ],
        "policy_overdue_total": int(overdue_events + overdue_submissions),
    }


def build_data_lifespan_snapshot_export(snapshot: dict) -> dict:
    prune_runs = [_serialize_prune_run(row) for row in (snapshot.get("prune_runs") or [])]
    return {
        "captured_at": _iso_or_empty(snapshot.get("captured_at")),
        "class_count": int(snapshot.get("class_count") or 0),
        "policy_overdue_total": int(snapshot.get("policy_overdue_total") or 0),
        "events_total": int(snapshot.get("events_total") or 0),
        "submissions_total": int(snapshot.get("submissions_total") or 0),
        "overdue_events": int(snapshot.get("overdue_events") or 0),
        "overdue_submissions": int(snapshot.get("overdue_submissions") or 0),
        "events_within_policy": int(snapshot.get("events_within_policy") or 0),
        "submissions_within_policy": int(snapshot.get("submissions_within_policy") or 0),
        "oldest_event": _iso_or_empty(snapshot.get("oldest_event")),
        "oldest_submission": _iso_or_empty(snapshot.get("oldest_submission")),
        "fallback_event_days": int(snapshot.get("fallback_event_days") or 0),
        "fallback_submission_days": int(snapshot.get("fallback_submission_days") or 0),
        "event_retention_disabled_classes": int(snapshot.get("event_retention_disabled_classes") or 0),
        "submission_retention_disabled_classes": int(snapshot.get("submission_retention_disabled_classes") or 0),
        "last_prune_run_at": _iso_or_empty(getattr(snapshot.get("last_prune_run"), "created_at", None)),
        "last_submission_prune_at": _iso_or_empty(getattr(snapshot.get("last_submission_prune"), "created_at", None)),
        "last_event_prune_at": _iso_or_empty(getattr(snapshot.get("last_event_prune"), "created_at", None)),
        "overdue_rows": list(snapshot.get("overdue_rows") or []),
        "prune_trend_rows": list(snapshot.get("prune_trend_rows") or []),
        "prune_runs": prune_runs,
    }


def build_data_lifespan_snapshot_csv(snapshot: dict) -> str:
    payload = build_data_lifespan_snapshot_export(snapshot)
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["field", "value"])
    writer.writerow(["captured_at", payload["captured_at"]])
    writer.writerow(["class_count", payload["class_count"]])
    writer.writerow(["policy_overdue_total", payload["policy_overdue_total"]])
    writer.writerow([])

    writer.writerow(["overdue_summary"])
    writer.writerow(["label", "total_rows", "overdue_rows", "within_policy_rows"])
    for row in payload["overdue_rows"]:
        writer.writerow(
            [
                row.get("label", ""),
                int(row.get("total_rows") or 0),
                int(row.get("overdue_rows") or 0),
                int(row.get("within_policy_rows") or 0),
            ]
        )
    writer.writerow([])

    writer.writerow(["prune_trend_last_7_days"])
    writer.writerow(["date", "run_count", "deleted_rows", "matched_rows"])
    for row in payload["prune_trend_rows"]:
        writer.writerow(
            [
                row.get("date", ""),
                int(row.get("run_count") or 0),
                int(row.get("deleted_rows") or 0),
                int(row.get("matched_rows") or 0),
            ]
        )
    writer.writerow([])

    writer.writerow(["recent_prune_runs"])
    writer.writerow(["created_at", "action", "deleted_rows", "matched_rows", "summary"])
    for row in payload["prune_runs"]:
        writer.writerow(
            [
                row.get("created_at", ""),
                row.get("action", ""),
                int(row.get("deleted_rows") or 0),
                int(row.get("matched_rows") or 0),
                row.get("summary", ""),
            ]
        )
    return out.getvalue()


__all__ = [
    "build_data_lifespan_snapshot",
    "build_data_lifespan_snapshot_csv",
    "build_data_lifespan_snapshot_export",
]
