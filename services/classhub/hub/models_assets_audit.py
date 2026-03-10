"""Lesson asset, certificate, and audit models extracted from hub.models."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .model_helpers import (
    gen_certificate_code,
    _lesson_asset_upload_to,
    _lesson_video_upload_to,
    _normalize_asset_folder_path,
)


class CertificateIssuance(models.Model):
    """Teacher-issued certificate record for one student in one class."""

    classroom = models.ForeignKey("Class", on_delete=models.CASCADE, related_name="certificate_issuances")
    student = models.ForeignKey("StudentIdentity", on_delete=models.CASCADE, related_name="certificate_issuances")
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_certificates",
    )
    code = models.CharField(max_length=24, unique=True, default=gen_certificate_code)
    signed_token = models.TextField(blank=True, default="")
    session_count = models.PositiveIntegerField(default=0)
    artifact_count = models.PositiveIntegerField(default=0)
    milestone_count = models.PositiveIntegerField(default=0)
    min_sessions_required = models.PositiveIntegerField(default=1)
    min_artifacts_required = models.PositiveIntegerField(default=1)
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "student"],
                name="uniq_certificate_per_student_class",
            ),
        ]
        indexes = [
            models.Index(fields=["classroom", "issued_at"], name="hub_cert_clsiss_1d1b_idx"),
            models.Index(fields=["student", "issued_at"], name="hub_cert_stuiss_67e4_idx"),
        ]

    def __str__(self) -> str:
        return f"Certificate {self.code} ({self.student.display_name})"


class LessonAssetFolder(models.Model):
    """Teacher-managed folder namespace for reference assets."""

    path = models.CharField(max_length=200, unique=True, default="general")
    display_name = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["path", "id"]

    def save(self, *args, **kwargs):
        self.path = _normalize_asset_folder_path(self.path)
        if not self.display_name:
            self.display_name = self.path
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.path


class LessonVideo(models.Model):
    """Teacher-managed video asset tagged to one course lesson."""

    course_slug = models.SlugField(max_length=120)
    lesson_slug = models.SlugField(max_length=120)
    title = models.CharField(max_length=200)
    minutes = models.PositiveIntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=300, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    video_file = models.FileField(upload_to=_lesson_video_upload_to, blank=True, null=True)
    order_index = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_index", "id"]
        indexes = [
            models.Index(
                fields=["course_slug", "lesson_slug", "is_active"],
                name="hub_lessonv_course__be98cb_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course_slug}/{self.lesson_slug}: {self.title}"


class LessonRelease(models.Model):
    """Per-class release overrides for lesson availability."""

    classroom = models.ForeignKey("Class", on_delete=models.CASCADE, related_name="lesson_releases")
    course_slug = models.SlugField(max_length=120)
    lesson_slug = models.SlugField(max_length=120)
    available_on = models.DateField(blank=True, null=True)
    force_locked = models.BooleanField(default=False)
    helper_context_override = models.CharField(max_length=200, blank=True, default="")
    helper_topics_override = models.TextField(blank=True, default="")
    helper_allowed_topics_override = models.TextField(blank=True, default="")
    helper_reference_override = models.CharField(max_length=200, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "course_slug", "lesson_slug"],
                name="uniq_lesson_release_per_class_lesson",
            ),
        ]
        indexes = [
            models.Index(
                fields=["classroom", "course_slug", "lesson_slug"],
                name="hub_lessonr_classro_0a0884_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.classroom.join_code}:{self.course_slug}/{self.lesson_slug}"


class LessonAsset(models.Model):
    """Teacher-managed reference file that can be linked inside lesson markdown."""

    folder = models.ForeignKey("LessonAssetFolder", on_delete=models.PROTECT, related_name="assets")
    course_slug = models.SlugField(max_length=120, blank=True, default="")
    lesson_slug = models.SlugField(max_length=120, blank=True, default="")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=_lesson_asset_upload_to)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        indexes = [
            models.Index(fields=["folder", "is_active"], name="hub_lessona_folder__764626_idx"),
            models.Index(
                fields=["course_slug", "lesson_slug", "is_active"],
                name="hub_lessona_course__7a0ed8_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.folder.path}: {self.title}"


class AuditEvent(models.Model):
    """Immutable staff-action record for operations and incident review."""

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hub_audit_events",
    )
    classroom = models.ForeignKey(
        "Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    summary = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_at"], name="hub_auditev_created_d7d36a_idx"),
            models.Index(fields=["action", "created_at"], name="hub_auditev_action__2026ec_idx"),
            models.Index(fields=["classroom", "created_at"], name="hub_auditev_classro_04f2a6_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.created_at.isoformat()} {self.action} {self.target_type}:{self.target_id}"


__all__ = [
    "AuditEvent",
    "CertificateIssuance",
    "LessonAsset",
    "LessonAssetFolder",
    "LessonRelease",
    "LessonVideo",
]
