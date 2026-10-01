#!/usr/bin/env python3
"""Copy configured public files without deleting public-only packaging files."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = ".code-cleanup-managed.json"


def equivalent_files(source: Path, destination: Path, normalize_text: bool) -> bool:
    if not destination.is_file():
        return False
    if not normalize_text:
        return destination.read_bytes() == source.read_bytes()
    try:
        source_text = source.read_text(encoding="utf-8-sig")
        destination_text = destination.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return destination.read_bytes() == source.read_bytes()
    return source_text.splitlines() == destination_text.splitlines()


def ignored(relative: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative.replace("\\", "/"), pattern) for pattern in patterns)


def privacy_violations(rows: list[tuple[Path, str]], config: dict) -> list[str]:
    privacy = config.get("sync", {}).get("privacy", config.get("privacy", {}))
    tokens = [str(value) for value in privacy.get("tokens", []) if str(value)]
    patterns = []
    for value in privacy.get("patterns", []):
        try:
            patterns.append(re.compile(str(value), re.IGNORECASE))
        except re.error as exc:
            return [f"invalid privacy regex {value!r}: {exc}"]
    failures = []
    for source, relative in rows:
        try:
            text = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for token in tokens:
            if token.casefold() in text.casefold():
                failures.append(f"{relative}: privacy token {token!r}")
        for pattern in patterns:
            if pattern.search(text):
                failures.append(f"{relative}: privacy pattern {pattern.pattern!r}")
    return failures


def safe_destination(destination_root: Path, relative: str) -> Path:
    root = destination_root.resolve()
    destination = (root / relative).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"sync path escapes public root: {relative}")
    return destination


def managed_paths(destination_root: Path) -> set[str]:
    manifest = destination_root / MANIFEST_NAME
    if not manifest.exists():
        return set()
    value = json.loads(manifest.read_text(encoding="utf-8-sig"))
    paths = value.get("managed_paths") if isinstance(value, dict) else None
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        raise ValueError(f"invalid sync manifest: {manifest}")
    return set(paths)


def write_manifest(destination_root: Path, paths: list[str]) -> None:
    manifest = destination_root / MANIFEST_NAME
    temporary = manifest.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"schema_version": 1, "managed_paths": paths}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "audit.config.json").read_text(encoding="utf-8-sig"))
    value = config.get("sync", {}).get("public_root")
    if not value:
        raise ValueError("sync.public_root is not configured")
    destination_root = Path(value).expanduser()
    if not destination_root.is_absolute():
        destination_root = (ROOT / destination_root).resolve()
    patterns = config.get("exclude", []) + config.get("sync", {}).get("ignore", [])
    normalize_text = bool(config.get("sync", {}).get("normalize_text", True))
    rows = []
    for source in sorted(path for path in ROOT.rglob("*") if path.is_file()):
        relative = source.relative_to(ROOT).as_posix()
        if not ignored(relative, patterns):
            rows.append((source, relative))
    violations = privacy_violations(rows, config)
    if violations:
        print(f"BLOCK public_root={destination_root} privacy_violations={len(violations)}")
        for violation in violations:
            print(violation)
        return 2
    current = [relative for _source, relative in rows]
    stale = sorted(managed_paths(destination_root) - set(current))
    changed = []
    for source, relative in rows:
        destination = safe_destination(destination_root, relative)
        if equivalent_files(source, destination, normalize_text):
            continue
        changed.append(relative)
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    if args.write:
        for relative in stale:
            safe_destination(destination_root, relative).unlink(missing_ok=True)
        write_manifest(destination_root, current)
    mode = "WRITE" if args.write else "DRY_RUN"
    print(f"{mode} public_root={destination_root} changed={len(changed)} stale={len(stale)}")
    for relative in changed:
        print(relative)
    for relative in stale:
        print(f"STALE {relative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
