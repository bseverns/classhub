from django.contrib import admin
from django.utils.html import format_html

from .services.audit import log_audit_event
from .models import (
    AuditEvent,
    CertificateIssuance,
    Class,
    ClassInviteLink,
    ClassStaffAssignment,
    ClassStaffModuleScopeGrant,
    LessonAsset,
    LessonAssetFolder,
    LessonRelease,
    LessonVideo,
    Material,
    Module,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationCustomRoleCapability,
    Organization,
    OrganizationRoleCapability,
    OrganizationMembership,
    RbacPolicyChangeRequest,
    StudentEvent,
    StudentIdentity,
    StudentMaterialResponse,
    StudentOutcomeEvent,
    Submission,
)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "updated_at")
    list_filter = ("organization", "role", "is_active")
    search_fields = ("organization__name", "user__username", "user__email")


@admin.register(OrganizationRoleCapability)
class OrganizationRoleCapabilityAdmin(admin.ModelAdmin):
    list_display = ("organization", "role", "capability", "is_active", "updated_at")
    list_filter = ("organization", "role", "capability", "is_active")
    search_fields = ("organization__name", "role", "capability")


@admin.register(OrganizationCustomRole)
class OrganizationCustomRoleAdmin(admin.ModelAdmin):
    list_display = ("organization", "slug", "name", "is_active", "updated_at")
    list_filter = ("organization", "is_active")
    search_fields = ("organization__name", "slug", "name")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "organization.custom_role.update" if change else "organization.custom_role.create"
        log_audit_event(
            request=request,
            action=action,
            target_type="OrganizationCustomRole",
            target_id=str(obj.id),
            summary=f"{'Updated' if change else 'Created'} custom role {obj.slug}",
            metadata={
                "organization_id": obj.organization_id,
                "slug": obj.slug,
                "name": obj.name,
                "is_active": bool(obj.is_active),
            },
        )

    def delete_model(self, request, obj):
        log_audit_event(
            request=request,
            action="organization.custom_role.delete",
            target_type="OrganizationCustomRole",
            target_id=str(obj.id),
            summary=f"Deleted custom role {obj.slug}",
            metadata={
                "organization_id": obj.organization_id,
                "slug": obj.slug,
                "name": obj.name,
            },
        )
        super().delete_model(request, obj)


@admin.register(OrganizationCustomRoleCapability)
class OrganizationCustomRoleCapabilityAdmin(admin.ModelAdmin):
    list_display = ("role", "capability", "is_active", "updated_at")
    list_filter = ("role__organization", "capability", "is_active")
    search_fields = ("role__organization__name", "role__slug", "capability")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "organization.custom_role_capability.update" if change else "organization.custom_role_capability.create"
        log_audit_event(
            request=request,
            action=action,
            target_type="OrganizationCustomRoleCapability",
            target_id=str(obj.id),
            summary=f"{'Updated' if change else 'Created'} custom role capability {obj.capability}",
            metadata={
                "organization_id": obj.role.organization_id,
                "role_id": obj.role_id,
                "capability": obj.capability,
                "is_active": bool(obj.is_active),
            },
        )

    def delete_model(self, request, obj):
        log_audit_event(
            request=request,
            action="organization.custom_role_capability.delete",
            target_type="OrganizationCustomRoleCapability",
            target_id=str(obj.id),
            summary=f"Deleted custom role capability {obj.capability}",
            metadata={
                "organization_id": obj.role.organization_id,
                "role_id": obj.role_id,
                "capability": obj.capability,
            },
        )
        super().delete_model(request, obj)


@admin.register(OrganizationCustomRoleAssignment)
class OrganizationCustomRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "updated_at")
    list_filter = ("organization", "is_active")
    search_fields = (
        "organization__name",
        "user__username",
        "user__email",
        "role__slug",
        "role__name",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "organization.custom_role_assignment.update" if change else "organization.custom_role_assignment.create"
        log_audit_event(
            request=request,
            action=action,
            target_type="OrganizationCustomRoleAssignment",
            target_id=str(obj.id),
            summary=f"{'Updated' if change else 'Created'} custom role assignment for user {obj.user_id}",
            metadata={
                "organization_id": obj.organization_id,
                "user_id": obj.user_id,
                "role_id": obj.role_id,
                "role_slug": obj.role.slug,
                "is_active": bool(obj.is_active),
            },
        )

    def delete_model(self, request, obj):
        log_audit_event(
            request=request,
            action="organization.custom_role_assignment.delete",
            target_type="OrganizationCustomRoleAssignment",
            target_id=str(obj.id),
            summary=f"Deleted custom role assignment for user {obj.user_id}",
            metadata={
                "organization_id": obj.organization_id,
                "user_id": obj.user_id,
                "role_id": obj.role_id,
                "role_slug": obj.role.slug,
            },
        )
        super().delete_model(request, obj)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "join_code", "enrollment_mode", "is_locked")
    search_fields = ("name", "join_code", "organization__name")
    list_filter = ("organization", "enrollment_mode", "is_locked")


@admin.register(ClassStaffAssignment)
class ClassStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = ("classroom", "user", "is_active", "updated_at")
    list_filter = ("classroom", "is_active")
    search_fields = ("classroom__name", "classroom__join_code", "user__username", "user__email")


