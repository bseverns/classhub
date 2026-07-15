"""Durable remote-compute lease evidence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone as dj_timezone

from .engine.config_source import helper_explicit_env
from .models import RemoteComputeClassMetric, RemoteComputeLeaseEvent, RemoteComputeLeaseSession

_STARTING_STATES = {"requested", "starting"}
_ACTIVE_STATES = {"requested", "starting", "ready", "degraded", "stopping", "error"}


@dataclass(frozen=True)
class RemoteComputeEvidenceSnapshot:
    activation_count: int
    requested_duration_minutes_total: int
    starting_seconds_total: int
    ready_seconds_total: int
    degraded_seconds_total: int
    manual_stop_count: int
    auto_stop_count: int
    remote_route_count: int
    fallback_local_count: int
    leased_minutes_total: int
    approximate_cost_usd_total: str
    recent_sessions: list[dict]
    recent_events: list[dict]


@dataclass(frozen=True)
class RemoteComputeOperatorSnapshot:
    summary: dict
    recent_classes: list[dict]


def create_or_update_active_session(*, payload: dict, provider_label: str, provider_adapter: str) -> int:
    session = _session_from_payload(payload)
    now = _parse_iso_datetime(str(payload.get("requested_at") or "").strip()) or _utc_now()
    defaults = {
        "class_id": _safe_int(payload.get("class_id")),
        "requested_by": str(payload.get("requested_by") or "").strip()[:150],
        "requested_at": now,
        "requested_duration_minutes": _safe_int(payload.get("requested_duration_minutes")),
        "expires_at": _parse_iso_datetime(str(payload.get("expires_at") or "").strip()),
        "provider_label": str(provider_label or "").strip()[:80],
        "provider_adapter": str(provider_adapter or "").strip()[:80],
        "provider_request_id": str(payload.get("provider_request_id") or "").strip()[:120],
        "active": _normalize_state(payload.get("state")) != "off",
        "current_state": _normalize_state(payload.get("state"), default="requested"),
        "last_transition_at": _parse_iso_datetime(str(payload.get("last_transition_at") or "").strip()) or now,
        "last_healthcheck_at": _parse_iso_datetime(str(payload.get("last_healthcheck_at") or "").strip()),
        "last_ready_probe_at": _parse_iso_datetime(str(payload.get("last_ready_probe_at") or "").strip()),
        "last_ready_probe_ok_at": _parse_iso_datetime(str(payload.get("last_ready_probe_ok_at") or "").strip()),
        "last_routed_at": _parse_iso_datetime(str(payload.get("last_routed_at") or "").strip()),
        "last_error_code": str(payload.get("last_error_code") or "").strip()[:80],
        "last_readiness_reason_code": str(payload.get("last_readiness_reason_code") or "").strip()[:80],
        "status_detail": str(payload.get("status_detail") or "").strip()[:160],
        "estimated_cost_per_hour_usd": _estimated_cost_per_hour_usd(),
    }
    try:
        if session is None:
            session = RemoteComputeLeaseSession.objects.create(**defaults)
            _create_event(
                session=session,
                event_type="activation_requested",
                to_state=session.current_state,
                detail=session.status_detail,
            )
        else:
            for field, value in defaults.items():
                setattr(session, field, value)
            session.save()
        return int(session.id)
    except (OperationalError, ProgrammingError):
        return 0


def sync_session_from_payload(
    *,
    payload: dict,
    reason_code: str = "",
    event_type: str = "state_sync",
    detail: str = "",
    stop_mode: str = "",
) -> None:
    session = _session_from_payload(payload)
    if session is None:
        return
    try:
        new_state = _normalize_state(payload.get("state"), default=session.current_state or "off")
        transition_at = _parse_iso_datetime(str(payload.get("last_transition_at") or "").strip()) or _utc_now()
        prev_state = _normalize_state(session.current_state, default="off")
        _apply_elapsed_state_time(session=session, until=transition_at)
        session.current_state = new_state
        session.active = new_state != "off"
        session.last_transition_at = transition_at
        session.last_healthcheck_at = _parse_iso_datetime(str(payload.get("last_healthcheck_at") or "").strip())
        session.last_ready_probe_at = _parse_iso_datetime(str(payload.get("last_ready_probe_at") or "").strip())
        session.last_ready_probe_ok_at = _parse_iso_datetime(str(payload.get("last_ready_probe_ok_at") or "").strip())
        session.last_routed_at = _parse_iso_datetime(str(payload.get("last_routed_at") or "").strip())
        session.last_error_code = str(payload.get("last_error_code") or "").strip()[:80]
        session.last_readiness_reason_code = str(payload.get("last_readiness_reason_code") or "").strip()[:80]
        session.status_detail = str(detail or payload.get("status_detail") or "").strip()[:160]
        session.provider_request_id = str(payload.get("provider_request_id") or session.provider_request_id or "").strip()[:120]
        session.expires_at = _parse_iso_datetime(str(payload.get("expires_at") or "").strip())
        session.requested_duration_minutes = _safe_int(payload.get("requested_duration_minutes"))
        if new_state == "ready" and session.first_ready_at is None:
            session.first_ready_at = transition_at
        if new_state == "off":
            session.ended_at = transition_at
        session.leased_minutes = _leased_minutes_between(start=session.requested_at, end=session.ended_at or transition_at)
        session.save()
        if prev_state != new_state or reason_code or event_type not in {"state_sync", ""}:
            _create_event(
                session=session,
                event_type=event_type or "state_transition",
                from_state=prev_state,
                to_state=new_state,
                reason_code=reason_code,
                detail=session.status_detail if detail == "" else detail,
            )
        if stop_mode == "manual":
            session.manual_stop_count += 1
            session.save(update_fields=["manual_stop_count", "updated_at"])
        elif stop_mode == "auto":
            session.auto_stop_count += 1
            session.save(update_fields=["auto_stop_count", "updated_at"])
    except (OperationalError, ProgrammingError):
        return


def record_ready_probe(*, payload: dict, ok: bool, reason_code: str, detail: str) -> None:
    session = _session_from_payload(payload)
    if session is None:
        return
    now = _utc_now()
    try:
        session.last_ready_probe_at = now
        session.last_readiness_reason_code = str(reason_code or "").strip()[:80]
        if ok:
            session.last_ready_probe_ok_at = now
        session.status_detail = str(detail or "").strip()[:160]
        session.save(
            update_fields=[
                "last_ready_probe_at",
                "last_readiness_reason_code",
                "last_ready_probe_ok_at",
                "status_detail",
                "updated_at",
            ]
        )
        _create_event(
            session=session,
            event_type="ready_probe_passed" if ok else "ready_probe_failed",
            to_state=session.current_state,
            reason_code=reason_code,
            detail=detail,
        )
    except (OperationalError, ProgrammingError):
        return


def record_remote_route(*, payload: dict) -> None:
    session = _session_from_payload(payload)
    if session is None:
        return
    try:
        session.remote_route_count += 1
        session.last_routed_at = _parse_iso_datetime(str(payload.get("last_routed_at") or "").strip()) or _utc_now()
        session.leased_minutes = _leased_minutes_between(start=session.requested_at, end=session.last_routed_at)
        session.save(update_fields=["remote_route_count", "last_routed_at", "leased_minutes", "updated_at"])
    except (OperationalError, ProgrammingError):
        return


def record_local_fallback(*, payload: dict, reason_code: str, detail: str = "") -> None:
    session = _session_from_payload(payload)
    if session is None:
        return
    try:
        session.local_fallback_count += 1
        session.last_fallback_reason_code = str(reason_code or "").strip()[:80]
        session.status_detail = str(detail or session.status_detail or "").strip()[:160]
        session.save(update_fields=["local_fallback_count", "last_fallback_reason_code", "status_detail", "updated_at"])
        _create_event(
            session=session,
            event_type="local_fallback",
            from_state=session.current_state,
            to_state="degraded",
            reason_code=reason_code,
            detail=detail,
        )
    except (OperationalError, ProgrammingError):
        return


def build_class_evidence(*, class_id: int, recent_limit: int = 8, event_limit: int = 12) -> RemoteComputeEvidenceSnapshot:
    try:
        sessions = list(RemoteComputeLeaseSession.objects.filter(class_id=int(class_id)).order_by("-requested_at", "-id"))
        recent_events = list(
            RemoteComputeLeaseEvent.objects.filter(lease_session__class_id=int(class_id))
            .select_related("lease_session")
            .order_by("-occurred_at", "-id")[:event_limit]
        )
    except (OperationalError, ProgrammingError):
        return RemoteComputeEvidenceSnapshot(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", [], [])

    activation_count = 0
    requested_duration_minutes_total = 0
    starting_seconds_total = 0
    ready_seconds_total = 0
    degraded_seconds_total = 0
    manual_stop_count = 0
    auto_stop_count = 0
    remote_route_count = 0
    fallback_local_count = 0
    leased_minutes_total = 0
    approximate_cost_total = Decimal("0.00")

    recent_session_rows: list[dict] = []
    for index, session in enumerate(sessions):
        snapshot = _session_snapshot(session)
        activation_count += 1
        requested_duration_minutes_total += snapshot["requested_duration_minutes"]
        starting_seconds_total += snapshot["starting_seconds"]
        ready_seconds_total += snapshot["ready_seconds"]
        degraded_seconds_total += snapshot["degraded_seconds"]
        manual_stop_count += snapshot["manual_stop_count"]
        auto_stop_count += snapshot["auto_stop_count"]
        remote_route_count += snapshot["remote_route_count"]
        fallback_local_count += snapshot["fallback_local_count"]
        leased_minutes_total += snapshot["leased_minutes"]
        approximate_cost_total += Decimal(snapshot["estimated_cost_usd"] or "0.00")
        if index < max(int(recent_limit), 0):
            recent_session_rows.append(snapshot)

    recent_event_rows = [
        {
            "occurred_at": event.occurred_at.isoformat(),
            "event_type": str(event.event_type or "").strip(),
            "from_state": str(event.from_state or "").strip(),
            "to_state": str(event.to_state or "").strip(),
            "reason_code": str(event.reason_code or "").strip(),
            "detail": str(event.detail or "").strip(),
            "lease_session_id": int(event.lease_session_id or 0),
        }
        for event in recent_events
    ]
    return RemoteComputeEvidenceSnapshot(
        activation_count=activation_count,
        requested_duration_minutes_total=requested_duration_minutes_total,
        starting_seconds_total=starting_seconds_total,
        ready_seconds_total=ready_seconds_total,
        degraded_seconds_total=degraded_seconds_total,
        manual_stop_count=manual_stop_count,
        auto_stop_count=auto_stop_count,
        remote_route_count=remote_route_count,
        fallback_local_count=fallback_local_count,
        leased_minutes_total=leased_minutes_total,
        approximate_cost_usd_total=f"{approximate_cost_total.quantize(Decimal('0.01'))}",
        recent_sessions=recent_session_rows,
        recent_events=recent_event_rows,
    )


def build_operator_evidence(*, class_limit: int = 8) -> RemoteComputeOperatorSnapshot:
    try:
        metric_rows = list(RemoteComputeClassMetric.objects.order_by("-updated_at", "-id")[: max(int(class_limit), 1)])
        all_metric_rows = list(RemoteComputeClassMetric.objects.filter(activation_count__gt=0))
        session_rows = list(RemoteComputeLeaseSession.objects.only("leased_minutes", "estimated_cost_per_hour_usd"))
    except (OperationalError, ProgrammingError):
        return RemoteComputeOperatorSnapshot(summary=_empty_operator_summary(), recent_classes=[])

    activation_count = 0
    ready_transition_count = 0
    cumulative_ready_seconds = 0
    remote_route_count = 0
    fallback_local_count = 0
    degraded_transition_count = 0
    provider_unreachable_count = 0
    unused_activation_count = 0
    leased_minutes_total = 0
    approximate_cost_total = Decimal("0.00")

    for row in all_metric_rows:
        activation_count += int(row.activation_count or 0)
        ready_transition_count += int(row.ready_transition_count or 0)
        cumulative_ready_seconds += int(row.cumulative_ready_seconds or 0)
        remote_route_count += int(row.remote_route_count or 0)
        fallback_local_count += int(row.fallback_local_count or 0)
        degraded_transition_count += int(row.degraded_transition_count or 0)
        provider_unreachable_count += int(row.provider_unreachable_count or 0)
        unused_activation_count += int(row.unused_activation_count or 0)

    for session in session_rows:
        leased_minutes_total += int(session.leased_minutes or 0)
        approximate_cost_total += Decimal(session.estimated_cost_usd() or "0.00")

    avg_ready_seconds = 0
    if ready_transition_count > 0:
        avg_ready_seconds = int(round(cumulative_ready_seconds / float(ready_transition_count)))

    recent_classes = [
        {
            "class_id": int(row.class_id or 0),
            "activation_count": int(row.activation_count or 0),
            "ready_transition_count": int(row.ready_transition_count or 0),
            "avg_ready_seconds": int(round((row.cumulative_ready_seconds or 0) / float(row.ready_transition_count)))
            if int(row.ready_transition_count or 0) > 0
            else 0,
            "remote_route_count": int(row.remote_route_count or 0),
            "fallback_local_count": int(row.fallback_local_count or 0),
            "degraded_transition_count": int(row.degraded_transition_count or 0),
            "provider_unreachable_count": int(row.provider_unreachable_count or 0),
            "unused_activation_count": int(row.unused_activation_count or 0),
            "last_activation_at": _iso_or_empty(getattr(row, "last_activation_at", None)),
            "last_ready_at": _iso_or_empty(getattr(row, "last_ready_at", None)),
            "last_fallback_at": _iso_or_empty(getattr(row, "last_fallback_at", None)),
            "updated_at": _iso_or_empty(getattr(row, "updated_at", None)),
        }
        for row in metric_rows
        if int(row.activation_count or 0) > 0
    ]
    return RemoteComputeOperatorSnapshot(
        summary={
            "class_count_with_activity": len(all_metric_rows),
            "activation_count": activation_count,
            "ready_transition_count": ready_transition_count,
            "avg_ready_seconds": avg_ready_seconds,
            "remote_route_count": remote_route_count,
            "fallback_local_count": fallback_local_count,
            "degraded_transition_count": degraded_transition_count,
            "provider_unreachable_count": provider_unreachable_count,
            "unused_activation_count": unused_activation_count,
            "leased_minutes_total": leased_minutes_total,
            "approximate_cost_usd_total": f"{approximate_cost_total.quantize(Decimal('0.01'))}",
        },
        recent_classes=recent_classes,
    )


def _session_from_payload(payload: dict) -> RemoteComputeLeaseSession | None:
    lease_session_id = _safe_int(payload.get("lease_session_id"))
    if lease_session_id <= 0:
        return None
    try:
        return RemoteComputeLeaseSession.objects.filter(id=lease_session_id).first()
    except (OperationalError, ProgrammingError):
        return None


def _session_snapshot(session: RemoteComputeLeaseSession) -> dict:
    now = session.ended_at or _utc_now()
    starting_seconds = int(session.starting_seconds or 0)
    ready_seconds = int(session.ready_seconds or 0)
    degraded_seconds = int(session.degraded_seconds or 0)
    if session.active and session.last_transition_at:
        elapsed = max(int((now - session.last_transition_at).total_seconds()), 0)
        if session.current_state in _STARTING_STATES:
            starting_seconds += elapsed
        elif session.current_state == "ready":
            ready_seconds += elapsed
        elif session.current_state == "degraded":
            degraded_seconds += elapsed
    leased_minutes = _leased_minutes_between(start=session.requested_at, end=session.ended_at or now)
    estimated_cost = session.estimated_cost_usd()
    return {
        "lease_session_id": int(session.id or 0),
        "class_id": int(session.class_id or 0),
        "requested_by": str(session.requested_by or "").strip(),
        "requested_at": _iso_or_empty(session.requested_at),
        "requested_duration_minutes": int(session.requested_duration_minutes or 0),
        "expires_at": _iso_or_empty(session.expires_at),
        "provider_label": str(session.provider_label or "").strip(),
        "provider_adapter": str(session.provider_adapter or "").strip(),
        "provider_request_id": str(session.provider_request_id or "").strip(),
        "current_state": str(session.current_state or "off").strip(),
        "status_detail": str(session.status_detail or "").strip(),
        "last_error_code": str(session.last_error_code or "").strip(),
        "last_readiness_reason_code": str(session.last_readiness_reason_code or "").strip(),
        "last_fallback_reason_code": str(session.last_fallback_reason_code or "").strip(),
        "last_transition_at": _iso_or_empty(session.last_transition_at),
        "last_healthcheck_at": _iso_or_empty(session.last_healthcheck_at),
        "last_ready_probe_at": _iso_or_empty(session.last_ready_probe_at),
        "last_ready_probe_ok_at": _iso_or_empty(session.last_ready_probe_ok_at),
        "first_ready_at": _iso_or_empty(session.first_ready_at),
        "last_routed_at": _iso_or_empty(session.last_routed_at),
        "ended_at": _iso_or_empty(session.ended_at),
        "starting_seconds": starting_seconds,
        "ready_seconds": ready_seconds,
        "degraded_seconds": degraded_seconds,
        "leased_minutes": leased_minutes,
        "manual_stop_count": int(session.manual_stop_count or 0),
        "auto_stop_count": int(session.auto_stop_count or 0),
        "remote_route_count": int(session.remote_route_count or 0),
        "fallback_local_count": int(session.fallback_local_count or 0),
        "estimated_cost_usd": f"{estimated_cost}" if estimated_cost is not None else "",
    }


def _create_event(
    *,
    session: RemoteComputeLeaseSession,
    event_type: str,
    from_state: str = "",
    to_state: str = "",
    reason_code: str = "",
    detail: str = "",
) -> None:
    try:
        RemoteComputeLeaseEvent.objects.create(
            lease_session=session,
            event_type=str(event_type or "").strip()[:48],
            from_state=str(from_state or "").strip()[:32],
            to_state=str(to_state or "").strip()[:32],
            reason_code=str(reason_code or "").strip()[:80],
            detail=str(detail or "").strip()[:160],
        )
    except (OperationalError, ProgrammingError):
        return


def _apply_elapsed_state_time(*, session: RemoteComputeLeaseSession, until: datetime) -> None:
    last_transition = session.last_transition_at or session.requested_at
    if last_transition is None:
        return
    elapsed = max(int((until - last_transition).total_seconds()), 0)
    if elapsed <= 0:
        return
    if session.current_state in _STARTING_STATES:
        session.starting_seconds += elapsed
    elif session.current_state == "ready":
        session.ready_seconds += elapsed
    elif session.current_state == "degraded":
        session.degraded_seconds += elapsed


def _estimated_cost_per_hour_usd() -> Decimal | None:
    raw = str(helper_explicit_env("HELPER_REMOTE_COMPUTE_ESTIMATED_USD_PER_HOUR") or "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if value < 0:
        return None
    return value.quantize(Decimal("0.01"))


def _leased_minutes_between(*, start: datetime | None, end: datetime | None) -> int:
    if start is None or end is None or end <= start:
        return 0
    elapsed_seconds = max(int((end - start).total_seconds()), 0)
    return max(int((elapsed_seconds + 59) // 60), 0)


def _parse_iso_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso_or_empty(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _empty_operator_summary() -> dict:
    return {
        "class_count_with_activity": 0,
        "activation_count": 0,
        "ready_transition_count": 0,
        "avg_ready_seconds": 0,
        "remote_route_count": 0,
        "fallback_local_count": 0,
        "degraded_transition_count": 0,
        "provider_unreachable_count": 0,
        "unused_activation_count": 0,
        "leased_minutes_total": 0,
        "approximate_cost_usd_total": "",
    }


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _normalize_state(value, *, default: str = "off") -> str:
    token = str(value or "").strip().lower()
    if token in {"off", "requested", "starting", "ready", "degraded", "stopping", "error"}:
        return token
    return default


def _utc_now() -> datetime:
    return dj_timezone.now()
