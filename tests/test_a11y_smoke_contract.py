from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AccessibilitySmokeContractTests(unittest.TestCase):
    def test_release_smoke_covers_trust_admin_and_destructive_surfaces_at_serious_threshold(self):
        runner = (ROOT / "scripts/a11y/run_smoke.mjs").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/stack-smoke.yml").read_text(encoding="utf-8")

        for route in ('path: "/privacy"', 'path: "/trust"', 'path: "/admin/login/"', 'path: "/student/my-data"'):
            self.assertIn(route, runner)
        self.assertIn("--fail-impact serious", workflow)
        self.assertNotIn("--fail-impact critical", workflow)


if __name__ == "__main__":
    unittest.main()
