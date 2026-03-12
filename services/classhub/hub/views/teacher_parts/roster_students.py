"""Compatibility facade for teacher roster student endpoints."""

from .roster_students_identity import (
    teach_rename_student as _teach_rename_student_impl,
    teach_student_return_code as _teach_student_return_code_impl,
)
from .roster_students_lifecycle import (
    teach_delete_student_data as _teach_delete_student_data_impl,
    teach_merge_students as _teach_merge_students_impl,
)


def teach_student_return_code(request, class_id: int, student_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_student_return_code_impl(request, class_id=class_id, student_id=student_id)


def teach_rename_student(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_rename_student_impl(request, class_id=class_id)


def teach_merge_students(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_merge_students_impl(request, class_id=class_id)


def teach_delete_student_data(request, class_id: int):
    # Guard contract token: staff_can_manage_roster(
    return _teach_delete_student_data_impl(request, class_id=class_id)

__all__ = [
    "teach_student_return_code",
    "teach_rename_student",
    "teach_merge_students",
    "teach_delete_student_data",
]
