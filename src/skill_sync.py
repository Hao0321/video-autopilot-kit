# -*- coding: utf-8 -*-
"""Keep a destination aligned with the live canonical Codex Skill.

This is an additive sync: it updates declared source/docs but never deletes
installed files, runtime state, media, demos or user outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Mapping


SKILL_PATH_ENV = "EDITKIN_VIDEO_AUTOPILOT_SKILL"
SYNC_MARKER_NAME = ".video-autopilot-skill.json"
DEFAULT_DEST = Path.home() / ".codex" / "skills" / "video-autopilot"


def canonical_source(
    *, env: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    environment = os.environ if env is None else env
    explicit = str(environment.get(SKILL_PATH_ENV, "")).strip()
    if explicit:
        skill_path = Path(explicit).expanduser()
        if not skill_path.is_absolute():
            raise ValueError(f"{SKILL_PATH_ENV} must be an absolute SKILL.md path")
    else:
        home_path = Path.home() if home is None else Path(home).expanduser()
        skill_path = home_path / ".codex" / "skills" / "video-autopilot" / "SKILL.md"
    skill_path = skill_path.resolve()
    if not skill_path.is_file():
        raise FileNotFoundError(f"Canonical video-autopilot SKILL.md is missing: {skill_path}")
    if not re.search(r"^name:\s*video-autopilot\s*$", skill_path.read_text(encoding="utf-8-sig"), re.MULTILINE):
        raise ValueError(f"Canonical Skill is not video-autopilot: {skill_path}")
    contract = skill_path.with_name("workflow_contract.json")
    if not contract.is_file():
        raise FileNotFoundError(f"Canonical workflow contract is missing beside SKILL.md: {contract}")
    return skill_path.parent


def sync_files(source: Path | None = None) -> list[Path]:
    source = canonical_source() if source is None else Path(source).expanduser().resolve()
    for parent in source.parents:
        manifest_path = parent / "AUTOPILOT_MANIFEST.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for skill in manifest.get("skills", []):
            declared_source = (parent / skill.get("source", "")).resolve()
            if skill.get("id") != "video-autopilot" or declared_source != source.resolve():
                continue
            found: dict[str, Path] = {}
            for pattern in skill.get("include", []):
                for path in source.glob(pattern):
                    if path.is_file():
                        found[path.relative_to(source).as_posix()] = path
            return [found[key] for key in sorted(found)]
    files = [source / "SKILL.md"]
    files += [source / "audit.config.json"]
    files += [source / "workflow_contract.json"]
    files += sorted(source.glob("*.py"))
    files += sorted((source / "references").glob("*.md"))
    files += sorted((source / "knowledge").glob("*.json"))
    files += sorted((source / "agents").glob("*.yaml"))
    files += sorted((source / "silent_vlog_maker").glob("*.py"))
    files += sorted((source / "longform_maker").glob("*.py"))
    files += sorted((source / "drama_pipeline").glob("*.py"))
    files += sorted((source / "projects").glob("*.py"))
    return [path for path in files if path.is_file()]


def _hash(path: Path) -> str:
    payload = path.read_bytes()
    if b"\x00" not in payload:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _metadata_status(source: Path, destination: Path, files: list[Path]) -> dict:
    if source.resolve() != destination.resolve():
        return {"status": "N/A", "drift": []}
    marker = destination / SYNC_MARKER_NAME
    if not marker.is_file():
        return {"status": "MISSING", "drift": [SYNC_MARKER_NAME]}
    try:
        state = json.loads(marker.read_text(encoding="utf-8-sig"))
        managed = state["managed_files"]
        hashes = state["managed_hashes"]
        if not isinstance(managed, list) or not isinstance(hashes, dict):
            raise ValueError("invalid managed metadata")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return {"status": "INVALID", "drift": [SYNC_MARKER_NAME], "error": str(error)}
    declared = [path.relative_to(source).as_posix() for path in files]
    drift = sorted(set(declared) ^ set(managed))
    drift.extend(
        relative for relative in declared
        if hashes.get(relative) != _hash(destination / relative)
    )
    drift = sorted(set(drift))
    return {"status": "GREEN" if not drift else "DRIFT", "drift": drift}


def status(destination: str | Path = DEFAULT_DEST, source: Path | None = None) -> dict:
    source = canonical_source() if source is None else Path(source).expanduser().resolve()
    dest = Path(destination).expanduser().resolve()
    missing, different, matched = [], [], 0
    files = sync_files(source)
    for src in files:
        rel = src.relative_to(source)
        target = dest / rel
        if not target.is_file():
            missing.append(rel.as_posix())
        elif _hash(src) != _hash(target):
            different.append(rel.as_posix())
        else:
            matched += 1
    metadata = _metadata_status(source, dest, files)
    return {
        "status": "GREEN" if not missing and not different and metadata["status"] in {"GREEN", "N/A"} else "RED",
        "source": str(source), "destination": str(dest), "declared_files": len(files),
        "matched": matched, "missing": missing, "different": different,
        "metadata": metadata,
        "policy": "additive; no destination files are deleted",
    }


def sync(destination: str | Path = DEFAULT_DEST, source: Path | None = None) -> dict:
    source = canonical_source() if source is None else Path(source).expanduser().resolve()
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
    source = canonical_source()
    with tempfile.TemporaryDirectory(prefix="skill-sync-") as temp_dir:
        result = sync(temp_dir, source)
        assert result["status"] == "GREEN" and result["copied"] == result["declared_files"]
        assert result["declared_files"] >= 180, "compat sync must use the v7 manifest include set"
        again = sync(temp_dir, source)
        assert again["status"] == "GREEN" and again["copied"] == 0
        fake_home = Path(temp_dir) / "home"
        fake_root = fake_home / ".codex" / "skills" / "video-autopilot"
        fake_root.mkdir(parents=True)
        shutil.copy2(source / "SKILL.md", fake_root / "SKILL.md")
        shutil.copy2(source / "workflow_contract.json", fake_root / "workflow_contract.json")
        assert canonical_source(env={}, home=fake_home) == fake_root.resolve()
        assert canonical_source(env={SKILL_PATH_ENV: str(source / "SKILL.md")}) == source.resolve()
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
