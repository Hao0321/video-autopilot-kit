#!/usr/bin/env python3
"""Dependency-free smoke tests for the audit engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from audit_core import collect_files, declared_versions, normalized_paragraphs, run_audit
from check_audit_snapshot import run_self_test as run_audit_snapshot_self_test
from check_build_receipt import run_self_test as run_build_receipt_self_test
from check_context_budget import run_self_test as run_context_budget_self_test
from check_security_assessment import run_self_test as run_security_assessment_self_test
from check_skill_revision import run_self_test as run_skill_revision_self_test
from sync_public import equivalent_files

def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")

def _single_update_finding(report: dict) -> dict:
    matches = [item for item in report["findings"] if item["dimension"] == 11]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one D11 update finding: {matches}")
    return matches[0]

def _update_coverage_class_controls(origin, root):
    write(root / "update-evidence.json", '{"fixture": true}\n')
    cases = [
        ("no-origin", {"classification": "no-origin"}, "NOT_CHECKED"),
        ("manual-only", {"classification": "manual-only", "canonical_origin": origin}, "REVIEW"),
        ("check-only", {
            "classification": "check-only", "canonical_origin": origin,
            "evidence": ["update-evidence.json"],
        }, "REVIEW"),
        ("safe-auto-update", {
            "classification": "safe-auto-update", "canonical_origin": origin,
            "evidence": ["update-evidence.json"],
        }, "REVIEW"),
        ("managed", {
            "classification": "managed", "canonical_origin": "npm:example-package",
            "manager": "npm", "evidence": ["update-evidence.json"],
        }, "REVIEW"),
    ]
    for expected, config, expected_status in cases:
        write(root / "audit.config.json", json.dumps({"update_coverage": config}))
        report = run_audit(root, "all")
        finding = _single_update_finding(report)
        coverage = report["update_coverage"]
        if coverage["classification"] != expected or finding["status"] != expected_status:
            raise AssertionError(f"update class {expected} drifted: {coverage}, {finding}")
        if expected in {"managed", "safe-auto-update"}:
            if finding["status"] == "PASS" or not coverage["requires_deep_validation"]:
                raise AssertionError(f"strong update claim produced a false green: {coverage}, {finding}")
    return config, finding, report


def test_update_coverage() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-update-coverage-") as raw:
        root = Path(raw) / "target"
        root.mkdir()
        write(root / "app.py", "value = 1\n")

        for mode in ("a", "b", "architecture", "all"):
            report = run_audit(root, mode)
            finding = _single_update_finding(report)
            coverage = report.get("update_coverage")
            if report.get("schema_version") != "1.2" or not isinstance(coverage, dict):
                raise AssertionError(f"update coverage report contract missing in {mode}: {report}")
            if coverage["classification"] != "no-origin" or finding["status"] != "NOT_CHECKED":
                raise AssertionError(f"{mode} did not conservatively classify no-origin: {coverage}")

        origin = "https://github.com/example/downstream.git"
        write(root / "audit.config.json", json.dumps({
            "update_coverage": {"canonical_origin": origin},
        }))
        inferred = run_audit(root, "architecture")
        if inferred["update_coverage"]["classification"] != "manual-only":
            raise AssertionError(f"known origin did not default to manual-only: {inferred['update_coverage']}")
        if inferred["update_coverage"]["origin_source"] != "config":
            raise AssertionError(f"configured origin provenance was lost: {inferred['update_coverage']}")

        write(root / "audit.config.json", json.dumps({
            "update_coverage": {"canonical_origin": "https://secret-token" + "@github.com/example/downstream.git"},
        }))
        redacted = run_audit(root, "architecture")["update_coverage"]
        if "secret-token" in redacted["canonical_origin"] or not redacted["origin_redacted"]:
            raise AssertionError(f"credential-bearing origin leaked into report: {redacted}")

        config, finding, report = _update_coverage_class_controls(origin, root)
        write(root / "audit.config.json", json.dumps({
            "exclude": ["update-evidence.json"],
            "update_coverage": {
                "classification": "safe-auto-update", "canonical_origin": origin,
                "evidence": ["update-evidence.json"],
            },
        }))
        excluded_evidence = run_audit(root, "architecture")
        inventory_paths = {item["path"] for item in excluded_evidence["inventory"]}
        if "update-evidence.json" not in inventory_paths:
            raise AssertionError("update evidence was omitted from freshness inventory")

        outside = Path(raw) / "outside.json"
        write(outside, "{}\n")
        invalid_cases = [
            {"classification": "safe-auto-update", "canonical_origin": origin},
            {"classification": "no-origin", "canonical_origin": origin},
            {"classification": "managed", "canonical_origin": origin, "evidence": ["update-evidence.json"]},
            {"classification": "automatic", "canonical_origin": origin},
            {"canonical_origin": origin, "evidence": ["update-evidence.json"]},
            {"classification": "check-only", "canonical_origin": origin, "evidence": ["update-evidence.json", "./update-evidence.json"]},
            {"classification": "safe-auto-update", "canonical_origin": origin, "evidence": ["../outside.json"]},
        ]
        for config in invalid_cases:
            write(root / "audit.config.json", json.dumps({"update_coverage": config}))
            report = run_audit(root, "all")
            finding = _single_update_finding(report)
            if finding["status"] != "FAIL" or finding["code"] != "update-coverage-invalid":
                raise AssertionError(f"invalid update coverage produced a false green: {report['update_coverage']}")
            if report["update_coverage"]["classification"] not in {"manual-only", "no-origin"}:
                raise AssertionError(f"invalid update coverage did not fail closed: {report['update_coverage']}")

def test_git_origin_scope() -> None:
    git = shutil.which("git")
    if not git:
        return
    with tempfile.TemporaryDirectory(prefix="cleanup-update-git-scope-") as raw:
        base = Path(raw)
        repo = base / "monorepo"
        nested = repo / "independent-skill"
        nested.mkdir(parents=True)
        write(nested / "SKILL.md", "---\nname: independent-skill\ndescription: fixture\n---\n# Fixture\n")
        for args in (
            [git, "init", "--quiet", str(repo)],
            [git, "-C", str(repo), "remote", "add", "origin", "https://github.com/example/monorepo.git"],
        ):
            completed = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if completed.returncode != 0:
                raise AssertionError(f"git origin fixture failed: {completed.stderr}")

        for mode in ("a", "b", "architecture", "all"):
            nested_report = run_audit(nested, mode)
            if nested_report["update_coverage"]["classification"] != "no-origin":
                raise AssertionError(f"nested target inherited parent Git origin in {mode}: {nested_report['update_coverage']}")
        write(nested / "audit.config.json", json.dumps({
            "update_coverage": {"classification": "no-origin"},
        }))
        explicit_no_origin = run_audit(nested, "architecture")
        if _single_update_finding(explicit_no_origin)["status"] != "NOT_CHECKED":
            raise AssertionError(f"parent Git origin invalidated explicit no-origin: {explicit_no_origin['update_coverage']}")

        root_report = run_audit(repo, "architecture")
        root_coverage = root_report["update_coverage"]
        if root_coverage["classification"] != "manual-only" or root_coverage["origin_source"] != "git":
            raise AssertionError(f"audit-root Git origin was not detected: {root_coverage}")

        outside = base / "not-a-repo"
        outside.mkdir()
        injected = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "remote.origin.url",
            "GIT_CONFIG_VALUE_0": "https://github.com/attacker/injected.git",
        }
        previous = {key: os.environ.get(key) for key in injected}
        try:
            os.environ.update(injected)
            outside_report = run_audit(outside, "architecture")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        if outside_report["update_coverage"]["classification"] != "no-origin":
            raise AssertionError(f"ambient Git config forged an origin: {outside_report['update_coverage']}")
