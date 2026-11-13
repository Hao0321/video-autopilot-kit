"""Every runnable example in examples/README.md exits 0 on a clean checkout."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExampleTests(unittest.TestCase):
    def _run(self, name: str) -> subprocess.CompletedProcess:
        environment = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, str(ROOT / "examples" / name)], cwd=ROOT, env=environment,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)

    def test_02_workflow_contract_example(self):
        completed = self._run("02_caption_broll_match.py")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Editkin v4 workflow contract: GREEN", completed.stdout)
        self.assertIn("long-form session: GREEN", completed.stdout)

    def test_05_interview_example(self):
        completed = self._run("05_interview_plan.py")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("OK -- interview_gate demo passed", completed.stdout)


class NestedReportTests(unittest.TestCase):
    """The example's verdict covers nested self-test reports without running the DAG."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("example_02", ROOT / "examples" / "02_caption_broll_match.py")
        self.example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.example)
        self.report = {"selftest": "GREEN", "completed_steps": 18, "legacy_plan_rejected": True,
                       "longform_session": {"selftest": "GREEN", "completed_steps": 24, "chapters": 2,
                                            "one_render": True}}

    def test_green_report_with_nested_session(self):
        self.assertTrue(self.example._green(self.report))

    def test_nested_failure_or_non_bool_check_is_not_green(self):
        for path, value in ((("longform_session", "one_render"), False),
                            (("longform_session", "selftest"), "RED"),
                            (("legacy_plan_rejected",), "yes")):
            report = {**self.report, "longform_session": dict(self.report["longform_session"])}
            target = report
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.assertFalse(self.example._green(report), path)


if __name__ == "__main__":
    unittest.main()
