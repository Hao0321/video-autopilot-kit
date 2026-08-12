# -*- coding: utf-8 -*-
"""Keep the installed Codex skill aligned with the project canonical source.

This is an additive sync: it updates declared source/docs but never deletes
installed files, runtime state, media, demos or user outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path


SOURCE = Path(__file__).resolve().parent
DEFAULT_DEST = Path.home() / ".codex" / "skills" / "video-autopilot"


def sync_files(source: Path = SOURCE) -> list[Path]:
    files = [source / "SKILL.md"]
    files += sorted(source.glob("*.py"))
    files += sorted((source / "references").glob("*.md"))
    files += sorted((source / "knowledge").glob("*.json"))
    files += sorted((source / "agents").glob("*.yaml"))
    files += sorted((source / "silent_vlog_maker").glob("*.py"))
    files += sorted((source / "longform_maker").glob("*.py"))
    files += sorted((source / "projects").glob("*.py"))
    return [path for path in files if path.is_file()]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(destination: str | Path = DEFAULT_DEST, source: Path = SOURCE) -> dict:
    dest = Path(destination).expanduser().resolve()
    missing, different, matched = [], [], 0
    for src in sync_files(source):
        rel = src.relative_to(source)
        target = dest / rel
        if not target.is_file():
            missing.append(rel.as_posix())
        elif _hash(src) != _hash(target):
            different.append(rel.as_posix())
        else:
            matched += 1
    return {
        "status": "GREEN" if not missing and not different else "RED",
        "source": str(source), "destination": str(dest), "declared_files": len(sync_files(source)),
        "matched": matched, "missing": missing, "different": different,
        "policy": "additive; no destination files are deleted",
    }


def sync(destination: str | Path = DEFAULT_DEST, source: Path = SOURCE) -> dict:
    dest = Path(destination).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in sync_files(source):
        rel = src.relative_to(source)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or _hash(src) != _hash(target):
            shutil.copy2(src, target)
            copied += 1
    result = status(dest, source)
    result["copied"] = copied
    return result


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="skill-sync-") as temp_dir:
        result = sync(temp_dir)
        assert result["status"] == "GREEN" and result["copied"] == result["declared_files"]
        again = sync(temp_dir)
        assert again["status"] == "GREEN" and again["copied"] == 0
    print("skill_sync self-test GREEN")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "sync", "selftest"), nargs="?", default="status")
    parser.add_argument("--destination", default=str(DEFAULT_DEST))
    args = parser.parse_args()
    if args.command == "selftest":
        self_test()
        return 0
    result = sync(args.destination) if args.command == "sync" else status(args.destination)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("SKILL SYNC " + result["status"])
    return 0 if result["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
