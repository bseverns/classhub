"""Data model for the MVP.

Teachers/admins can manage these objects in Django admin.
Students never authenticate with email/password; they join a class by code.

Note: for Day-1, we keep the model tiny. As the platform grows, add:
- Rubrics/grading + teacher feedback
"""

import re
import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from django.conf import settings
from django.db import models
from django.utils import timezone


def gen_class_code(length: int = 8) -> str:
    """Generate a human-friendly class code.

    Excludes ambiguous characters (0/O, 1/I).
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_student_return_code(length: int = 6) -> str:
    """Generate a short student return code.

    This is shown to students so they can reclaim their identity after cookie loss.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_student_invite_token(length: int = 24) -> str:
    """Generate a URL-safe invite token."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Class(models.Model):
    """A classroom roster with one join code.

    Non-technical framing:
    - Think of this as one class period/section.
    - `is_locked=True` temporarily blocks new student joins.
    """

    ENROLLMENT_OPEN = "open"
    ENROLLMENT_INVITE_ONLY = "invite_only"
    ENROLLMENT_CLOSED = "closed"
    ENROLLMENT_MODE_CHOICES = [
        (ENROLLMENT_OPEN, "Open"),
        (ENROLLMENT_INVITE_ONLY, "Invite only"),
        (ENROLLMENT_CLOSED, "Closed"),
    ]

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes",
    )
    name = models.CharField(max_length=200)
    join_code = models.CharField(max_length=16, unique=True, default=gen_class_code)
    enrollment_mode = models.CharField(
        max_length=20,
        choices=ENROLLMENT_MODE_CHOICES,
        default=ENROLLMENT_OPEN,
    )
    is_locked = models.BooleanField(default=False)
    # Increment to invalidate active student sessions without rotating database IDs.
    session_epoch = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.name} ({self.join_code})"


class Organization(models.Model):
    """Top-level tenant boundary for programs/cohorts."""

    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class OrganizationMembership(models.Model):
    """Staff role assignment scoped to one organization."""

    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_TEACHER = "teacher"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_TEACHER, "Teacher"),
        (ROLE_VIEWER, "Viewer"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classhub_organization_memberships",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_TEACHER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="uniq_org_membership_user",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "role", "is_active"], name="hub_orgmem_orgrol_86ee_idx"),
            models.Index(fields=["user", "is_active"], name="hub_orgmem_usract_2129_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.user} ({self.role})"


class Module(models.Model):
    """An ordered group of materials (usually one lesson/session)."""

    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self) -> str:
        return f"{self.classroom.name}: {self.title}"


class Material(models.Model):
    """A single item shown to students inside a module.

    Types:
    - link: points to lesson/content URL
    - text: short instructions/reminders
    - upload: student dropbox for file submission
    """

    TYPE_LINK = "link"
    TYPE_TEXT = "text"
    TYPE_UPLOAD = "upload"
    TYPE_CHOICES = [
        (TYPE_LINK, "Link"),
        (TYPE_TEXT, "Text"),
        (TYPE_UPLOAD, "Upload"),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_LINK)

    # For link material
    url = models.URLField(blank=True, default="")

    # For text material
    body = models.TextField(blank=True, default="")

    # For upload material
    # Comma-separated list of extensions (including the leading dot), e.g. ".sb3,.png"
    accepted_extensions = models.CharField(max_length=200, blank=True, default="")
    max_upload_mb = models.PositiveIntegerField(default=50)

    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self) -> str:
        return self.title


def _submission_upload_to(instance: "Submission", filename: str) -> str:
    """Upload path for student submissions.

    We keep paths boring and segregated by class + material.
    """
    ext = Path(str(filename or "")).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,16}", ext or ""):
        ext = ""
    stored_name = f"{secrets.token_hex(16)}{ext}"

    classroom_id = instance.material.module.classroom_id
    material_id = instance.material_id
    student_id = instance.student_id
    return f"submissions/class_{classroom_id}/material_{material_id}/student_{student_id}/{stored_name}"


class Submission(models.Model):
    """A student file upload tied to a specific Material.

    Students do not have accounts; we tie this to StudentIdentity (stored in session).
    """

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("StudentIdentity", on_delete=models.CASCADE, related_name="submissions")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=_submission_upload_to)
    note = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        indexes = [
            models.Index(fields=["material", "uploaded_at"], name="hub_submis_matup_2a3bf4_idx"),
            models.Index(fields=["student", "uploaded_at"], name="hub_submiss_student_4f0ac8_idx"),
            models.Index(fields=["material", "student"], name="hub_submis_matstu_91b9f2_idx"),
        ]

    def __str__(self) -> str:
        return f"Submission {self.id} ({self.student.display_name} → {self.material.title})"


class StudentIdentity(models.Model):
    """A pseudonymous identity stored per-class.

    Created when a student joins via class code.
    The id is stored in the session cookie.
    """

    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="students")
    display_name = models.CharField(max_length=80)
    return_code = models.CharField(max_length=12, default=gen_student_return_code)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Return code only needs to be unique inside one class.
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "return_code"],
                name="uniq_student_return_code_per_class",
            ),
        ]
        # Speeds up joins/searches by class + display name/return code.
        indexes = [
            models.Index(fields=["classroom", "display_name"], name="hub_studeni_classro_11dfba_idx"),
            models.Index(fields=["classroom", "return_code"], name="hub_studeni_classro_3c11ef_idx"),
            models.Index(fields=["classroom", "created_at"], name="hub_studid_clscrt_a1d2_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} @ {self.classroom.join_code}"


class ClassInviteLink(models.Model):
    """Teacher-generated student invite bridge with optional expiry and seat cap."""

    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="invite_links")
    token = models.CharField(max_length=48, unique=True, default=gen_student_invite_token)
    label = models.CharField(max_length=120, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_invites_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["classroom", "is_active"], name="hub_clsinv_clsact_93d2_idx"),
            models.Index(fields=["classroom", "created_at"], name="hub_clsinv_clscrt_5d9a_idx"),
            models.Index(fields=["expires_at"], name="hub_clsinv_exp_a2e1_idx"),
        ]

    def is_expired(self, *, at=None) -> bool:
        when = at or timezone.now()
        return bool(self.expires_at and self.expires_at <= when)

    def has_seat_available(self) -> bool:
        if self.max_uses is None:
            return True
        return int(self.use_count or 0) < int(self.max_uses or 0)

    def is_usable(self, *, at=None) -> bool:
        return bool(self.is_active and not self.is_expired(at=at) and self.has_seat_available())

    def seats_remaining(self) -> int | None:
        if self.max_uses is None:
            return None
        return max(int(self.max_uses) - int(self.use_count or 0), 0)

    def __str__(self) -> str:
        return f"Invite #{self.id} for class {self.classroom_id}"


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
    EVENT_HELPER_CHAT_ACCESS = "helper_chat_access"

    EVENT_TYPE_CHOICES = [
        (EVENT_CLASS_JOIN, "Class join"),
        (EVENT_REJOIN_DEVICE_HINT, "Session rejoin (device hint)"),
        (EVENT_REJOIN_RETURN_CODE, "Session rejoin (return code)"),
        (EVENT_SUBMISSION_UPLOAD, "Submission upload"),
        (EVENT_HELPER_CHAT_ACCESS, "Helper chat access"),
    ]

    classroom = models.ForeignKey(
        Class,
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


def _safe_path_part(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", (raw or "").strip().lower())
    value = value.strip("-")
    return value or "unknown"


def _lesson_video_upload_to(instance: "LessonVideo", filename: str) -> str:
    course = _safe_path_part(instance.course_slug)
    lesson = _safe_path_part(instance.lesson_slug)
    return f"lesson_videos/{course}/{lesson}/{filename}"


def _normalize_asset_folder_path(raw: str) -> str:
    parts = []
    for segment in str(raw or "").replace("\\", "/").split("/"):
        segment = segment.strip()
        if not segment:
            continue
        parts.append(_safe_path_part(segment))
    return "/".join(parts) or "general"


def _safe_asset_filename(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", (raw or "").strip())
    value = value.strip("._")
    return value or "asset"


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


def _lesson_asset_upload_to(instance: "LessonAsset", filename: str) -> str:
    folder_path = _normalize_asset_folder_path(getattr(instance.folder, "path", "general"))
    return f"lesson_assets/{folder_path}/{_safe_asset_filename(filename)}"


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
    """Per-class release overrides for lesson availability.

    Priority:
    - `force_locked=True` always locks
    - else `available_on` can schedule open date
    - else lesson uses markdown/content defaults
    """

    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="lesson_releases")
    course_slug = models.SlugField(max_length=120)
    lesson_slug = models.SlugField(max_length=120)
    # If set, students are locked until this date in the classroom.
    available_on = models.DateField(blank=True, null=True)
    # Hard lock regardless of date (until toggled off by teacher/admin).
    force_locked = models.BooleanField(default=False)
    # Optional helper-scope overrides for this class + lesson.
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

    folder = models.ForeignKey(LessonAssetFolder, on_delete=models.PROTECT, related_name="assets")
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
        Class,
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
