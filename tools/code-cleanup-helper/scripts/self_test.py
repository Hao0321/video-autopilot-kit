#!/usr/bin/env python3
"""Dependency-free smoke tests for the audit engine."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from audit_core import collect_files, declared_versions, normalized_paragraphs, run_audit
from check_audit_snapshot import run_self_test as run_audit_snapshot_self_test
from check_build_receipt import run_self_test as run_build_receipt_self_test
from check_skill_revision import run_self_test as run_skill_revision_self_test
from sync_public import (
    equivalent_files, managed_paths, privacy_violations, safe_destination, write_manifest,
)


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


def test_root_level_double_star_exclusion() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-root-glob-") as raw:
        root = Path(raw) / "root-glob-project"
        root.mkdir()
        write(root / "keep.py", "value = 1\n")
        write(root / "_runtime" / "root.json", "{}\n")
        write(root / "pkg" / "_runtime" / "nested.json", "{}\n")
        files = collect_files(root, {"exclude": ["**/_runtime/**"]})
        relative = {path.relative_to(root).as_posix() for path in files}
        if relative != {"keep.py"}:
            raise AssertionError(f"**/ root exclusion semantics failed: {sorted(relative)}")


def test_public_sync_guard() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-public-sync-") as raw:
        root = Path(raw)
        candidate = root / "candidate.md"
        write(candidate, "contains private-marker")
        config = {"sync": {"privacy": {"tokens": ["private-marker"], "patterns": []}}}
        if not privacy_violations([(candidate, "candidate.md")], config):
            raise AssertionError("public sync privacy marker was not blocked")
        try:
            safe_destination(root, "../escape.txt")
        except ValueError:
            pass
        else:
            raise AssertionError("public sync accepted a path outside its root")
        write_manifest(root, ["safe.md"])
        if managed_paths(root) != {"safe.md"}:
            raise AssertionError("public sync managed manifest did not round-trip")


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


def test_cross_language_architecture_boundary() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-cross-language-") as raw:
        root = Path(raw) / "cross-language-project"
        root.mkdir()
        write(root / "src" / "app.ts", "import { plan } from './plan';\nexport const value = plan();\n")
        write(root / "native" / "core.rs", "pub fn plan() -> usize { 1 }\n")
        report = run_audit(root, "architecture")
        finding = next(
            (item for item in report["findings"]
             if item["code"] == "cross-language-architecture-not-checked"),
            None,
        )
        if not finding or finding["status"] != "NOT_CHECKED":
            raise AssertionError(f"cross-language-only repository was falsely cleared: {report}")
        if finding["details"]["languages"] != {"Rust": 1, "TypeScript": 1}:
            raise AssertionError(f"cross-language inventory drifted: {finding}")
        if report["architecture"].get("modules") != 0:
            raise AssertionError("non-Python sources were misrepresented as parsed Python modules")

    with tempfile.TemporaryDirectory(prefix="cleanup-mixed-language-") as raw:
        root = Path(raw) / "mixed-language-project"
        root.mkdir()
        write(root / "clean.py", "value = 1\n")
        write(root / "ui.tsx", "export const Ui = () => null;\n")
        report = run_audit(root, "architecture")
        codes = {(item["status"], item["code"]) for item in report["findings"]}
        if ("PASS", "architecture") not in codes or (
            "NOT_CHECKED", "cross-language-architecture-not-checked"
        ) not in codes:
            raise AssertionError(f"mixed-language boundary was not kept visible: {report}")


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


def test_dependency_hotspot_exceptions() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-hotspot-exception-") as raw:
        root = Path(raw) / "hotspot-project"
        root.mkdir()
        write(root / "foundation.py", "value = 1\n")
        for index in range(3):
            write(root / f"consumer_{index}.py", "from foundation import value\n")
        write(root / "audit.config.json", json.dumps({"architecture": {
            "max_module_fan_in": 1,
            "module_hotspot_exceptions": [{
                "path": "foundation.py", "max_fan_in": 3, "max_out_degree": 0,
                "reason": "stable dependency-free foundation fixture", "expires_on": "2099-12-31",
            }],
        }}))
        excepted = run_audit(root, "architecture")
        matches = [item for item in excepted["findings"]
                   if item["code"] == "dependency-hotspot-exception-active"]
        if len(matches) != 1 or matches[0]["status"] != "REVIEW":
            raise AssertionError(f"bounded hotspot exception was not reported: {excepted}")
        if excepted["summary"]["fail"]:
            raise AssertionError(f"valid bounded hotspot exception should prevent FAIL: {excepted}")
        write(root / "consumer_3.py", "from foundation import value\n")
        exceeded = run_audit(root, "architecture")
        if not any(item["code"] == "dependency-hotspot" and item["status"] == "FAIL"
                   for item in exceeded["findings"]):
            raise AssertionError("hotspot exceeding its bounded exception did not fail")


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


def test_module_candidate_dimension() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-module-candidate-") as raw:
        root = Path(raw) / "module-candidate-project"
        root.mkdir()
        repeated = "This repeated workflow paragraph is intentionally long enough to become a deterministic extraction candidate.\n"
        for index in range(3):
            write(root / f"doc-{index}.md", repeated)
        report = run_audit(root, "a")
        candidates = [item for item in report["findings"] if item["dimension"] == 3]
        if len(candidates) != 1 or candidates[0]["status"] != "REVIEW":
            raise AssertionError(f"three-use module candidate was not reported: {candidates}")
        write(root / "audit.config.json", json.dumps({"duplicate_min_occurrences": 4}))
        clean = run_audit(root, "a")
        passes = [item for item in clean["findings"] if item["dimension"] == 3]
        if len(passes) != 1 or passes[0]["status"] != "PASS":
            raise AssertionError(f"checked-clean module dimension was absent: {passes}")


def test_artifact_set_assertions() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        for folder in ("ads", "supplier"):
            (root / folder).mkdir()
            for name in ("a001.webp", "a002.webp"):
                (root / folder / name).write_bytes(b"valid-artifact")
        config = {
            "artifact_set_assertions": [{
                "id": "product-images",
                "left_glob": "ads/*.webp",
                "right_glob": "supplier/*.webp",
                "key_pattern": r"^(a\d{3})\.webp$",
                "expected_count": 2,
                "min_bytes": 4,
                "forbid_globs": ["supplier/*.png"],
            }],
        }
        write(root / "audit.config.json", json.dumps(config))
        clean = run_audit(root, "b")
        if not any(item["code"] == "artifact-set-assertion" and item["status"] == "PASS" for item in clean["findings"]):
            raise AssertionError(f"paired artifact control did not pass: {clean['findings']}")
        frozen = {item["path"] for item in clean["inventory"]}
        if not {"ads/a001.webp", "supplier/a001.webp"}.issubset(frozen):
            raise AssertionError(f"artifact bytes were absent from freshness inventory: {sorted(frozen)}")

        (root / "supplier/a002.webp").unlink()
        (root / "supplier/a001.png").write_bytes(b"duplicate-format")
        (root / "ads/a001.webp").write_bytes(b"x")
        broken = run_audit(root, "b")
        failures = [item for item in broken["findings"] if item["code"] == "artifact-set-drift"]
        if len(failures) != 1:
            raise AssertionError(f"artifact drift was not detected: {broken['findings']}")
        details = failures[0]["details"]
        if details["missing_from_right"] != ["a002"] or not details["forbidden"] or not details["undersized"]:
            raise AssertionError(f"artifact failure classes were incomplete: {details}")


def test_artifact_set_false_green_controls() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-artifact-controls-") as raw:
        root = Path(raw)
        (root / "assets").mkdir()
        (root / "assets/a001.webp").write_bytes(b"valid")
        base = {
            "id": "paired-assets", "left_glob": "assets/*.webp",
            "right_glob": "assets/*.webp", "key_pattern": r"^(a\d{3})\.webp$",
            "expected_count": 1,
        }
        write(root / "audit.config.json", json.dumps({"artifact_set_assertions": [base]}))
        overlap = run_audit(root, "b")
        drift = [item for item in overlap["findings"] if item["code"] == "artifact-set-drift"]
        if not drift or drift[0]["details"]["left_right_overlap"] != ["assets/a001.webp"]:
            raise AssertionError(f"left/right overlap produced a false green: {overlap['findings']}")

        invalid_cases = [
            {**base, "left_glob": "missing-left/*.webp", "right_glob": "missing-right/*.webp", "expected_count": 0},
            {key: value for key, value in base.items() if key != "expected_count"},
            {**base, "key_pattern": r"^a\d{3}\.webp$"},
            {**base, "forbid_globs": "assets/*.png"},
        ]
        for index, assertion in enumerate(invalid_cases):
            write(root / "audit.config.json", json.dumps({"artifact_set_assertions": [assertion]}))
            report = run_audit(root, "b")
            if not any(item["code"] == "artifact-set-invalid" for item in report["findings"]):
                raise AssertionError(f"invalid artifact config {index} produced a false green: {report['findings']}")


def test_sync_line_endings() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-sync-newlines-") as raw:
        root = Path(raw)
        source, destination = root / "private.md", root / "public.md"
        source.write_bytes(b"first\nsecond\n")
        destination.write_bytes(b"first\r\nsecond\r\n")
        if not equivalent_files(source, destination, normalize_text=True):
            raise AssertionError("normalized sync treated LF/CRLF as content drift")
        if equivalent_files(source, destination, normalize_text=False):
            raise AssertionError("byte-exact sync ignored LF/CRLF drift")
        destination.write_bytes(b"first\r\nchanged\r\n")
        if equivalent_files(source, destination, normalize_text=True):
            raise AssertionError("normalized sync hid a semantic text change")


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
    run_skill_revision_self_test()
    test_parsers()
    test_root_level_double_star_exclusion()
    test_public_sync_guard()
    test_general_audit()
    test_architecture_graph()
    test_cross_language_architecture_boundary()
    test_import_resolution()
    test_function_thresholds()
    test_dependency_hotspot_exceptions()
    test_file_thresholds()
    test_module_candidate_dimension()
    test_artifact_set_assertions()
    test_artifact_set_false_green_controls()
    test_sync_line_endings()
    test_json_contract()
    run_audit_snapshot_self_test()
    run_build_receipt_self_test()
    print("self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
