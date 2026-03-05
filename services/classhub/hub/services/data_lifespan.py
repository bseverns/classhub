"""Read-only retention/lifecycle metrics for operator visibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from ..models import AuditEvent, Class, StudentEvent, Submission
from .retention_policy import class_event_retention_days, class_submission_retention_days

_PRUNE_ACTION_SUBMISSIONS = "retention.prune_submissions"
_PRUNE_ACTION_EVENTS = "retention.prune_student_events"
_PRUNE_ACTIONS = (_PRUNE_ACTION_SUBMISSIONS, _PRUNE_ACTION_EVENTS)


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
        total += StudentEvent.objects.filter(
            classroom_id__in=class_ids,
            created_at__lt=cutoff,
        ).count()
    if fallback_event_days > 0:
        fallback_cutoff = now - timedelta(days=fallback_event_days)
        total += StudentEvent.objects.filter(
            classroom__isnull=True,
            created_at__lt=fallback_cutoff,
        ).count()
    return total


def _latest_audit_by_action(action: str):
    return AuditEvent.objects.filter(action=action).only("id", "created_at", "action", "summary", "metadata").first()


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

    events_total = StudentEvent.objects.count()
    submissions_total = Submission.objects.count()
    oldest_event = StudentEvent.objects.order_by("created_at").values_list("created_at", flat=True).first()
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

    prune_runs = list(
        AuditEvent.objects.filter(action__in=_PRUNE_ACTIONS)
        .only("id", "created_at", "action", "summary", "metadata")
        .order_by("-created_at", "-id")[:25]
    )
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
        "policy_overdue_total": int(overdue_events + overdue_submissions),
    }


__all__ = ["build_data_lifespan_snapshot"]
