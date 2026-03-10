"""Data model for the MVP.

Teachers/admins can manage these objects in Django admin.
Students never authenticate with email/password; they join a class by code.

Note: for Day-1, we keep the model tiny. As the platform grows, add:
- Rubrics/grading + teacher feedback
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .model_helpers import (
    gen_certificate_code,
    gen_class_code,
    gen_student_invite_token,
    gen_student_return_code,
    _lesson_asset_upload_to,
    _lesson_video_upload_to,
    _normalize_asset_folder_path,
    _safe_asset_filename,
    _safe_path_part,
    _submission_upload_to,
)


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
    RETENTION_ERASE_7_DAYS = "erase_after_7_days"
    RETENTION_KEEP_SEMESTER = "keep_for_semester"
    RETENTION_KEEP_UNTIL_STUDENT_DELETES = "keep_until_student_deletes"
    RETENTION_PRESET_CHOICES = [
        (RETENTION_ERASE_7_DAYS, "Erase after 7 days"),
        (RETENTION_KEEP_SEMESTER, "Keep for semester"),
        (RETENTION_KEEP_UNTIL_STUDENT_DELETES, "Keep portfolio until student deletes"),
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
    student_landing_title = models.CharField(max_length=200, blank=True, default="")
    student_landing_message = models.TextField(blank=True, default="")
    # Accept either an absolute URL or a same-origin path (for /lesson-asset/*).
    student_landing_hero_url = models.CharField(max_length=500, blank=True, default="")
    enrollment_mode = models.CharField(
        max_length=20,
        choices=ENROLLMENT_MODE_CHOICES,
        default=ENROLLMENT_OPEN,
    )
    retention_preset = models.CharField(
        max_length=40,
        choices=RETENTION_PRESET_CHOICES,
        default=RETENTION_ERASE_7_DAYS,
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


class OrganizationRoleCapability(models.Model):
    """Per-organization role capability template override.

    Behavior:
    - If a role has one or more active rows in an organization, those rows
      define the effective capabilities for that role in that organization.
    - If a role has no active rows, default role capability mapping applies.
    """

    CAP_CLASS_VIEW = "class.view"
    CAP_CLASS_MANAGE = "class.manage"
    CAP_CLASS_CREATE = "class.create"
    CAP_ROSTER_MANAGE = "roster.manage"
    CAP_SUBMISSION_VIEW = "submission.view"
    CAP_SUBMISSION_DELETE = "submission.delete"
    CAP_POLICY_MANAGE = "policy.manage"
    CAP_SYLLABUS_EXPORT = "syllabus.export"
    CAPABILITY_CHOICES = [
        (CAP_CLASS_VIEW, "Class view"),
        (CAP_CLASS_MANAGE, "Class manage"),
        (CAP_CLASS_CREATE, "Class create"),
        (CAP_ROSTER_MANAGE, "Roster manage"),
        (CAP_SUBMISSION_VIEW, "Submission view"),
        (CAP_SUBMISSION_DELETE, "Submission delete"),
        (CAP_POLICY_MANAGE, "Policy manage"),
        (CAP_SYLLABUS_EXPORT, "Syllabus export"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="role_capabilities",
    )
    role = models.CharField(max_length=20, choices=OrganizationMembership.ROLE_CHOICES)
    capability = models.CharField(max_length=40, choices=CAPABILITY_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "role", "capability"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "role", "capability"],
                name="uniq_org_role_capability",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "role", "is_active"], name="hub_orgrole_orgrol_1f5a_idx"),
            models.Index(fields=["organization", "capability", "is_active"], name="hub_orgrole_orgcap_79bc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.role} -> {self.capability}"


class OrganizationCustomRole(models.Model):
    """First-class organization-scoped custom role entity."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="custom_roles",
    )
    slug = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "slug", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="uniq_org_custom_role_slug",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="hub_crole_orgact_9f33_idx"),
            models.Index(fields=["organization", "slug"], name="hub_crole_orgslug_2f3b_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.slug}"


class OrganizationCustomRoleCapability(models.Model):
    """Capability membership for a custom role."""

    role = models.ForeignKey(
        OrganizationCustomRole,
        on_delete=models.CASCADE,
        related_name="capabilities",
    )
    capability = models.CharField(
        max_length=40,
        choices=OrganizationRoleCapability.CAPABILITY_CHOICES,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role_id", "capability", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "capability"],
                name="uniq_custom_role_capability",
            ),
        ]
        indexes = [
            models.Index(fields=["role", "is_active"], name="hub_crolecap_roleac_20bb_idx"),
            models.Index(fields=["capability", "is_active"], name="hub_crolecap_capact_7d3c_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role} -> {self.capability}"


class OrganizationCustomRoleAssignment(models.Model):
    """Assign one custom role to one staff user inside one organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="custom_role_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classhub_custom_role_assignments",
    )
    role = models.ForeignKey(
        OrganizationCustomRole,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "user_id", "role_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "role"],
                name="uniq_org_custom_role_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "user", "is_active"], name="hub_croleasg_orgusr_514f_idx"),
            models.Index(fields=["role", "is_active"], name="hub_croleasg_roleac_c050_idx"),
        ]

    def clean(self):
        super().clean()
        if self.organization_id and self.role_id:
            role_org_id = getattr(self.role, "organization_id", None)
            if role_org_id is not None and int(role_org_id) != int(self.organization_id):
                raise ValidationError({"organization": "Organization must match custom role organization."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.user} -> {self.role.slug}"


class RbacPolicyChangeRequest(models.Model):
    """Approval workflow record for high-impact RBAC policy mutations."""

    REQUEST_SCOPE_GRANT_UPSERT = "scope_grant_upsert"
    REQUEST_SCOPE_GRANT_SET_ACTIVE = "scope_grant_set_active"
    REQUEST_CUSTOM_ROLE_UPSERT = "custom_role_upsert"
    REQUEST_CUSTOM_ROLE_CAPABILITY_UPSERT = "custom_role_capability_upsert"
    REQUEST_CUSTOM_ROLE_ASSIGNMENT_UPSERT = "custom_role_assignment_upsert"
    REQUEST_POLICY_IMPORT = "policy_import"
    REQUEST_TYPE_CHOICES = [
        (REQUEST_SCOPE_GRANT_UPSERT, "Scoped grant upsert"),
        (REQUEST_SCOPE_GRANT_SET_ACTIVE, "Scoped grant set active"),
        (REQUEST_CUSTOM_ROLE_UPSERT, "Custom role upsert"),
        (REQUEST_CUSTOM_ROLE_CAPABILITY_UPSERT, "Custom role capability upsert"),
        (REQUEST_CUSTOM_ROLE_ASSIGNMENT_UPSERT, "Custom role assignment upsert"),
        (REQUEST_POLICY_IMPORT, "Policy import"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    request_type = models.CharField(max_length=64, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classhub_rbac_policy_change_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classhub_rbac_policy_change_reviews",
    )
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rbac_policy_change_requests",
    )
    classroom = models.ForeignKey(
        "Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rbac_policy_change_requests",
    )
    summary = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    review_note = models.CharField(max_length=500, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="hub_rbacreq_statcrt_c17a_idx"),
            models.Index(fields=["request_type", "status"], name="hub_rbacreq_typsta_d522_idx"),
            models.Index(fields=["organization", "status"], name="hub_rbacreq_orgsta_7ba7_idx"),
            models.Index(fields=["classroom", "status"], name="hub_rbacreq_clssta_8a2b_idx"),
            models.Index(fields=["requested_by", "status"], name="hub_rbacreq_usrsta_5f3e_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.request_type} ({self.status}) #{self.id}"


class ClassStaffAssignment(models.Model):
    """Explicit class assignment for staff prioritization and ownership views."""

    classroom = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classhub_class_assignments",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["classroom_id", "user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "user"],
                name="uniq_class_staff_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["classroom", "is_active"], name="hub_clsasg_clsact_91f3_idx"),
            models.Index(fields=["user", "is_active"], name="hub_clsasg_usract_b03a_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.classroom.name}: {self.user}"


class ClassStaffModuleScopeGrant(models.Model):
    """Optional module-range capability grant for one staff user in one class."""

    CAP_SUBMISSION_VIEW = "submission.view"
    CAP_SUBMISSION_DELETE = "submission.delete"
    CAP_ROSTER_MANAGE = "roster.manage"
    CAP_POLICY_MANAGE = "policy.manage"
    EFFECT_ALLOW = "allow"
    EFFECT_DENY = "deny"
    CAPABILITY_CHOICES = [
        (CAP_SUBMISSION_VIEW, "Submission view"),
        (CAP_SUBMISSION_DELETE, "Submission delete"),
        (CAP_ROSTER_MANAGE, "Roster manage"),
        (CAP_POLICY_MANAGE, "Policy manage"),
    ]
    EFFECT_CHOICES = [
        (EFFECT_ALLOW, "Allow"),
        (EFFECT_DENY, "Deny"),
    ]

    classroom = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="staff_module_scope_grants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classhub_module_scope_grants",
    )
    capability = models.CharField(max_length=40, choices=CAPABILITY_CHOICES)
    effect = models.CharField(max_length=16, choices=EFFECT_CHOICES, default=EFFECT_ALLOW)
    module_order_start = models.PositiveIntegerField(default=0)
    module_order_end = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["classroom_id", "user_id", "capability", "module_order_start", "module_order_end", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "user", "capability", "effect", "module_order_start", "module_order_end"],
                name="uniq_staff_module_scope_effect_grant",
            ),
            models.CheckConstraint(
                check=models.Q(module_order_end__gte=models.F("module_order_start")),
                name="staff_module_scope_order_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["classroom", "user", "capability", "effect", "is_active"],
                name="hub_stmodgr_clsusr_cap_idx",
            ),
            models.Index(
                fields=["classroom", "capability", "effect", "module_order_start", "module_order_end"],
                name="hub_stmodgr_scope_rng_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.classroom.name}: {self.user} {self.effect} {self.capability} "
            f"[{self.module_order_start}-{self.module_order_end}]"
        )


class Module(models.Model):
    """An ordered group of materials (usually one lesson/session)."""

    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order_index = models.PositiveIntegerField(default=0)
    gallery_enabled = models.BooleanField(default=True)

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
    - gallery: upload with optional class-visible sharing
    - checklist: student self-report checklist
    - reflection: private journal prompt/response
    - rubric: criterion ratings + optional feedback
    """

    TYPE_LINK = "link"
    TYPE_TEXT = "text"
    TYPE_UPLOAD = "upload"
    TYPE_GALLERY = "gallery"
    TYPE_CHECKLIST = "checklist"
    TYPE_REFLECTION = "reflection"
    TYPE_RUBRIC = "rubric"
    TYPE_CHOICES = [
        (TYPE_LINK, "Link"),
        (TYPE_TEXT, "Text"),
        (TYPE_UPLOAD, "Upload"),
        (TYPE_GALLERY, "Gallery"),
        (TYPE_CHECKLIST, "Checklist"),
        (TYPE_REFLECTION, "Reflection"),
        (TYPE_RUBRIC, "Rubric"),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_LINK)

    # For link material
    url = models.URLField(blank=True, default="")

    # For text material
    body = models.TextField(blank=True, default="")
    rubric_scale_max = models.PositiveSmallIntegerField(default=4)

    # For upload material
    # Comma-separated list of extensions (including the leading dot), e.g. ".sb3,.png"
    accepted_extensions = models.CharField(max_length=200, blank=True, default="")
    max_upload_mb = models.PositiveIntegerField(default=50)

    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self) -> str:
        return self.title

class Submission(models.Model):
    """A student file upload tied to a specific Material.

    Students do not have accounts; we tie this to StudentIdentity (stored in session).
    """

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("StudentIdentity", on_delete=models.CASCADE, related_name="submissions")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=_submission_upload_to)
    note = models.TextField(blank=True, default="")
    is_gallery_shared = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    remix_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remixes",
    )
    process_note = models.TextField(blank=True, default="")
    station_label = models.CharField(max_length=80, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        indexes = [
            models.Index(fields=["material", "uploaded_at"], name="hub_submis_matup_2a3bf4_idx"),
            models.Index(fields=["student", "uploaded_at"], name="hub_submiss_student_4f0ac8_idx"),
            models.Index(fields=["material", "student"], name="hub_submis_matstu_91b9f2_idx"),
            models.Index(fields=["material", "is_gallery_shared", "uploaded_at"], name="hub_submis_matshr_90a5_idx"),
            models.Index(fields=["material", "is_published", "published_at"], name="hub_submis_matpub_f4b5_idx"),
        ]

    def __str__(self) -> str:
        return f"Submission {self.id} ({self.student.display_name} → {self.material.title})"


class StudentMaterialResponse(models.Model):
    """Student-authored response data for non-file material interactions."""

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="student_responses")
    student = models.ForeignKey("StudentIdentity", on_delete=models.CASCADE, related_name="material_responses")
    checklist_checked = models.JSONField(default=list, blank=True)
    reflection_text = models.TextField(blank=True, default="")
    rubric_scores = models.JSONField(default=list, blank=True)
    rubric_feedback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["material", "student"],
                name="uniq_material_response_per_student",
            ),
        ]
        indexes = [
            models.Index(fields=["material", "student"], name="hub_matresp_matstu_3a9b_idx"),
            models.Index(fields=["student", "updated_at"], name="hub_matresp_stupd_7f2c_idx"),
        ]

    def __str__(self) -> str:
        return f"Response {self.id} ({self.student.display_name} → {self.material.title})"


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


