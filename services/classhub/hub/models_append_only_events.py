"""Append-only event models extracted from hub.models."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models


_STUDENT_EVENT_DELETE_ALLOWED = ContextVar("hub_student_event_delete_allowed", default=False)


def _student_event_delete_allowed() -> bool:
    return bool(_STUDENT_EVENT_DELETE_ALLOWED.get())


class StudentEventQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        if not _student_event_delete_allowed():
            raise ValueError("StudentEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)


class StudentEventManager(models.Manager.from_queryset(StudentEventQuerySet)):
    pass


class StudentEvent(models.Model):
    """Append-only student activity stream for operational visibility.

    Privacy boundary:
    - Keep this event log metadata-only (IDs, modes, status, timing).
    - Do not store raw helper prompts or submission file contents.
    """

    EVENT_CLASS_JOIN = "class_join"
    EVENT_REJOIN_DEVICE_HINT = "session_rejoin_device_hint"
    EVENT_REJOIN_RETURN_CODE = "session_rejoin_return_code"
    EVENT_SUBMISSION_UPLOAD = "submission_upload"
    EVENT_SUBMISSION_UPLOAD_ERROR = "submission_upload_error"
    EVENT_HELPER_CHAT_ACCESS = "helper_chat_access"
    EVENT_MICRO_CHECK_CAN_DO_THIS = "micro_check_can_do_this"
    EVENT_MICRO_CHECK_STUCK = "micro_check_stuck"
    EVENT_MICRO_CHECK_TAUGHT_SOMEONE = "micro_check_taught_someone"
    EVENT_MICRO_CHECK_STUCK_RESOLVED = "micro_check_stuck_resolved"
    EVENT_STUDENT_DELETE_WORK_REQUEST = "student_delete_work_request"
    EVENT_STUDENT_DELETE_WORK_REQUEST_RESOLVED = "student_delete_work_request_resolved"

    EVENT_TYPE_CHOICES = [
        (EVENT_CLASS_JOIN, "Class join"),
        (EVENT_REJOIN_DEVICE_HINT, "Session rejoin (device hint)"),
        (EVENT_REJOIN_RETURN_CODE, "Session rejoin (return code)"),
        (EVENT_SUBMISSION_UPLOAD, "Submission upload"),
        (EVENT_HELPER_CHAT_ACCESS, "Helper chat access"),
    ]

    classroom = models.ForeignKey(
        "Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_events",
    )
    student = models.ForeignKey(
        "StudentIdentity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    event_type = models.CharField(max_length=48, choices=EVENT_TYPE_CHOICES)
    source = models.CharField(max_length=40, default="classhub")
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["event_type", "created_at"], name="hub_student_event_t_387746_idx"),
            models.Index(fields=["classroom", "created_at"], name="hub_student_classro_a0c234_idx"),
            models.Index(fields=["student", "created_at"], name="hub_student_student_01e0d2_idx"),
            models.Index(fields=["classroom", "event_type", "created_at"], name="hub_ste_cl_evtcr_b2e3_idx"),
        ]

    objects = StudentEventManager()

    @classmethod
    @contextmanager
    def allow_retention_delete(cls):
        token = _STUDENT_EVENT_DELETE_ALLOWED.set(True)
        try:
            yield
        finally:
            _STUDENT_EVENT_DELETE_ALLOWED.reset(token)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("StudentEvent is append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not _student_event_delete_allowed():
            raise ValueError("StudentEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.created_at.isoformat()} {self.event_type}"


_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED = ContextVar("hub_student_outcome_event_delete_allowed", default=False)


def _student_outcome_event_delete_allowed() -> bool:
    return bool(_STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.get())


class StudentOutcomeEventQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        if not _student_outcome_event_delete_allowed():
            raise ValueError("StudentOutcomeEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)


class StudentOutcomeEventManager(models.Manager.from_queryset(StudentOutcomeEventQuerySet)):
    pass


class StudentOutcomeEvent(models.Model):
    """Append-only student outcomes stream for certificates/reporting."""

    EVENT_SESSION_COMPLETED = "session_completed"
    EVENT_ARTIFACT_SUBMITTED = "artifact_submitted"
    EVENT_MILESTONE_EARNED = "milestone_earned"
    EVENT_TYPE_CHOICES = [
        (EVENT_SESSION_COMPLETED, "Session completed"),
        (EVENT_ARTIFACT_SUBMITTED, "Artifact submitted"),
        (EVENT_MILESTONE_EARNED, "Milestone earned"),
    ]

    classroom = models.ForeignKey(
        "Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_outcome_events",
    )
    student = models.ForeignKey(
        "StudentIdentity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outcome_events",
    )
    module = models.ForeignKey(
        "Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_outcome_events",
    )
    material = models.ForeignKey(
        "Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_outcome_events",
    )
    event_type = models.CharField(max_length=40, choices=EVENT_TYPE_CHOICES)
    source = models.CharField(max_length=40, default="classhub")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["classroom", "event_type", "created_at"], name="hub_stout_cl_evt_cra_idx"),
            models.Index(fields=["student", "event_type", "created_at"], name="hub_stout_st_evt_cra_idx"),
            models.Index(fields=["module", "event_type", "created_at"], name="hub_stout_mod_evt_cra_idx"),
        ]

    objects = StudentOutcomeEventManager()

    @classmethod
    @contextmanager
    def allow_retention_delete(cls):
        token = _STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.set(True)
        try:
            yield
        finally:
            _STUDENT_OUTCOME_EVENT_DELETE_ALLOWED.reset(token)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("StudentOutcomeEvent is append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not _student_outcome_event_delete_allowed():
            raise ValueError("StudentOutcomeEvent deletion is restricted to retention workflows.")
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.created_at.isoformat()} {self.event_type}"


__all__ = [
    "StudentEvent",
    "StudentEventManager",
    "StudentEventQuerySet",
    "StudentOutcomeEvent",
    "StudentOutcomeEventManager",
    "StudentOutcomeEventQuerySet",
]
