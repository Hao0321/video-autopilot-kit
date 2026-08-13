# -*- coding: utf-8 -*-
"""Non-destructive, idempotent workspace-schema migration.

The release updater owns code.  This module owns only generated workspace
structure: it may add the publishing hub and hardlink completed artifacts, but
it never removes or overwrites user media, profiles, credentials or unknown
files.  Legacy roots are reported for explicit review rather than moved by an
automatic update.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_paths import discover_project_root


SCHEMA_VERSION = 7
STATE_RELATIVE = Path(".video-autopilot") / "workspace-migration.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".workspace-migration-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _workspace_root(root: Path | None) -> Path:
    return root.expanduser().resolve() if root else discover_project_root(Path(__file__).resolve())


def plan(root: Path | None = None) -> dict[str, Any]:
    workspace = _workspace_root(root)
    hub = workspace / "videos" / "_PUBLISH_HUB"
    required = [
        hub / "READY", hub / "PUBLISHED", hub / "_STATE", hub / "_AUDIT",
    ]
    legacy = [workspace / "videos" / "_READY_TO_PUBLISH",
              workspace / "videos" / "_PUBLISHED"]
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": str(workspace),
        "missing_directories": [str(path) for path in required if not path.is_dir()],
        "legacy_roots_for_explicit_review": [str(path) for path in legacy if path.exists()],
        "protected_contract": "add generated structure; never delete or overwrite user media",
    }


def _pure_failures(workspace: Path) -> list[dict[str, Any]]:
    import publish_hub
    from publish_contract import completion_failures
    from publish_hub_layout import iter_manifests, validate_package

    if publish_hub.ROOT.resolve() != workspace.resolve():
        raise RuntimeError("workspace migrator and publishing hub resolved different project roots")
    manifests = list(iter_manifests())
    failures: list[dict[str, Any]] = []
    for manifest in manifests:
        failures.extend(validate_package(manifest))
    failures.extend(completion_failures(
        root=workspace, shorts_root=publish_hub.SHORTS_ROOT, manifests=manifests
    ))
    if not publish_hub.START_HERE.is_file():
        failures.append({"error": "missing publishing START_HERE"})
    if not publish_hub.ROOT_ENTRY.is_file():
        failures.append({"error": "missing project-root publishing shortcut"})
    return failures


def migrate(root: Path | None = None, *, apply: bool = False) -> dict[str, Any]:
    workspace = _workspace_root(root)
    migration_plan = plan(workspace)
    if not apply:
        return {"status": "PREVIEW", **migration_plan}

    state_path = workspace / STATE_RELATIVE
    prior = {}
    if state_path.is_file():
        try:
            prior = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            prior = {}
    failures = _pure_failures(workspace)
    if int(prior.get("schema_version") or 0) >= SCHEMA_VERSION and not failures:
        return {
            "status": "CURRENT", "schema_version": SCHEMA_VERSION,
            "workspace": str(workspace), "changed": False,
            "legacy_roots_for_explicit_review": migration_plan["legacy_roots_for_explicit_review"],
        }

    for raw in migration_plan["missing_directories"]:
        Path(raw).mkdir(parents=True, exist_ok=True)

    import publish_hub
    promoted = publish_hub.migrate_ready_shorts()
    registry = publish_hub.rebuild_index()
    remaining = _pure_failures(workspace)
    payload = {
        "status": "MIGRATED" if not remaining else "ATTENTION",
        "schema_version": SCHEMA_VERSION,
        "workspace": str(workspace),
        "changed": True,
        "completed_shorts_registered": len(promoted),
        "hub": registry.get("hub"),
        "start_here": registry.get("start_here"),
        "remaining_failures": remaining,
        "legacy_roots_for_explicit_review": migration_plan["legacy_roots_for_explicit_review"],
        "migrated_at": _now(),
    }
    _atomic_json(state_path, payload)
    return payload


def selftest() -> None:
    # The task-shaped orphan/stale fixtures live in publish_contract.  This
    # self-test protects the migration planner from ever treating user media as
    # a managed target.
    with tempfile.TemporaryDirectory(prefix="workspace-migrator-") as temporary:
        root = Path(temporary)
        (root / "AUTOPILOT_MANIFEST.json").write_text(
            '{"schema_version": 2, "project_id": "fixture"}', encoding="utf-8"
        )
        source = root / "videos" / "raw" / "user.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"protected")
        preview = plan(root)
        assert preview["missing_directories"]
        assert source.read_bytes() == b"protected"
        assert all("user.mp4" not in path for path in preview["missing_directories"])
    print("workspace_migrator self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Video Autopilot workspace schema migrator")
    parser.add_argument("command", choices=("plan", "apply", "selftest"))
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
        return 0
    payload = migrate(Path(args.root) if args.root else None, apply=args.command == "apply")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("status") == "ATTENTION" else 0


if __name__ == "__main__":
    raise SystemExit(main())
