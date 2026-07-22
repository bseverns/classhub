import builtins
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = REPO_ROOT / "scripts" / "coursepack_sdk.py"


class CoursepackSdkTests(unittest.TestCase):
    def test_validate_all_does_not_import_django(self):
        real_import = builtins.__import__

        def import_without_django(name, *args, **kwargs):
            if name == "django" or name.startswith("django."):
                raise AssertionError(f"validate imported {name}")
            return real_import(name, *args, **kwargs)

        with (
            patch.object(builtins, "__import__", side_effect=import_without_django),
            patch.object(sys, "argv", [str(SDK_PATH), "validate", "--all"]),
            patch.object(sys, "path", [str(SDK_PATH.parent), *sys.path]),
            self.assertRaises(SystemExit) as exit_context,
        ):
            runpy.run_path(str(SDK_PATH), run_name="__main__")

        self.assertEqual(exit_context.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
