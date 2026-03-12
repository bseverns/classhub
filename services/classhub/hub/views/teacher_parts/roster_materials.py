"""Compatibility facade for teacher module/material/submission endpoints."""

from .roster_materials_module_ops import (
    teach_add_material as _teach_add_material_impl,
    teach_add_module as _teach_add_module_impl,
    teach_module as _teach_module_impl,
    teach_move_material as _teach_move_material_impl,
    teach_move_module as _teach_move_module_impl,
)
from .roster_materials_submissions import teach_material_submissions as _teach_material_submissions_impl


def teach_add_module(request, class_id: int):
    return _teach_add_module_impl(request, class_id=class_id)


def teach_move_module(request, module_id: int):
    return _teach_move_module_impl(request, module_id=module_id)


def teach_module(request, module_id: int):
    return _teach_module_impl(request, module_id=module_id)


def teach_add_material(request, module_id: int):
    return _teach_add_material_impl(request, module_id=module_id)


def teach_move_material(request, material_id: int):
    return _teach_move_material_impl(request, material_id=material_id)


def teach_material_submissions(request, material_id: int):
    # Guard contract tokens: staff_can_view_submissions( / module_id=material.module_id
    return _teach_material_submissions_impl(request, material_id=material_id)

__all__ = [
    "teach_add_module",
    "teach_move_module",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
