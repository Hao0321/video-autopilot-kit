#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example 02 — exercise the Editkin v4 durable workflow contract.

The self-test builds a temporary Editkin project and two fake source files, then
walks the complete receipt-bound DAG: material evidence, semantic records,
route/plugin discovery, edit-plan/v4 audit, atomic apply, render, human review
and outcome recording. It also proves the important failure cases stay blocked.

Run:
    python examples/02_caption_broll_match.py

Needs: Python 3.9+ only. No ffmpeg, desktop editor or real media.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "src" / "workflow_contract.py"


def main() -> int:
    completed = subprocess.run(
        [sys.executable, str(WORKFLOW), "selftest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode

    payload = json.loads(completed.stdout)
    result = payload["result"]
    print("Editkin v4 workflow contract:", result["selftest"])
    print("completed steps:", result["completed_steps"])
    for name in (
        "parallel_prepare",
        "parallel_route_plugin",
        "contract_downgrade_rejected",
        "legacy_plan_rejected",
        "tampered_keyframe_rejected",
        "unviewed_semantic_evidence_rejected",
        "interrupted_apply_requires_reconcile",
        "machine_human_review_rejected",
        "source_drift_rejected",
    ):
        print(f"  {name}: {result[name]}")

    if result["selftest"] != "GREEN" or not all(
        value is True for key, value in result.items()
        if key not in {"selftest", "completed_steps"}
    ):
        raise RuntimeError("Editkin v4 workflow contract self-test was not GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
