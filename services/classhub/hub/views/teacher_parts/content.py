"""Compatibility re-exports for teacher content views."""

from .content_home import (
    teach_download_authoring_template,
    teach_generate_authoring_templates,
    teach_home,
)
from .content_lessons import teach_lessons, teach_set_lesson_release

__all__ = [
    "teach_home",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
    "teach_lessons",
    "teach_set_lesson_release",
]
