"""Portable regressions for the complete pinned Cleanup distribution."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

import public_cleanup_bundle as bundle
from public_sync_paths import _text_sha256
from public_privacy_gate import public_privacy_findings
from public_upstream_fixtures import reviewed_fixture_rules

ROOT = Path(__file__).resolve().parents[1]


class CleanupBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cleanup-bundle-regression-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "kit"
        self.cleanup = self.root / "tools/code-cleanup-helper"
        shutil.copytree(ROOT / "tools/code-cleanup-helper", self.cleanup)

    def manifest(self):
        return json.loads((self.root / bundle.BUNDLE_PATH).read_text(encoding="utf-8"))

    def write_manifest(self, value):
        (self.root / bundle.BUNDLE_PATH).write_text(json.dumps(value), encoding="utf-8")

    def test_exact_current_export_and_portable_defaults(self):
        bundle.verify_cleanup_bundle(self.root)
        self.assertEqual(self.manifest()["upstream"]["tag"], "v0.22.1")
        self.assertEqual(len(self.manifest()["files"]), 71)
        config = json.loads((self.cleanup / "audit.config.json").read_text(encoding="utf-8"))
        self.assertIsNone(config["sync"]["public_root"])

    def test_missing_dependency_is_rejected(self):
        (self.cleanup / "scripts/audit_coverage_selftest.py").unlink()
        with self.assertRaises((ValueError, OSError)):
            bundle.verify_cleanup_bundle(self.root)

    def test_changed_source_cannot_be_hidden_by_manifest_rehash(self):
        source = self.cleanup / "scripts/check_release_exposure.py"
        source.write_text("changed = True\n", encoding="utf-8")
        value = self.manifest()
        value["files"]["scripts/check_release_exposure.py"] = _text_sha256(source)
        self.write_manifest(value)
        with self.assertRaisesRegex(ValueError, "export pin"):
            bundle.verify_cleanup_bundle(self.root)

    def test_stale_release_and_incomplete_manifest_are_rejected(self):
        original = self.manifest()
        changed = json.loads(json.dumps(original))
        changed["upstream"]["tag"] = "v0.21.0"
        self.write_manifest(changed)
        with self.assertRaisesRegex(ValueError, "provenance"):
            bundle.verify_cleanup_bundle(self.root)
        original["files"].pop("scripts/sync_safety.py")
        self.write_manifest(original)
        with self.assertRaisesRegex(ValueError, "provenance"):
            bundle.verify_cleanup_bundle(self.root)

    def test_new_upstream_dependency_requires_inventory_refresh(self):
        (self.cleanup / "BUNDLE.json").unlink()
        bundle.validate_cleanup_source(self.cleanup)
        (self.cleanup / "scripts/new_dependency.py").write_text("VALUE = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inventory"):
            bundle.validate_cleanup_source(self.cleanup)

    def test_changed_upstream_source_requires_pin_refresh(self):
        (self.cleanup / "BUNDLE.json").unlink()
        source = self.cleanup / "scripts/audit.py"
        source.write_text(source.read_text(encoding="utf-8") + "\nVALUE = 1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            bundle.validate_cleanup_source(self.cleanup)

    def test_public_fixture_recognition_is_exact_and_keeps_other_rules(self):
        name = "tools/code-cleanup-helper/scripts/exposure_scope_regression.py"
        text = (self.root / name).read_text(encoding="utf-8")
        self.assertEqual(reviewed_fixture_rules(name, text), {"user-home-path"})
        self.assertFalse(public_privacy_findings(name, text))
        self.assertIn("user-home-path", public_privacy_findings("README.md", text))
        changed = text + "\n# extra data\n"
        self.assertFalse(reviewed_fixture_rules(name, changed))
        self.assertIn("user-home-path", public_privacy_findings(name, changed))


def run_self_test():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CleanupBundleTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("bundled Cleanup regression failed")
    print("bundled Cleanup regression GREEN")


if __name__ == "__main__":
    run_self_test()
