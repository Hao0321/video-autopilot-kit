# -*- coding: utf-8 -*-
"""Bounded public-runtime auto-update and workspace migration hook."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REEXEC_FLAG = "VIDEO_AUTOPILOT_UPDATE_REEXEC"


def _manifest() -> dict:
    return json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))


def _migrate_workspace() -> dict:
    from project_paths import discover_project_root
    from workspace_migrator import migrate
    # Code may live in a nested distributable kit while the operational
    # workspace (videos, publish hub, review state) is its enclosing project.
    # Resolve the data root independently; standalone public installs still
    # resolve to ROOT when launched from their own directory.
    return migrate(discover_project_root(ROOT), apply=True)


def ensure_current() -> dict:
    """Check at the manifest interval, re-exec after update, then migrate data shape."""
    if os.environ.get(REEXEC_FLAG) == "1":
        return {"status": "REEXECUTED", "workspace": _migrate_workspace()}

    manifest = _manifest()
    policy = manifest.get("auto_update") or {}
    result: dict = {"status": "DISABLED"}
    if policy.get("channel"):
        try:
            from release_manager import auto_update
            result = auto_update(
                str(policy["channel"]), ROOT,
                float(policy.get("check_interval_hours") or 24),
            )
        except Exception as exc:  # editing must remain available offline
            result = {"status": "CHECK_FAILED", "error": str(exc), "non_blocking": True}

    if result.get("status") == "UPDATED":
        os.environ[REEXEC_FLAG] = "1"
        os.execv(sys.executable, [sys.executable, *sys.argv])

    workspace = _migrate_workspace()
    if result.get("status") in {"CONFIRM_REQUIRED", "CHECK_FAILED"}:
        print("[video-autopilot update] " + json.dumps(result, ensure_ascii=False), file=sys.stderr)
    return {"status": result.get("status"), "update": result, "workspace": workspace}


if __name__ == "__main__":
    print(json.dumps(ensure_current(), ensure_ascii=False, indent=2))
