"""Compatibility re-exports for teacher content views."""

from .content_home import (
    teach_download_authoring_template,
    teach_generate_authoring_templates,
    teach_home,
)
from .content_data_lifespan import teach_data_lifespan, teach_data_lifespan_export
from .content_rbac_tools import (
    teach_review_rbac_change_request,
    teach_set_module_scope_grant_active,
    teach_simulate_rbac_access,
    teach_upsert_custom_role,
    teach_upsert_custom_role_assignment,
    teach_upsert_custom_role_capability,
    teach_upsert_module_scope_grant,
)
from .content_rbac_policy_io import (
    teach_export_rbac_policy,
    teach_import_rbac_policy,
)
from .content_lessons import teach_edit_lesson_content, teach_lessons, teach_set_lesson_release
from .content_syllabus_import import teach_import_syllabus_source
from .content_syllabus_exports import teach_export_syllabus

__all__ = [
    "teach_home",
    "teach_data_lifespan",
    "teach_data_lifespan_export",
    "teach_upsert_module_scope_grant",
    "teach_set_module_scope_grant_active",
    "teach_simulate_rbac_access",
    "teach_upsert_custom_role",
    "teach_upsert_custom_role_capability",
    "teach_upsert_custom_role_assignment",
    "teach_review_rbac_change_request",
    "teach_export_rbac_policy",
    "teach_import_rbac_policy",
    "teach_import_syllabus_source",
    "teach_export_syllabus",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
    "teach_lessons",
    "teach_set_lesson_release",
    "teach_edit_lesson_content",
]
