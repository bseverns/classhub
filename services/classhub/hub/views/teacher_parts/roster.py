"""Compatibility exports for split teacher roster endpoints."""

from .roster_class import (
    teach_class_dashboard,
    teach_class_join_card,
    teach_create_invite_link,
    teach_create_class,
    teach_disable_invite_link,
    teach_export_class_summary_csv,
    teach_export_class_submissions_today,
    teach_lock_class,
    teach_reset_helper_conversations,
    teach_reset_roster,
    teach_rotate_code,
    teach_toggle_lock,
)
from .roster_materials import (
    teach_add_material,
    teach_add_module,
    teach_material_submissions,
    teach_module,
    teach_move_material,
    teach_move_module,
)
from .roster_students import (
    teach_delete_student_data,
    teach_merge_students,
    teach_rename_student,
    teach_student_return_code,
)

__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_create_invite_link",
    "teach_disable_invite_link",
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_summary_csv",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
    "teach_add_module",
    "teach_move_module",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
