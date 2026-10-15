#!/usr/bin/env python3
"""Explicit maintainer sync: validate the complete delta before writing."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from sync_safety import MANIFEST, SyncError, checked_root, plan_sync, safe_path, verify_plan

ROOT = Path(__file__).resolve().parents[1]


def equivalent_files(source: Path, destination: Path, normalize_text: bool) -> bool:
    if not destination.is_file():
        return False
    if normalize_text:
        try:
            return source.read_text(encoding="utf-8-sig").splitlines() == destination.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeError:
            pass
    return source.read_bytes() == destination.read_bytes()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=".sync-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(raw, path)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def apply_plan(plan: dict) -> None:
    destination = plan["destination"]
    checked_root(destination, allow_missing=True)
    destination.mkdir(parents=True, exist_ok=True)
    lock = safe_path(destination, ".public-sync.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        verify_plan(plan)
        for row in plan["rows"]:
            if row["changed"]:
                atomic_write(safe_path(destination, row["path"]), row["data"])
        for row in plan["stale"]:
            safe_path(destination, row["path"]).unlink()
        value = {"schema_version": 2, "managed_paths": [r["path"] for r in plan["rows"]],
                 "managed_sha256": {r["path"]: r["sha256"] for r in plan["rows"]}}
        atomic_write(safe_path(destination, MANIFEST), (json.dumps(value, indent=2) + "\n").encode("utf-8"))
    finally:
        os.close(descriptor)
        lock.unlink()


def main(source_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--public-root", type=Path)
    parser.add_argument("--allow-empty", action="store_true", help="Explicitly retire all managed files when selection is empty.")
    parser.add_argument("--adopt-existing", action="store_true", help="Adopt reviewed existing/legacy files; modified hash-owned files still block.")
    args = parser.parse_args()
    source = source_root or ROOT
    try:
        source = checked_root(source)
        config = json.loads((source / "audit.config.json").read_text(encoding="utf-8-sig"))
        raw = args.public_root or config.get("sync", {}).get("public_root")
        if not raw:
            raise SyncError("sync.public_root is not configured")
        destination = Path(raw).expanduser()
        if not destination.is_absolute():
            destination = source / destination
        plan = plan_sync(source, destination, config, adopt_existing=args.adopt_existing,
                         allow_empty=args.allow_empty)
        if args.write:
            apply_plan(plan)
    except (OSError, ValueError) as exc:
        print(f"BLOCK: {exc}")
        return 2
    changed = [r["path"] for r in plan["rows"] if r["changed"]]
    print(f"{'WRITE' if args.write else 'DRY_RUN'} public_root={destination.resolve()} changed={len(changed)} stale={len(plan['stale'])}")
    for name in changed:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
