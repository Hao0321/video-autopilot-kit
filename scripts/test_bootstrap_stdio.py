"""The bootstrap reports success when the install root is outside the ANSI codepage."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "the ANSI-codepage pipe default is Windows-only")
class BootstrapStdioTests(unittest.TestCase):
    def test_apply_reports_status_for_non_ansi_install_root(self):
        with tempfile.TemporaryDirectory(prefix="bootstrap-stdio-") as temporary:
            base = Path(temporary)
            built = subprocess.run(
                [sys.executable, str(ROOT / "src" / "release_manager.py"), "build", "--dist", str(base / "dist")],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            channel = base / "dist" / "release-channel.json"
            install = base / "José 视频"  # cp950 cannot encode the accented e; cp1252 cannot encode the CJK pair
            # Agents read this JSON through a pipe without UTF-8 mode, as on a default Windows console.
            environment = {key: value for key, value in os.environ.items()
                           if key not in {"PYTHONUTF8", "PYTHONIOENCODING"}}
            for _ in range(2):  # fresh install, then the already-current report
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "install_or_upgrade.py"), "--channel", str(channel),
                     "--install-root", str(install), "--apply"],
                    cwd=base, env=environment, capture_output=True, timeout=300)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                result = json.loads(completed.stdout.decode("utf-8"))
                self.assertIn(result["status"], {"UPDATED", "CURRENT"})


if __name__ == "__main__":
    unittest.main()
