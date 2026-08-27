#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the calibrated architecture evaluator against the canonical skill.

The evaluator remains an external development instrument. Runtime editing and
public installations do not depend on it; missing tooling is reported rather
than silently treated as a pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _config_path() -> Path:
    candidates = (HERE / "audit.config.json", HERE.parent / "audit.config.json")
    return next((path for path in candidates if path.is_file()), candidates[0])


def _default_cleanup() -> Path:
    candidates = (
        Path.home() / ".codex" / "skills" / "code-cleanup-helper" / "scripts" / "audit.py",
        HERE.parent / "code-cleanup-helper" / "scripts" / "audit.py",
        HERE.parent / "codex-skill" / "code-cleanup-helper" / "scripts" / "audit.py",
        HERE.parent / "tools" / "code-cleanup-helper" / "scripts" / "audit.py",
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def evaluate(cleanup: Path | None = None) -> dict:
    cleanup = cleanup or _default_cleanup()
    config = _config_path()
    if not cleanup.is_file():
        return {
            "status": "NOT_CHECKED",
            "reason": f"cleanup evaluator missing: {cleanup}",
            "evaluator": str(cleanup),
            "config": str(config),
        }
    completed = subprocess.run(
         [sys.executable, str(cleanup), str(HERE.parent), "--mode", "architecture",
         "--config", str(config), "--format", "json"],
        cwd=HERE.parent, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, check=False,
    )
    if completed.returncode not in (0, 1):
        return {
            "status": "ERROR", "returncode": completed.returncode,
            "stderr": completed.stderr[-2000:], "evaluator": str(cleanup),
        }
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "reason": str(exc), "stdout": completed.stdout[-2000:]}
    summary = report.get("summary") or {}
    architecture = report.get("architecture") or {}
    return {
        "status": "GREEN" if int(summary.get("fail", 0)) == 0 else "RED",
        "evaluator": str(cleanup),
        "evaluator_sha256": _sha256(cleanup.with_name("audit_core.py")),
        "config": str(config),
        "config_sha256": _sha256(config),
        "report_schema": report.get("schema_version"),
        "summary": summary,
        "cycles": architecture.get("cycles", []),
        "layer_violations": architecture.get("layer_violations", []),
        "forbidden_dependencies": architecture.get("forbidden_dependencies", []),
        "parse_errors": architecture.get("parse_errors", []),
        "review_count": summary.get("review", 0),
        "report": report,
    }


def self_test(*, require_evaluator: bool = False) -> None:
    missing = evaluate(HERE / "definitely-missing-audit.py")
    assert missing["status"] == "NOT_CHECKED"
    result = evaluate()
    assert result["status"] in {"GREEN", "RED", "NOT_CHECKED"}
    if require_evaluator and result["status"] == "NOT_CHECKED":
        raise AssertionError(result["reason"])
    if result["status"] != "NOT_CHECKED":
        assert result["evaluator_sha256"] and result["config_sha256"]
        assert result["report_schema"]
    print("architecture_gate self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrated architecture gate")
    parser.add_argument("command", choices=("audit", "selftest"), nargs="?", default="audit")
    parser.add_argument("--output")
    parser.add_argument("--require-evaluator", action="store_true")
    args = parser.parse_args()
    if args.command == "selftest":
        self_test(require_evaluator=args.require_evaluator)
        return 0
    result = evaluate()
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    printable = {key: value for key, value in result.items() if key != "report"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
