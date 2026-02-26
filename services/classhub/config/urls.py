"""Top-level URL map for the Class Hub Django service.

Plain-language map:
- `/` + `/join` + `/student` are the learner flow.
- `/teach/...` is the teacher/staff workspace.
- `/admin/...` is the Django admin surface (superusers only here).
- `/helper/...` is intentionally NOT in this file; Caddy routes it to the
  separate Homework Helper service.
"""

from django.contrib import admin
from django.urls import path
from hub import views

urlpatterns = [
    # Admin surface (operations/configuration). Kept separate from daily teaching UI.
    path("admin/", admin.site.urls),

    # Health endpoint for reverse proxy and uptime checks.
    path("healthz", views.healthz),
    path("internal/events/helper-chat-access", views.internal_helper_chat_access_event),

    # Student flow (class-code login and classroom page).
    path("", views.index),
    path("invite/<slug:invite_token>", views.invite_join),
    path("join", views.join_class),
    path("student", views.student_home),
    path("student/return-code", views.student_return_code),
    path("student/my-data", views.student_my_data),
    path("student/delete-work", views.student_delete_work),
    path("student/end-session", views.student_end_session),
    path("student/portfolio-export", views.student_portfolio_export),
    path("logout", views.student_logout),

    # Student upload + shared download/stream routes.
    path("material/<int:material_id>/upload", views.material_upload),
    path("material/<int:material_id>/checklist", views.material_checklist),
    path("material/<int:material_id>/reflection", views.material_reflection),
    path("material/<int:material_id>/rubric", views.material_rubric),
    path("submission/<int:submission_id>/download", views.submission_download),
    path("lesson-video/<int:video_id>/stream", views.lesson_video_stream),
    path("lesson-asset/<int:asset_id>/download", views.lesson_asset_download),

    # Repo-authored course content pages (markdown rendered to HTML).
    path("course/<slug:course_slug>", views.course_overview),
    path("course/<slug:course_slug>/<slug:lesson_slug>", views.course_lesson),

    # Teacher cockpit (staff-only, outside Django admin).
    path("teach", views.teach_home),
    path("teach/login", views.teach_login),
    path("teach/profile/update", views.teach_update_profile),
    path("teach/profile/password", views.teach_change_password),
    path("teach/2fa/setup", views.teach_teacher_2fa_setup),
    path("teach/create-teacher", views.teach_create_teacher),
    path("teach/create-organization", views.teach_create_organization),
    path("teach/org-membership/upsert", views.teach_upsert_organization_membership),
    path("teach/org/<int:org_id>/set-active", views.teach_set_organization_active),
    path("teach/generate-authoring-templates", views.teach_generate_authoring_templates),
    path("teach/authoring-template/download", views.teach_download_authoring_template),
    path("teach/logout", views.teacher_logout),
    path("teach/lessons", views.teach_lessons),
    path("teach/lessons/release", views.teach_set_lesson_release),
    path("teach/assets", views.teach_assets),
    path("teach/create-class", views.teach_create_class),
    path("teach/class/<int:class_id>", views.teach_class_dashboard),
    path("teach/class/<int:class_id>/join-card", views.teach_class_join_card),
    path("teach/class/<int:class_id>/create-invite-link", views.teach_create_invite_link),
    path("teach/class/<int:class_id>/disable-invite-link", views.teach_disable_invite_link),
    path("teach/class/<int:class_id>/set-enrollment-mode", views.teach_set_enrollment_mode),
    path("teach/class/<int:class_id>/student/<int:student_id>/return-code", views.teach_student_return_code),
    path("teach/class/<int:class_id>/rename-student", views.teach_rename_student),
    path("teach/class/<int:class_id>/merge-students", views.teach_merge_students),
    path("teach/class/<int:class_id>/delete-student-data", views.teach_delete_student_data),
    path("teach/class/<int:class_id>/reset-roster", views.teach_reset_roster),
    path("teach/class/<int:class_id>/reset-helper-conversations", views.teach_reset_helper_conversations),
    path("teach/class/<int:class_id>/toggle-lock", views.teach_toggle_lock),
    path("teach/class/<int:class_id>/lock", views.teach_lock_class),
    path("teach/class/<int:class_id>/export-submissions-today", views.teach_export_class_submissions_today),
    path("teach/class/<int:class_id>/export-outcomes-csv", views.teach_export_class_outcomes_csv),
    path("teach/class/<int:class_id>/export-summary-csv", views.teach_export_class_summary_csv),
    path("teach/class/<int:class_id>/certificate-eligibility", views.teach_certificate_eligibility),
    path("teach/class/<int:class_id>/mark-session-completed", views.teach_mark_session_completed),
    path("teach/class/<int:class_id>/issue-certificate", views.teach_issue_certificate),
    path(
        "teach/class/<int:class_id>/certificate/<int:student_id>/download",
        views.teach_download_certificate,
    ),
    path(
        "teach/class/<int:class_id>/certificate/<int:student_id>/download.pdf",
        views.teach_download_certificate_pdf,
    ),
    path("teach/class/<int:class_id>/rotate-code", views.teach_rotate_code),
    path("teach/class/<int:class_id>/add-module", views.teach_add_module),
    path("teach/class/<int:class_id>/move-module", views.teach_move_module),
    path("teach/videos", views.teach_videos),
    path("teach/module/<int:module_id>", views.teach_module),
    path("teach/module/<int:module_id>/add-material", views.teach_add_material),
    path("teach/module/<int:module_id>/move-material", views.teach_move_material),
    path("teach/material/<int:material_id>/submissions", views.teach_material_submissions),
]
