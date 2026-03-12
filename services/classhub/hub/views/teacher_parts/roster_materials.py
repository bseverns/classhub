"""Compatibility facade for teacher module/material/submission endpoints."""

from .roster_materials_module_ops import (
    teach_add_material,
    teach_add_module,
    teach_module,
    teach_move_material,
    teach_move_module,
)
from .roster_materials_submissions import teach_material_submissions

__all__ = [
    "teach_add_module",
    "teach_move_module",
    "teach_module",
    "teach_add_material",
    "teach_move_material",
    "teach_material_submissions",
]