@admin.register(ClassStaffModuleScopeGrant)
class ClassStaffModuleScopeGrantAdmin(admin.ModelAdmin):
    list_display = (
        "classroom",
        "user",
        "capability",
        "effect",
        "module_order_start",
        "module_order_end",
        "is_active",
        "updated_at",
    )
    list_filter = ("classroom", "capability", "effect", "is_active")
    search_fields = ("classroom__name", "classroom__join_code", "user__username", "user__email")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "rbac.scope_grant.update" if change else "rbac.scope_grant.create"
        log_audit_event(
            request=request,
            action=action,
            classroom=obj.classroom,
            target_type="ClassStaffModuleScopeGrant",
            target_id=str(obj.id),
            summary=f"{'Updated' if change else 'Created'} scoped grant {obj.capability} ({obj.effect})",
            metadata={
                "user_id": obj.user_id,
                "capability": obj.capability,
                "effect": obj.effect,
                "module_order_start": obj.module_order_start,
                "module_order_end": obj.module_order_end,
                "is_active": bool(obj.is_active),
            },
        )

    def delete_model(self, request, obj):
        log_audit_event(
            request=request,
            action="rbac.scope_grant.delete",
            classroom=obj.classroom,
            target_type="ClassStaffModuleScopeGrant",
            target_id=str(obj.id),
            summary=f"Deleted scoped grant {obj.capability} ({obj.effect})",
            metadata={
                "user_id": obj.user_id,
                "capability": obj.capability,
                "effect": obj.effect,
                "module_order_start": obj.module_order_start,
                "module_order_end": obj.module_order_end,
            },
        )
        super().delete_model(request, obj)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "order_index")
    list_filter = ("classroom",)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "type", "order_index")
    list_filter = ("type", "module__classroom")

@admin.register(StudentIdentity)
class StudentIdentityAdmin(admin.ModelAdmin):
    list_display = ("display_name", "return_code", "classroom", "created_at", "last_seen_at")
    list_filter = ("classroom",)
    search_fields = ("display_name", "return_code")


@admin.register(StudentEvent)
class StudentEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "classroom", "student", "source", "ip_address")
    list_filter = ("event_type", "classroom", "student", ("created_at", admin.DateFieldListFilter))
    search_fields = ("source", "ip_address", "student__display_name", "classroom__name", "classroom__join_code")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StudentOutcomeEvent)
class StudentOutcomeEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "classroom", "student", "module", "material", "source")
    list_filter = ("event_type", "classroom", "module", ("created_at", admin.DateFieldListFilter))
    search_fields = ("source", "student__display_name", "classroom__name", "classroom__join_code")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ClassInviteLink)
class ClassInviteLinkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "classroom",
        "label",
        "is_active",
        "max_uses",
        "use_count",
        "expires_at",
        "created_at",
        "last_used_at",
    )
    list_filter = ("is_active", "classroom")
    search_fields = ("token", "label", "classroom__name", "classroom__join_code")
    readonly_fields = ("use_count", "created_at", "last_used_at", "updated_at")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "uploaded_at", "student", "material", "original_filename", "is_gallery_shared", "download_link")
    list_filter = ("material__module__classroom", "material")
    search_fields = ("original_filename", "student__display_name")
    readonly_fields = ("uploaded_at",)

    def download_link(self, obj: Submission):
        return format_html('<a href="/submission/{}/download">Download</a>', obj.id)

    download_link.short_description = "Download"


@admin.register(StudentMaterialResponse)
class StudentMaterialResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "material", "updated_at")
    list_filter = ("material__module__classroom", "material")
    search_fields = ("student__display_name", "material__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CertificateIssuance)
class CertificateIssuanceAdmin(admin.ModelAdmin):
    list_display = ("code", "classroom", "student", "issued_by", "session_count", "artifact_count", "issued_at")
    list_filter = ("classroom", "issued_by")
    search_fields = ("code", "student__display_name", "classroom__name", "classroom__join_code")
    readonly_fields = ("issued_at", "updated_at")


@admin.register(LessonVideo)
class LessonVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "course_slug", "lesson_slug", "order_index", "is_active", "updated_at")
    list_filter = ("course_slug", "lesson_slug", "is_active")
    search_fields = ("title", "course_slug", "lesson_slug", "source_url")


@admin.register(LessonRelease)
class LessonReleaseAdmin(admin.ModelAdmin):
    list_display = ("classroom", "course_slug", "lesson_slug", "available_on", "force_locked", "updated_at")
    list_filter = ("classroom", "course_slug", "force_locked")
    search_fields = ("classroom__name", "classroom__join_code", "course_slug", "lesson_slug")


@admin.register(LessonAssetFolder)
class LessonAssetFolderAdmin(admin.ModelAdmin):
    list_display = ("path", "display_name", "created_at", "updated_at")
    search_fields = ("path", "display_name")
    ordering = ("path", "id")


@admin.register(LessonAsset)
class LessonAssetAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "folder",
        "course_slug",
        "lesson_slug",
        "is_active",
        "updated_at",
        "download_link",
    )
    list_filter = ("is_active", "folder", "course_slug", "lesson_slug")
    search_fields = ("title", "description", "original_filename", "folder__path", "course_slug", "lesson_slug")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("folder",)

    def download_link(self, obj: LessonAsset):
        return format_html('<a href="/lesson-asset/{}/download" target="_blank" rel="noopener">Download</a>', obj.id)

    download_link.short_description = "Download"


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor_user", "classroom", "target_type", "target_id", "ip_address")
    list_filter = ("action", "classroom", "actor_user")
    search_fields = ("action", "summary", "target_type", "target_id", "ip_address", "actor_user__username")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RbacPolicyChangeRequest)
class RbacPolicyChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "request_type",
        "status",
        "requested_by",
        "reviewed_by",
        "organization",
        "classroom",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("request_type", "status", "organization")
    search_fields = ("summary", "requested_by__username", "reviewed_by__username")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
