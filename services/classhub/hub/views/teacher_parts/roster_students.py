"""Compatibility facade for teacher roster student endpoints."""

from .roster_students_identity import (
    teach_rename_student,
    teach_student_return_code,
)
from .roster_students_lifecycle import (
    teach_delete_student_data,
    teach_merge_students,
)

__all__ = [
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
]
