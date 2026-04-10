from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone


class RemoteComputeLeaseRecord(models.Model):
    """Durable singleton row for the active remote helper lease."""

    slot = models.CharField(max_length=32, primary_key=True, default="active", editable=False)
    state = models.CharField(max_length=32, default="off")
    class_id = models.PositiveIntegerField(default=0)
    requested_by = models.CharField(max_length=150, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    requested_duration_minutes = models.PositiveIntegerField(default=0)
    provider_request_id = models.CharField(max_length=120, blank=True)
    lease_session_id = models.PositiveBigIntegerField(default=0)
    status_detail = models.CharField(max_length=160, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_readiness_reason_code = models.CharField(max_length=80, blank=True)
    last_transition_at = models.DateTimeField(null=True, blank=True)
    last_healthcheck_at = models.DateTimeField(null=True, blank=True)
    last_ready_probe_at = models.DateTimeField(null=True, blank=True)
    last_ready_probe_ok_at = models.DateTimeField(null=True, blank=True)
    last_routed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class RemoteComputeClassMetric(models.Model):
    """Durable per-class remote helper accounting summary."""

    class_id = models.PositiveIntegerField(unique=True)
    activation_count = models.PositiveIntegerField(default=0)
    ready_transition_count = models.PositiveIntegerField(default=0)
    cumulative_ready_seconds = models.PositiveIntegerField(default=0)
    remote_route_count = models.PositiveIntegerField(default=0)
    fallback_local_count = models.PositiveIntegerField(default=0)
    degraded_transition_count = models.PositiveIntegerField(default=0)
    provider_unreachable_count = models.PositiveIntegerField(default=0)
    unused_activation_count = models.PositiveIntegerField(default=0)
    last_activation_at = models.DateTimeField(null=True, blank=True)
    last_ready_at = models.DateTimeField(null=True, blank=True)
    last_fallback_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class RemoteComputeLeaseSession(models.Model):
    """Per-activation remote helper lease evidence row."""

    class_id = models.PositiveIntegerField(db_index=True)
    requested_by = models.CharField(max_length=150, blank=True)
    requested_at = models.DateTimeField(default=timezone.now, db_index=True)
    requested_duration_minutes = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    provider_label = models.CharField(max_length=80, blank=True)
    provider_adapter = models.CharField(max_length=80, blank=True)
    provider_request_id = models.CharField(max_length=120, blank=True, db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    current_state = models.CharField(max_length=32, default="requested", db_index=True)
    last_transition_at = models.DateTimeField(default=timezone.now)
    last_healthcheck_at = models.DateTimeField(null=True, blank=True)
    last_ready_probe_at = models.DateTimeField(null=True, blank=True)
    last_ready_probe_ok_at = models.DateTimeField(null=True, blank=True)
    first_ready_at = models.DateTimeField(null=True, blank=True)
    last_routed_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_readiness_reason_code = models.CharField(max_length=80, blank=True)
    last_fallback_reason_code = models.CharField(max_length=80, blank=True)
    status_detail = models.CharField(max_length=160, blank=True)
    starting_seconds = models.PositiveIntegerField(default=0)
    ready_seconds = models.PositiveIntegerField(default=0)
    degraded_seconds = models.PositiveIntegerField(default=0)
    leased_minutes = models.PositiveIntegerField(default=0)
    manual_stop_count = models.PositiveIntegerField(default=0)
    auto_stop_count = models.PositiveIntegerField(default=0)
    remote_route_count = models.PositiveIntegerField(default=0)
    fallback_local_count = models.PositiveIntegerField(default=0)
    estimated_cost_per_hour_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-requested_at", "-id")

    def estimated_cost_usd(self) -> Decimal | None:
        if self.estimated_cost_per_hour_usd in (None, ""):
            return None
        if int(self.leased_minutes or 0) <= 0:
            return Decimal("0.00")
        hourly = Decimal(self.estimated_cost_per_hour_usd)
        return (hourly * Decimal(self.leased_minutes) / Decimal(60)).quantize(Decimal("0.01"))


class RemoteComputeLeaseEvent(models.Model):
    """Small transition/fallback audit trail for conference-grade evidence."""

    lease_session = models.ForeignKey(
        RemoteComputeLeaseSession,
        on_delete=models.CASCADE,
        related_name="events",
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    event_type = models.CharField(max_length=48)
    from_state = models.CharField(max_length=32, blank=True)
    to_state = models.CharField(max_length=32, blank=True)
    reason_code = models.CharField(max_length=80, blank=True)
    detail = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ("-occurred_at", "-id")
