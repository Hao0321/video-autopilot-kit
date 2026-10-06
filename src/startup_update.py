# -*- coding: utf-8 -*-
"""Bounded public-runtime auto-update and workspace migration hook."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REEXEC_FLAG = "VIDEO_AUTOPILOT_UPDATE_REEXEC"
# Files on disk changed under this process: restart before importing more.
REEXEC_STATUSES = frozenset({"UPDATED", "INTERRUPTED_TRANSACTION_RECOVERED"})
NOTICE_STATUSES = frozenset({
    "CONFIRM_REQUIRED", "CHECK_FAILED", "LOCKED",
    "INTERRUPTED_TRANSACTION", "INTERRUPTED_TRANSACTION_RECOVERED",
})


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


def _windows_host() -> bool:
    return os.name == "nt"


def _reexec_current_process() -> None:
    """Restart this command so it imports one consistent set of modules."""
    command = [sys.executable, *sys.argv]
    if _windows_host():
        # Windows _execv spawns a detached child, reports success to the caller
        # at once and re-splits arguments containing spaces.  Wait for a
        # list-quoted child instead and propagate its exit status.
        raise SystemExit(subprocess.call(command))
    os.execv(sys.executable, command)


def _public_error(error: Exception) -> str:
    """Describe an updater failure without echoing a machine-local path."""
    try:
        from release_manager import public_error_text
    except Exception:
        return type(error).__name__
    return public_error_text(error)


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
            result = {"status": "CHECK_FAILED", "error": _public_error(exc), "non_blocking": True}

    if result.get("status") in NOTICE_STATUSES:
        print("[video-autopilot update] " + json.dumps(result, ensure_ascii=False), file=sys.stderr)
    if result.get("status") in REEXEC_STATUSES:
        os.environ[REEXEC_FLAG] = "1"
        _reexec_current_process()

    workspace = _migrate_workspace()
    return {"status": result.get("status"), "update": result, "workspace": workspace}


if __name__ == "__main__":
    print(json.dumps(ensure_current(), ensure_ascii=False, indent=2))
