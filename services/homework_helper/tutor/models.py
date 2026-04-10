from django.db import models


class RemoteComputeLeaseRecord(models.Model):
    """Durable singleton row for the active remote helper lease."""

    slot = models.CharField(max_length=32, primary_key=True, default="active", editable=False)
    state = models.CharField(max_length=32, default="off")
    class_id = models.PositiveIntegerField(default=0)
    requested_by = models.CharField(max_length=150, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    provider_request_id = models.CharField(max_length=120, blank=True)
    status_detail = models.CharField(max_length=160, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_transition_at = models.DateTimeField(null=True, blank=True)
    last_healthcheck_at = models.DateTimeField(null=True, blank=True)
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

