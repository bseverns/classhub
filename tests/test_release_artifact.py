from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        # Match the canonical path produced by make_release_zip.sh (`pwd`).
        # macOS exposes /var as a symlink to /private/var.
        self.repo = Path(self.tempdir.name).resolve()
        fixture_files = {
            "VERSION": "1.9.0-dev\n",
            "release/policy.json": json.dumps(
                {"schema_version": 1, "supported_upgrade_origins": ["1.8.4"]}
            )
            + "\n",
            "compose/.env.example.domain": "\n".join(
                (
                    "CADDY_IMAGE=caddy:2.10.2",
                    "POSTGRES_IMAGE=postgres:16.8",
                    "REDIS_IMAGE=redis:7.4.2",
                    "OLLAMA_IMAGE=ollama/ollama:0.5.7",
                    "MINIO_IMAGE=minio/minio:stable",
                )
            )
            + "\n",
            "services/classhub/Dockerfile": "FROM python:3.12-slim\n",
            "services/homework_helper/Dockerfile": "FROM python:3.12-slim\n",
            "services/classhub/requirements.txt": "Django==5.2.16\n",
            "services/homework_helper/requirements.txt": "Django==5.2.16\n",
            "services/classhub/hub/migrations/0001_initial.py": (
                "class Migration:\n    dependencies = []\n"
            ),
            "services/classhub/hub/migrations/0002_next.py": (
                "class Migration:\n"
                "    dependencies = [('hub', '0001_initial')]\n"
            ),
            "payload.txt": "committed payload\n",
        }
        for relative, content in fixture_files.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        scripts_dir = self.repo / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        for name in ("make_release_zip.sh", "release_artifact.py", "lint_release_artifact.py"):
            shutil.copy2(REPO_ROOT / "scripts" / name, scripts_dir / name)
        self._git("init", "-q")
        self._git("config", "user.name", "Release Test")
        self._git("config", "user.email", "release-test@example.invalid")
        self._git("add", ".")
        self._git("commit", "-qm", "fixture")
        self.commit = self._git("rev-parse", "HEAD").stdout.strip()
        self.output = self.repo / "artifact.zip"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def _build(self, *extra: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        return subprocess.run(
            [
                "bash",
                "scripts/make_release_zip.sh",
                *extra,
                str(self.output),
            ],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_publishing_requires_matching_annotated_tag(self) -> None:
        untagged = self._build()
        self.assertNotEqual(untagged.returncode, 0)
        self.assertIn("requires an annotated", untagged.stderr)

        self._git("tag", "1.9.0-dev")
        lightweight = self._build()
        self.assertNotEqual(lightweight.returncode, 0)
        self.assertIn("requires an annotated", lightweight.stderr)

        self._git("tag", "-d", "1.9.0-dev")
        self._git("tag", "-a", "1.9.0-dev", "-m", "release fixture")
        tagged = self._build()
        self.assertEqual(tagged.returncode, 0, tagged.stdout + tagged.stderr)

    def test_ci_mode_builds_exact_commit_with_manifest_and_sidecars(self) -> None:
        result = self._build("--allow-untagged", "--ref", self.commit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(Path(f"{self.output}.sha256").is_file())
        self.assertTrue(Path(f"{self.output}.manifest.json").is_file())

        with ZipFile(self.output) as archive:
            manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
            self.assertEqual(archive.read("payload.txt"), b"committed payload\n")
        self.assertEqual(manifest["version"], "1.9.0-dev")
        self.assertEqual(manifest["source"]["commit"], self.commit)
        self.assertIsNone(manifest["source"]["tag"])
        self.assertEqual(manifest["supported_upgrade_origins"], ["1.8.4"])
        self.assertEqual(manifest["migration_heads"]["hub"], ["0002_next"])
        self.assertEqual(manifest["runtime_versions"]["django"]["classhub"], "5.2.16")
        self.assertGreater(manifest["payload"]["file_count"], 5)

        detached = json.loads(Path(f"{self.output}.manifest.json").read_text(encoding="utf-8"))
        checksum = Path(f"{self.output}.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(detached["artifact"]["sha256"], checksum)
        self.assertEqual(detached["artifact"]["filename"], self.output.name)

    def test_dirty_tracked_tree_is_rejected(self) -> None:
        (self.repo / "payload.txt").write_text("dirty payload\n", encoding="utf-8")
        result = self._build("--allow-untagged")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean working tree", result.stderr)
        self.assertFalse(self.output.exists())

    def test_payload_tampering_is_detected(self) -> None:
        result = self._build("--allow-untagged")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with ZipFile(self.output) as original:
            entries = {name: original.read(name) for name in original.namelist()}
        entries["payload.txt"] = b"tampered\n"
        with ZipFile(self.output, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(name, content)

        verify = subprocess.run(
            [sys.executable, "scripts/lint_release_artifact.py", str(self.output)],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("payload", verify.stderr.lower())

    def test_missing_checksum_sidecar_is_rejected(self) -> None:
        result = self._build("--allow-untagged")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        Path(f"{self.output}.sha256").unlink()

        verify = subprocess.run(
            [sys.executable, "scripts/lint_release_artifact.py", str(self.output)],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("sidecar is missing", verify.stderr)


if __name__ == "__main__":
    unittest.main()
