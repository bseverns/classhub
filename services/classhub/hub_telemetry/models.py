"""Telemetry-native append-only event models for split DB rollout."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models
from django.utils import timezone


_TELEMETRY_STUDENT_EVENT_DELETE_ALLOWED = ContextVar(
    "hub_telemetry_student_event_delete_allowed",
    default=False,
)
_TELEMETRY_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED = ContextVar(
    "hub_telemetry_student_outcome_event_delete_allowed",
    default=False,
)


def _telemetry_student_event_delete_allowed() -> bool:
    return bool(_TELEMETRY_STUDENT_EVENT_DELETE_ALLOWED.get())


def _telemetry_student_outcome_event_delete_allowed() -> bool:
    return bool(_TELEMETRY_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.get())


class TelemetryStudentEventQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        if not _telemetry_student_event_delete_allowed():
            raise ValueError("TelemetryStudentEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)


class TelemetryStudentOutcomeEventQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        if not _telemetry_student_outcome_event_delete_allowed():
            raise ValueError("TelemetryStudentOutcomeEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)


class TelemetryStudentEvent(models.Model):
    """Append-only telemetry event stream with scalar references only."""

    core_event_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    classroom_id = models.PositiveBigIntegerField(null=True, blank=True)
    student_id = models.PositiveBigIntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=48)
    source = models.CharField(max_length=40, default="classhub")
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["event_type", "created_at"], name="hbtm_evt_type_crt_idx"),
            models.Index(fields=["classroom_id", "created_at"], name="hbtm_evt_cls_crt_idx"),
            models.Index(fields=["student_id", "created_at"], name="hbtm_evt_stu_crt_idx"),
            models.Index(fields=["classroom_id", "event_type", "created_at"], name="hbtm_evt_clstypcrt_idx"),
        ]

    objects = TelemetryStudentEventQuerySet.as_manager()

    @classmethod
    @contextmanager
    def allow_retention_delete(cls):
        token = _TELEMETRY_STUDENT_EVENT_DELETE_ALLOWED.set(True)
        try:
            yield
        finally:
            _TELEMETRY_STUDENT_EVENT_DELETE_ALLOWED.reset(token)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("TelemetryStudentEvent is append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not _telemetry_student_event_delete_allowed():
            raise ValueError("TelemetryStudentEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)


class TelemetryStudentOutcomeEvent(models.Model):
    """Append-only telemetry outcomes stream with scalar references only."""

    core_outcome_event_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    classroom_id = models.PositiveBigIntegerField(null=True, blank=True)
    student_id = models.PositiveBigIntegerField(null=True, blank=True)
    module_id = models.PositiveBigIntegerField(null=True, blank=True)
    material_id = models.PositiveBigIntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=40)
    source = models.CharField(max_length=40, default="classhub")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["classroom_id", "event_type", "created_at"], name="hbtm_out_clstypcrt_idx"),
            models.Index(fields=["student_id", "event_type", "created_at"], name="hbtm_out_stutypcrt_idx"),
            models.Index(fields=["module_id", "event_type", "created_at"], name="hbtm_out_modtypcrt_idx"),
        ]

    objects = TelemetryStudentOutcomeEventQuerySet.as_manager()

    @classmethod
    @contextmanager
    def allow_retention_delete(cls):
        token = _TELEMETRY_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.set(True)
        try:
            yield
        finally:
            _TELEMETRY_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.reset(token)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("TelemetryStudentOutcomeEvent is append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not _telemetry_student_outcome_event_delete_allowed():
            raise ValueError("TelemetryStudentOutcomeEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)
