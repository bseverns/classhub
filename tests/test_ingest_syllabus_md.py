import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ingest_syllabus_md.py"
SPEC = importlib.util.spec_from_file_location("ingest_syllabus_md", SCRIPT_PATH)
assert SPEC and SPEC.loader
ingest_syllabus_md = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ingest_syllabus_md)


class StandaloneSyllabusSlugTests(unittest.TestCase):
    def _assert_write_rejected(self, source: str, expected: str) -> None:
        sessions = ingest_syllabus_md._parse_sessions(source)
        with tempfile.TemporaryDirectory() as temp_dir:
            courses_root = Path(temp_dir) / "courses"
            original_root = ingest_syllabus_md.COURSES_ROOT
            ingest_syllabus_md.COURSES_ROOT = courses_root
            try:
                with self.assertRaisesRegex(ValueError, expected):
                    ingest_syllabus_md._write_course(
                        "slug_test",
                        "Slug Test",
                        sessions,
                        75,
                        "",
                        "",
                        [],
                        "secondary",
                        "secondary",
                    )
            finally:
                ingest_syllabus_md.COURSES_ROOT = original_root
            self.assertFalse(courses_root.exists())

    def test_rejects_duplicate_final_lesson_slugs_before_writing(self):
        self._assert_write_rejected(
            """Session 01: First
Lesson slug (for course.yaml): s01-duplicate
Session 01: Second
Lesson slug (for course.yaml): s01-duplicate
""",
            "Duplicate lesson slug",
        )

    def test_rejects_malformed_explicit_lesson_slug_before_writing(self):
        self._assert_write_rejected(
            """Session 01: First
Lesson slug (for course.yaml): S01_bad_slug
""",
            "sNN-lowercase-dashes",
        )


if __name__ == "__main__":
    unittest.main()