class StudentSupportTag(models.Model):
    """Staff-only structured support tags for low-surveillance facilitation."""

    TAG_NEEDS_EXTRA_TIME = "needs_extra_time"
    TAG_PREFERS_QUIET = "prefers_quiet"
    TAG_DEVICE_HELP = "device_help"
    TAG_CHOICES = [
        (TAG_NEEDS_EXTRA_TIME, "Needs extra time"),
        (TAG_PREFERS_QUIET, "Prefers quiet"),
        (TAG_DEVICE_HELP, "Device help"),
    ]

    classroom = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="student_support_tags",
    )
    student = models.ForeignKey(
        "StudentIdentity",
        on_delete=models.CASCADE,
        related_name="support_tags",
    )
    tag = models.CharField(max_length=32, choices=TAG_CHOICES)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_support_tags_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student_id", "tag", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "student", "tag"],
                name="uniq_student_support_tag_per_class",
            ),
        ]
        indexes = [
            models.Index(fields=["classroom", "tag"], name="hub_stutag_clstag_70a1_idx"),
            models.Index(fields=["student", "tag"], name="hub_stutag_sttag_28f8_idx"),
        ]

    @classmethod
    def label_for(cls, tag: str) -> str:
        for value, label in cls.TAG_CHOICES:
            if value == tag:
                return str(label)
        return str(tag or "").replace("_", " ").strip().title()

    def save(self, *args, **kwargs):
        if self.student_id and self.classroom_id and self.student.classroom_id != self.classroom_id:
            raise ValueError("Student support tags must stay inside one class boundary.")
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student.display_name}: {self.label_for(self.tag)}"


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


from . import models_append_only_events as _append_only_events
from . import models_assets_audit as _assets_audit

StudentEventQuerySet = _append_only_events.StudentEventQuerySet
StudentEventManager = _append_only_events.StudentEventManager
StudentEvent = _append_only_events.StudentEvent
StudentOutcomeEventQuerySet = _append_only_events.StudentOutcomeEventQuerySet
StudentOutcomeEventManager = _append_only_events.StudentOutcomeEventManager
StudentOutcomeEvent = _append_only_events.StudentOutcomeEvent
CertificateIssuance = _assets_audit.CertificateIssuance
LessonAssetFolder = _assets_audit.LessonAssetFolder
LessonVideo = _assets_audit.LessonVideo
LessonRelease = _assets_audit.LessonRelease
LessonAsset = _assets_audit.LessonAsset
AuditEvent = _assets_audit.AuditEvent
