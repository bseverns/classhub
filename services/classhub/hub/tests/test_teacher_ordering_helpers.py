from unittest.mock import patch

from ._shared import *  # noqa: F401,F403

from hub.views.teacher_parts.shared_ordering import _apply_directional_reorder, _normalize_order


class TeacherOrderingHelperTests(TestCase):
    def test_apply_directional_reorder_bulk_updates_changed_modules(self):
        classroom = Class.objects.create(name="Ordering Class", join_code="ORD12345")
        first = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        second = Module.objects.create(classroom=classroom, title="Session 2", order_index=1)
        modules = list(classroom.modules.all().order_by("order_index", "id"))

        with patch.object(
            Module.objects,
            "bulk_update",
            wraps=Module.objects.bulk_update,
        ) as bulk_update:
            changed = _apply_directional_reorder(modules, target_id=second.id, direction="up")

        self.assertTrue(changed)
        bulk_update.assert_called_once()
        self.assertEqual(len(bulk_update.call_args.args[0]), 2)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.order_index, first.order_index), (0, 1))

    def test_normalize_order_bulk_updates_changed_materials(self):
        classroom = Class.objects.create(name="Normalize Class", join_code="NORM1234")
        module = Module.objects.create(classroom=classroom, title="Session 1", order_index=0)
        first = Material.objects.create(
            module=module,
            title="Later",
            type=Material.TYPE_TEXT,
            body="later",
            order_index=4,
        )
        second = Material.objects.create(
            module=module,
            title="Sooner",
            type=Material.TYPE_TEXT,
            body="sooner",
            order_index=7,
        )
        materials = list(module.materials.all().order_by("order_index", "id"))

        with patch.object(
            Material.objects,
            "bulk_update",
            wraps=Material.objects.bulk_update,
        ) as bulk_update:
            _normalize_order(materials)

        bulk_update.assert_called_once()
        self.assertEqual(len(bulk_update.call_args.args[0]), 2)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.order_index, second.order_index), (0, 1))
