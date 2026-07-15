import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RemoteComputeOpsContractTests(unittest.TestCase):
    def test_reconcile_timer_is_hardened_short_cadence_and_documented(self):
        service = (ROOT / "ops/systemd/classhub-remote-compute-reconcile.service").read_text()
        timer = (ROOT / "ops/systemd/classhub-remote-compute-reconcile.timer").read_text()
        runbook = (ROOT / "docs/REMOTE_HELPER_COMPUTE_CONTROL.md").read_text()
        control_panel = (
            ROOT / "services/classhub/templates/includes/teach_class/helper_signals/remote_compute_panel.html"
        ).read_text()

        self.assertIn("manage.py reconcile_remote_compute_state", service)
        self.assertIn("User=lms", service)
        self.assertIn("NoNewPrivileges=yes", service)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("OnUnitActiveSec=2min", timer)
        self.assertIn("classhub-remote-compute-reconcile.timer", runbook)
        self.assertIn("provider-side hard TTL", runbook)
        self.assertIn("minutes == 30 %} selected", control_panel)

    def test_headscale_artifacts_use_canonical_tags_login_server_and_https_acl(self):
        policy = (ROOT / "ops/headscale/policy.hujson.example").read_text()
        helper_docs = (ROOT / "docs/OPENAI_HELPER.md").read_text()
        headscale_docs = (ROOT / "docs/HEADSCALE_CONTROL_PLANE.md").read_text()

        self.assertIn('"tag:classhub-lms"', policy)
        self.assertIn('"tag:thundercompute-gpu"', policy)
        self.assertIn('"src": ["tag:classhub-lms"]', policy)
        self.assertIn('"dst": ["tag:thundercompute-gpu:443"]', policy)
        self.assertIn('"src": ["tag:ops"]', policy)
        self.assertIn('"dst": ["tag:classhub-lms:22", "tag:thundercompute-gpu:22"]', policy)
        self.assertNotIn('"tag:gpu:*"', policy)
        self.assertNotIn('"src": ["tag:thundercompute-gpu"]', policy)
        self.assertIn("--login-server=https://hs.creatempls.org", helper_docs)
        self.assertIn("--auth-key=REPLACE_WITH_PREAUTH_KEY", helper_docs)
        self.assertIn("--advertise-tags=tag:thundercompute-gpu", helper_docs)
        self.assertIn("--advertise-tags=tag:classhub-lms", headscale_docs)


if __name__ == "__main__":
    unittest.main()
