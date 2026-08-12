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


def main() -> int:
    versions = declared_versions("# Doc\n目前版本：**v2.3.4**\n散文提到 v9.9.9 不算宣告\n## v2.2.0 — old\n")
    if versions != ["v2.3.4", "v2.2.0"]:
        raise AssertionError(f"version declaration parser failed: {versions}")
    paragraphs = normalized_paragraphs("before\n\n```text\nhidden\n```\n\nafter\n", 1)
    if [item[2] for item in paragraphs] != ["before", "after"]:
        raise AssertionError(f"markdown fence filtering failed: {paragraphs}")
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
                {
                    "id": "forbidden-old-value",
                    "files": ["SKILL.md"],
                    "pattern": "Cases 1-1",
                    "expected_count": 0,
                },
                {"id": "invalid-regex", "files": ["SKILL.md"], "pattern": "["},
            ],
            "privacy": {
                "tokens": ["C:\\Users\\sample-user"],
                "patterns": ["sample-user\\\\private", "["],
                "allow": [],
            },
        }))
        report = run_audit(root, "all")
        codes = {item["code"] for item in report["findings"] if item["status"] == "FAIL"}
        expected = {
            "range-drift", "broken-link", "forbidden-old-value", "privacy-token",
            "privacy-pattern", "agents-metadata", "skill-frontmatter",
            "privacy-pattern-invalid",
            "assertion-pattern-invalid",
        }
        missing = expected - codes
        if missing:
            raise AssertionError(f"self-test missing expected findings: {sorted(missing)}")
        broken = [item for item in report["findings"] if item["code"] == "broken-link"]
        if len(broken) != 1 or broken[0]["path"] != "references/broken.md":
            raise AssertionError(f"pseudo-link filter failed: {broken}")
        nested = [item for item in report["findings"] if item["code"] == "agents-metadata"]
        if not nested or nested[0]["path"] != "nested":
            raise AssertionError(f"nested skill metadata was not audited: {nested}")
    with tempfile.TemporaryDirectory(prefix="cleanup-architecture-") as raw:
        root = Path(raw) / "sample-project"
        root.mkdir()
        write(root / "core.py", "from ui import render\n\ndef shared(value):\n    total = value + 1\n    total *= 2\n    total -= 3\n    return total\n")
        write(root / "ui.py", "from core import shared\n\ndef render(value):\n    total = value + 1\n    total *= 2\n    total -= 3\n    return total\n")
        write(root / "audit.config.json", json.dumps({
            "architecture": {
                "layers": [
                    {"name": "core", "patterns": ["core.py"], "may_depend_on": []},
                    {"name": "ui", "patterns": ["ui.py"], "may_depend_on": ["core"]},
                ],
                "function_warning_lines": 3,
                "function_severe_lines": 4,
                "duplicate_function_min_lines": 3,
                "duplicate_function_min_nodes": 4,
            },
        }))
        report = run_audit(root, "architecture")
        codes = {item["code"] for item in report["findings"] if item["status"] == "FAIL"}
        expected = {"dependency-cycle", "layer-violation", "duplicate-function-body", "function-too-long"}
        missing = expected - codes
        if missing:
            raise AssertionError(f"architecture audit missing expected findings: {sorted(missing)}")
        architecture = report.get("architecture", {})
        if architecture.get("modules") != 2 or len(architecture.get("edges", [])) != 2:
            raise AssertionError(f"architecture graph incomplete: {architecture}")
    with tempfile.TemporaryDirectory(prefix="cleanup-review-") as raw:
        root = Path(raw) / "review-project"
        root.mkdir()
        write(root / "medium.py", "def medium(value):\n    value += 1\n    value *= 2\n    value -= 3\n    return value\n")
        write(root / "audit.config.json", json.dumps({
            "architecture": {
                "function_warning_lines": 3,
                "function_severe_lines": 10,
            },
        }))
        report = run_audit(root, "architecture")
        reviews = [item for item in report["findings"] if item["status"] == "REVIEW"]
        if report["summary"]["fail"] != 0 or not any(item["code"] == "function-long" for item in reviews):
            raise AssertionError(f"medium function must be REVIEW, not FAIL: {report}")
        write(root / "audit.config.json", json.dumps({
            "architecture": {
                "function_warning_lines": 3,
                "function_severe_lines": 4,
                "function_exceptions": [{
                    "path": "medium.py",
                    "name": "medium",
                    "max_lines": 5,
                    "reason": "linear compatibility fixture",
                    "expires_on": "2099-12-31",
                }],
            },
        }))
        excepted = run_audit(root, "architecture")
        if not any(item["code"] == "function-exception-active" for item in excepted["findings"]):
            raise AssertionError(f"bounded exception was not reported: {excepted}")
        if excepted["summary"]["fail"] != 0:
            raise AssertionError(f"valid bounded exception should prevent severe FAIL: {excepted}")
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
    print("self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
