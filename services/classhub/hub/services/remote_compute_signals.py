"""Derived operator signals for bounded remote helper compute."""

from __future__ import annotations


def build_remote_compute_signal_summary(*, status_result, evidence_result) -> dict:
    if not bool(getattr(status_result, "ok", False)):
        return {
            "level": "unavailable",
            "summary": "Trend signals unavailable",
            "detail": "The helper status path did not return enough evidence to judge remote-compute health for this class.",
            "remote_attempt_count": 0,
            "fallback_rate_pct": 0,
            "unused_activation_rate_pct": 0,
            "alerts": [],
        }

    activation_count = _safe_int(getattr(status_result, "activation_count", 0))
    remote_route_count = _safe_int(getattr(status_result, "remote_route_count", 0))
    fallback_local_count = _safe_int(getattr(status_result, "fallback_local_count", 0))
    degraded_transition_count = _safe_int(getattr(status_result, "degraded_transition_count", 0))
    provider_unreachable_count = _safe_int(getattr(status_result, "provider_unreachable_count", 0))
    unused_activation_count = _safe_int(getattr(status_result, "unused_activation_count", 0))
    avg_ready_seconds = _safe_int(getattr(status_result, "avg_ready_seconds", 0))

    remote_attempt_count = remote_route_count + fallback_local_count
    fallback_rate_pct = _percent(fallback_local_count, remote_attempt_count)
    unused_activation_rate_pct = _percent(unused_activation_count, activation_count)

    alerts: list[dict] = []
    if activation_count > 0 and unused_activation_rate_pct >= 50:
        alerts.append(
            {
                "level": "warning",
                "summary": "Lease waste risk",
                "detail": (
                    f"{unused_activation_count} of {activation_count} activations never routed a remote helper chat."
                ),
            }
        )
    if remote_attempt_count >= 4 and fallback_rate_pct >= 25:
        alerts.append(
            {
                "level": "warning",
                "summary": "Fallback rate is elevated",
                "detail": (
                    f"{fallback_local_count} of {remote_attempt_count} remote attempts fell back to local/default mode."
                ),
            }
        )
    if provider_unreachable_count > 0:
        alerts.append(
            {
                "level": "warning",
                "summary": "Provider reachability failed recently",
                "detail": (
                    f"The helper recorded {provider_unreachable_count} provider-unreachable event(s) for this class."
                ),
            }
        )
    elif degraded_transition_count >= 2:
        alerts.append(
            {
                "level": "notice",
                "summary": "Remote path has repeated degraded transitions",
                "detail": (
                    f"The lease entered degraded state {degraded_transition_count} time(s), so this path is not calm yet."
                ),
            }
        )
    if activation_count > 0 and avg_ready_seconds >= 30:
        alerts.append(
            {
                "level": "notice",
                "summary": "Warm-up is slow for class use",
                "detail": (
                    f"Average time to ready is {avg_ready_seconds} second(s), which is high for a live class workflow."
                ),
            }
        )

    if alerts:
        level = "attention" if any(alert["level"] == "warning" for alert in alerts) else "watch"
        summary = "Needs attention" if level == "attention" else "Watch this path"
        detail = "Recent remote-compute evidence shows instability, waste, or slow readiness."
    elif activation_count > 0:
        level = "calm"
        summary = "Trend signals are calm"
        detail = "Recent remote-compute evidence is bounded and has not crossed the current warning thresholds."
    else:
        level = "quiet"
        summary = "No trend evidence yet"
        detail = "This class has not built enough remote-compute history to infer longer-term health or waste signals."

    recent_sessions = list(getattr(evidence_result, "recent_sessions", []) or [])
    if recent_sessions and activation_count <= 0:
        activation_count = len([row for row in recent_sessions if isinstance(row, dict)])

    return {
        "level": level,
        "summary": summary,
        "detail": detail,
        "remote_attempt_count": remote_attempt_count,
        "fallback_rate_pct": fallback_rate_pct,
        "unused_activation_rate_pct": unused_activation_rate_pct,
        "alerts": alerts,
    }


def _percent(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return int(round((max(numerator, 0) * 100.0) / float(denominator)))


def _safe_int(value) -> int:
    try:
        return max(int(value or 0), 0)
    except Exception:
        return 0


__all__ = ["build_remote_compute_signal_summary"]
