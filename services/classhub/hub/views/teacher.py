"""Compatibility export surface for teacher portal endpoints."""

from .teacher_parts.auth import *  # noqa: F401,F403
from .teacher_parts.content import *  # noqa: F401,F403
from .teacher_parts.roster import *  # noqa: F401,F403
from .teacher_parts.videos import *  # noqa: F401,F403

__all__ = [
    "teach_login",
    "teacher_logout",
    "teach_home",
    "teach_teacher_2fa_setup",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
    "teach_create_teacher",
    "teach_lessons",
    "teach_set_lesson_release",
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
    "teach_reset_roster",
    "teach_reset_helper_conversations",
    "teach_toggle_lock",
    "teach_lock_class",
    "teach_export_class_submissions_today",
    "teach_rotate_code",
    "teach_add_module",
    "teach_move_module",
    "teach_videos",
    "teach_assets",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
