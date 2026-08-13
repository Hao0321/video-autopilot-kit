#!/usr/bin/env python3
"""Dependency-free smoke tests for the audit engine."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from audit_core import declared_versions, normalized_paragraphs, run_audit


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_parsers() -> None:
    versions = declared_versions("# Doc\n目前版本：**v2.3.4**\n散文提到 v9.9.9 不算宣告\n## v2.2.0 — old\n")
    if versions != ["v2.3.4", "v2.2.0"]:
        raise AssertionError(f"version declaration parser failed: {versions}")
    paragraphs = normalized_paragraphs("before\n\n```text\nhidden\n```\n\nafter\n", 1)
    if [item[2] for item in paragraphs] != ["before", "after"]:
        raise AssertionError(f"markdown fence filtering failed: {paragraphs}")


def test_general_audit() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-audit-") as raw:
        root = Path(raw) / "sample-skill"
        root.mkdir()
        write(root / "SKILL.md", "---\nname: sample-skill\ndescription: sample\n---\n# Sample\nCases 1-1\n")
        write(root / "agents" / "openai.yaml", 'interface:\n  default_prompt: "Use $sample-skill to audit this."\n')
        write(root / "references" / "cases.md", "# Cases\n\n## Case 1: A\n\n## Case 2: B\n")
        write(root / "references" / "broken.md", "[missing](nope.md)\n")
        write(root / "references" / "notes.md", "[note](這是一段說明，不是路徑)\n")
        write(root / "leak.txt", "Example path: C:\\Users\\sample-user\\private\n")
        write(root / "nested" / "SKILL.md", "---\nname: nested\ndescription: nested test\n---\n# Nested\n")
        write(root / "bad-frontmatter" / "SKILL.md", "---\nname: bad-frontmatter\n---\n# Bad\n")
        write(root / "bad-frontmatter" / "agents" / "openai.yaml", 'interface:\n  default_prompt: "Use $bad-frontmatter."\n')
        write(root / "audit.config.json", json.dumps({
            "drift_assertions": [
                {"id": "forbidden-old-value", "files": ["SKILL.md"], "pattern": "Cases 1-1", "expected_count": 0},
                {"id": "invalid-regex", "files": ["SKILL.md"], "pattern": "["},
            ],
            "privacy": {"tokens": ["C:\\Users\\sample-user"], "patterns": ["sample-user\\\\private", "["], "allow": []},
        }))
        report = run_audit(root, "all")
        codes = {item["code"] for item in report["findings"] if item["status"] == "FAIL"}
        expected = {
            "range-drift", "broken-link", "forbidden-old-value", "privacy-token",
            "privacy-pattern", "agents-metadata", "skill-frontmatter",
            "privacy-pattern-invalid", "assertion-pattern-invalid",
        }
        if expected - codes:
            raise AssertionError(f"self-test missing expected findings: {sorted(expected - codes)}")
        broken = [item for item in report["findings"] if item["code"] == "broken-link"]
        if len(broken) != 1 or broken[0]["path"] != "references/broken.md":
            raise AssertionError(f"pseudo-link filter failed: {broken}")
        nested = [item for item in report["findings"] if item["code"] == "agents-metadata"]
        if not nested or nested[0]["path"] != "nested":
            raise AssertionError(f"nested skill metadata was not audited: {nested}")


def test_architecture_graph() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-architecture-") as raw:
        root = Path(raw) / "sample-project"
        root.mkdir()
        write(root / "core.py", "from ui import render\n\ndef shared(value):\n    total = value + 1\n    total *= 2\n    total -= 3\n    return total\n")
        write(root / "ui.py", "from core import shared\n\ndef render(value):\n    total = value + 1\n    total *= 2\n    total -= 3\n    return total\n")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "layers": [
                {"name": "core", "patterns": ["core.py"], "may_depend_on": []},
                {"name": "ui", "patterns": ["ui.py"], "may_depend_on": ["core"]},
            ],
            "function_warning_lines": 3, "function_severe_lines": 4,
            "duplicate_function_min_lines": 3, "duplicate_function_min_nodes": 4,
        }}))
        report = run_audit(root, "architecture")
        codes = {item["code"] for item in report["findings"] if item["status"] == "FAIL"}
        expected = {"dependency-cycle", "layer-violation", "duplicate-function-body", "function-too-long"}
        if expected - codes:
            raise AssertionError(f"architecture audit missing expected findings: {sorted(expected - codes)}")
        architecture = report.get("architecture", {})
        if architecture.get("modules") != 2 or len(architecture.get("edges", [])) != 2:
            raise AssertionError(f"architecture graph incomplete: {architecture}")


def test_import_resolution() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-script-import-") as raw:
        root = Path(raw) / "script-import-project"
        root.mkdir()
        write(root / "scripts" / "a.py", "from b import value\n")
        write(root / "scripts" / "b.py", "value = 1\n")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "required_dependencies": [{"source": "scripts/a.py", "target": "scripts/b.py"}],
        }}))
        report = run_audit(root, "architecture")
        edges = {(item["source"], item["target"]) for item in report["architecture"]["edges"]}
        if edges != {("scripts.a", "scripts.b")} or report["summary"]["fail"]:
            raise AssertionError(f"script-style sibling import failed: {report}")
    with tempfile.TemporaryDirectory(prefix="cleanup-missing-dependency-") as raw:
        root = Path(raw) / "missing-dependency-project"
        root.mkdir()
        write(root / "scripts" / "a.py", "value = 1\n")
        write(root / "scripts" / "b.py", "value = 2\n")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "required_dependencies": [{"source": "scripts/a.py", "target": "scripts/b.py"}],
        }}))
        report = run_audit(root, "architecture")
        if not any(item["code"] == "required-dependency-missing" for item in report["findings"]):
            raise AssertionError("missing required dependency did not fail calibration")
    with tempfile.TemporaryDirectory(prefix="cleanup-absolute-import-") as raw:
        root = Path(raw) / "absolute-import-project"
        root.mkdir()
        write(root / "external.py", "value = 1\n")
        write(root / "pkg" / "a.py", "from external import value\n")
        write(root / "pkg" / "external.py", "value = 2\n")
        report = run_audit(root, "architecture")
        edges = {(item["source"], item["target"]) for item in report["architecture"]["edges"]}
        if ("pkg.a", "external") not in edges or ("pkg.a", "pkg.external") in edges:
            raise AssertionError(f"absolute import was shadowed by sibling fallback: {edges}")
    with tempfile.TemporaryDirectory(prefix="cleanup-package-stdlib-") as raw:
        root = Path(raw) / "package-stdlib-project"
        root.mkdir()
        write(root / "pkg" / "__init__.py", "from .store import value\n")
        write(root / "pkg" / "store.py",
              "import json\nfrom datetime import datetime\nfrom pathlib import Path\nvalue = (json, datetime, Path)\n")
        report = run_audit(root, "architecture")
        edges = {(item["source"], item["target"]) for item in report["architecture"]["edges"]}
        if edges != {("pkg", "pkg.store")} or report["summary"]["fail"]:
            raise AssertionError(f"stdlib import falsely resolved to package facade: {report}")


def test_function_thresholds() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-review-") as raw:
        root = Path(raw) / "review-project"
        root.mkdir()
        write(root / "medium.py", "def medium(value):\n    value += 1\n    value *= 2\n    value -= 3\n    return value\n")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "function_warning_lines": 3, "function_severe_lines": 10,
        }}))
        report = run_audit(root, "architecture")
        reviews = [item for item in report["findings"] if item["status"] == "REVIEW"]
        if report["summary"]["fail"] or not any(item["code"] == "function-long" for item in reviews):
            raise AssertionError(f"medium function must be REVIEW, not FAIL: {report}")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "function_warning_lines": 3, "function_severe_lines": 4,
            "function_exceptions": [{
                "path": "medium.py", "name": "medium", "max_lines": 5,
                "reason": "linear compatibility fixture", "expires_on": "2099-12-31",
            }],
        }}))
        excepted = run_audit(root, "architecture")
        if not any(item["code"] == "function-exception-active" for item in excepted["findings"]):
            raise AssertionError(f"bounded exception was not reported: {excepted}")
        if excepted["summary"]["fail"]:
            raise AssertionError(f"valid bounded exception should prevent severe FAIL: {excepted}")


def test_file_thresholds() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-file-threshold-") as raw:
        root = Path(raw) / "file-threshold-project"
        root.mkdir()
        write(root / "warning.py", "\n".join(f"warning_{index} = {index}" for index in range(5)) + "\n")
        write(root / "severe.py", "\n".join(f"severe_{index} = {index}" for index in range(8)) + "\n")
        write(root / "audit.config.json", json.dumps({"thresholds": {
            "code_warning": 3,
            "code_severe": 6,
        }}))
        report = run_audit(root, "a")
        warning = [item for item in report["findings"] if item["path"] == "warning.py"]
        severe = [item for item in report["findings"] if item["path"] == "severe.py"]
        if len(warning) != 1 or warning[0]["code"] != "file-long" or warning[0]["status"] != "REVIEW":
            raise AssertionError(f"warning-size file must be REVIEW: {warning}")
        if len(severe) != 1 or severe[0]["code"] != "file-too-long" or severe[0]["status"] != "FAIL":
            raise AssertionError(f"severe-size file must be FAIL: {severe}")


def test_json_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-json-contract-") as raw:
        root = Path(raw) / "json-project"
        root.mkdir()
        write(root / "clean.py", "def clean():\n    return True\n")
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("audit.py")), str(root),
             "--mode", "architecture", "--format", "json"],
            capture_output=True, text=True, encoding="utf-8", errors="strict", check=False,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        if completed.returncode != 0:
            raise AssertionError(f"JSON CLI exited nonzero: {completed.stderr}")
        decoder = json.JSONDecoder()
        _, offset = decoder.raw_decode(completed.stdout)
        if completed.stdout[offset:].strip():
            raise AssertionError("JSON CLI emitted trailing non-JSON output")


def main() -> int:
    test_parsers()
    test_general_audit()
    test_architecture_graph()
    test_import_resolution()
    test_function_thresholds()
    test_file_thresholds()
    test_json_contract()
    print("self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
