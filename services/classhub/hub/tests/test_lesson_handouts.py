from ._shared import *  # noqa: F401,F403


class LessonHandoutTests(TestCase):
    def test_course_lesson_surfaces_belonging_layers_and_reading_level_handout(self):
        manifest = """
title: "Neighborhood Circuits"
community_glossary:
  loop: "a path that closes back on itself"
lessons:
  - slug: s01-neighborhood-circuits
    title: "Neighborhood Circuits"
    file: "lessons/01-neighborhood-circuits.md"
"""
        lesson = """---
title: Neighborhood Circuits
makes: "A small circuit plan you can explain."
needs:
  - battery
  - tape
privacy:
  - Keep private names out of the final artifact.
submission:
  type: file
  accepted:
    - .pdf
  naming: circuit-plan.pdf
local_anchors:
  - Where might you see this in your neighborhood?
  - Who fixes or uses this around here?
example_variants:
  - kitchen timer
  - transit light
community_glossary:
  - term: resistor
    definition: part that slows electricity down
offline_handout:
  subtitle: "Build, explain, and upload one circuit idea."
  do_now:
    - Sketch one circuit idea.
    - Label the energy path.
  reading_levels:
    simple:
      do_now:
        - Draw one circuit.
        - Show where energy moves.
      submit:
        - Upload one PDF page.
---
## Build

Draw, test, and explain one loop.
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            content_root = Path(temp_dir)
            course_dir = content_root / "courses" / "neighborhood_circuits"
            lesson_dir = course_dir / "lessons"
            lesson_dir.mkdir(parents=True, exist_ok=True)
            (course_dir / "course.yaml").write_text(manifest, encoding="utf-8")
            (lesson_dir / "01-neighborhood-circuits.md").write_text(lesson, encoding="utf-8")

            with override_settings(CONTENT_ROOT=content_root):
                resp = self.client.get("/course/neighborhood_circuits/s01-neighborhood-circuits?reading_level=simple")
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, "Local anchors")
                self.assertContains(resp, "Community glossary")
                self.assertContains(resp, "Reading level: Simple")
                self.assertContains(resp, "Draw one circuit.")
                self.assertContains(resp, "Download handout PDF")

                handout = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout?reading_level=simple"
                )
                self.assertEqual(handout.status_code, 200)
                self.assertContains(handout, "Open online")
                self.assertContains(handout, "<svg", html=False)
                self.assertContains(handout, "Upload one PDF page.")

                pdf = self.client.get(
                    "/course/neighborhood_circuits/s01-neighborhood-circuits/handout.pdf?reading_level=simple"
                )
                self.assertEqual(pdf.status_code, 200)
                self.assertEqual(pdf["Content-Type"], "application/pdf")
                self.assertTrue(pdf.content.startswith(b"%PDF-1.4"))
