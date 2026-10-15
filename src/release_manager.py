# -*- coding: utf-8 -*-
"""Integrity-checked release builder, updater, migration ledger and rollback.

The updater owns only files declared by release-index.json. Unknown files and
all release-manifest protected paths are never deleted or overwritten.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

if __package__:
    from .release_integrity import (
        collect_skill_sources as _collect_skill_sources,
        assert_contained_release_path as _assert_contained_release_path,
        assert_transaction_id as _assert_transaction_id,
        assert_safe_mutation_path as _assert_safe_mutation_path,
        canonical_portable_relative as _canonical_portable_relative,
        canonical_persisted_hashes as _canonical_persisted_hashes,
        load_sync_inventory_contract as _load_sync_inventory_contract,
        preflight_apply_paths as _preflight_apply_paths,
        preflight_rollback_paths as _preflight_rollback_paths,
        resolve_mutation_root as _resolve_mutation_root,
        staged_sync_receipt_errors as _staged_sync_receipt_errors,
        validated_install_state as _validated_install_state,
        validated_transaction_record as _validated_transaction_record,
    )
else:
    _integrity_path = Path(__file__).resolve().with_name("release_integrity.py")
    _integrity_spec = importlib.util.spec_from_file_location(
        "_video_autopilot_release_integrity", _integrity_path
    )
    if _integrity_spec is None or _integrity_spec.loader is None:
        raise RuntimeError("release integrity module loader unavailable")
    _integrity_module = importlib.util.module_from_spec(_integrity_spec)
    _integrity_spec.loader.exec_module(_integrity_module)
    _collect_skill_sources = _integrity_module.collect_skill_sources
    _assert_contained_release_path = _integrity_module.assert_contained_release_path
    _assert_transaction_id = _integrity_module.assert_transaction_id
    _assert_safe_mutation_path = _integrity_module.assert_safe_mutation_path
    _canonical_portable_relative = _integrity_module.canonical_portable_relative
    _canonical_persisted_hashes = _integrity_module.canonical_persisted_hashes
    _load_sync_inventory_contract = _integrity_module.load_sync_inventory_contract
    _preflight_apply_paths = _integrity_module.preflight_apply_paths
    _preflight_rollback_paths = _integrity_module.preflight_rollback_paths
    _resolve_mutation_root = _integrity_module.resolve_mutation_root
    _staged_sync_receipt_errors = _integrity_module.staged_sync_receipt_errors
    _validated_install_state = _integrity_module.validated_install_state
    _validated_transaction_record = _integrity_module.validated_transaction_record


if __package__:
    from .release_archive import verify_archive, sha256_path, load_bootstrap_install_component, stage_verified_archive
else:
    _archive_path = Path(__file__).with_name("release_archive.py").resolve()
    _archive_spec = importlib.util.spec_from_file_location("_video_autopilot_release_archive", _archive_path)
    if _archive_spec is None or _archive_spec.loader is None:
        raise RuntimeError("release archive module loader unavailable")
    _archive_module = importlib.util.module_from_spec(_archive_spec)
    _archive_spec.loader.exec_module(_archive_module)
    verify_archive = _archive_module.verify_archive
    sha256_path = _archive_module.sha256_path
    load_bootstrap_install_component = _archive_module.load_bootstrap_install_component
    stage_verified_archive = _archive_module.stage_verified_archive


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANNEL = "https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/release-channel.json"
STATE_DIR = ".video-autopilot"
TEXT_EXTENSIONS = {".css", ".csv", ".html", ".ini", ".js", ".json", ".jsonl", ".log", ".md", ".mjs", ".ndjson", ".py", ".svg", ".toml", ".ts", ".txt", ".yaml", ".yml"}

_RELEASE_COMPONENTS = {}


def _load_release_component(name: str, archive=None, expected_hash=None):
    """Load only a declared sibling; ambient PYTHONPATH cannot select runtime code."""
    if name not in {"release_build", "release_install"}:
        raise ValueError("unknown release component")
    if name not in _RELEASE_COMPONENTS:
        component = Path(__file__).with_name(name + ".py")
        if name == "release_install" and not component.is_file() and archive is not None:
            module = load_bootstrap_install_component(archive, expected_hash)
            _RELEASE_COMPONENTS[name] = module
            return module
        spec = importlib.util.spec_from_file_location("_video_autopilot_" + name, component)
        if spec is None or spec.loader is None:
            raise RuntimeError("release component loader unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RELEASE_COMPONENTS[name] = module
    return _RELEASE_COMPONENTS[name]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_transaction_id() -> str:
    """Return a sortable, collision-resistant backup transaction identifier."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:12]}"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def version_tuple(value: Optional[str]) -> Optional[tuple[int, int, int]]:
    if not value:
        return None
    match = re.search(r"(?:^|v)(\d+)\.(\d+)\.(\d+)", str(value))
    return tuple(map(int, match.groups())) if match else None


def declared_migration(current: Optional[str], target: str, manifest: dict) -> Optional[dict]:
    """Return the explicit idempotent migration covering this version pair."""
    current_value = version_tuple(current)
    target_value = version_tuple(target)
    if target_value is None:
        return None
    for row in manifest.get("migrations", []):
        if not row.get("idempotent"):
            continue
        target_minimum = version_tuple(row.get("target_minimum"))
        target_maximum = version_tuple(row.get("target_maximum_exclusive"))
        if not target_minimum or not target_maximum:
            continue
        if not (target_minimum <= target_value < target_maximum):
            continue
        if current_value is None:
            if row.get("from") == "unversioned":
                return row
            continue
        from_minimum = version_tuple(row.get("from_minimum"))
        from_maximum = version_tuple(row.get("from_maximum_exclusive"))
        if from_minimum and from_maximum and from_minimum <= current_value < from_maximum:
            return row
    return None


def _matches(relative: str, patterns: Iterable[str]) -> bool:
    value = relative.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        while pattern.startswith("./"):
            pattern = pattern[2:]
        if pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if value == prefix or value.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def _private_release_path_patterns(manifest: dict) -> tuple[str, ...]:
    return _load_release_component("release_build")._private_release_path_patterns(globals(), manifest)


def _is_private_release_path(relative: str, patterns: Iterable[str]) -> bool:
    return _load_release_component("release_build")._is_private_release_path(globals(), relative, patterns)


def _git_tracked_release_paths(root: Path) -> Optional[set[str]]:
    return _load_release_component("release_build")._git_tracked_release_paths(globals(), root)


def collect_release_files(root: Path, manifest: dict) -> list[Path]:
    return _load_release_component("release_build").collect_release_files(globals(), root, manifest)


def validate_release_tree(root: Path, manifest: dict, files: list[Path]) -> list[str]:
    return _load_release_component("release_build").validate_release_tree(globals(), root, manifest, files)


def _release_payload(path: Path) -> bytes:
    return _load_release_component("release_build")._release_payload(globals(), path)


def _deterministic_zip(source: Path, archive: Path) -> None:
    return _load_release_component("release_build")._deterministic_zip(globals(), source, archive)


def build_release(
    root: Path = ROOT,
    dist: Optional[Path] = None,
    base_url: Optional[str] = None,
) -> dict:
    return _load_release_component("release_build").build_release(globals(), root, dist, base_url)


def _read_url_or_path(value: str, base: Optional[str] = None) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(value, timeout=30) as response:  # nosec B310
            return response.read(), value
    path = Path(value)
    if not path.is_absolute() and base and urllib.parse.urlparse(base).scheme not in {"http", "https"}:
        path = Path(base).parent / path
    return path.resolve().read_bytes(), str(path.resolve())


def load_channel(value: str) -> tuple[dict, str]:
    payload, resolved = _read_url_or_path(value)
    channel = json.loads(payload.decode("utf-8"))
    if channel.get("project_id") != "video-autopilot-kit":
        raise ValueError("update channel belongs to another project")
    return channel, resolved


def resolve_channel_asset(url: str, channel_source: str) -> str:
    if urllib.parse.urlparse(url).scheme in {"http", "https"}:
        return url
    if urllib.parse.urlparse(channel_source).scheme in {"http", "https"}:
        return urllib.parse.urljoin(channel_source, url)
    return str((Path(channel_source).parent / url).resolve())


def detect_current_version(install_root: Path) -> Optional[str]:
    install_root = _resolve_mutation_root(install_root)
    state = install_root / STATE_DIR / "install-state.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, state, require_file=True)
    if state.is_file():
        payload = read_json(state)
        if not isinstance(payload, dict):
            raise RuntimeError("install state is invalid")
        _validated_install_state(payload)
        return payload.get("version")
    manifest = install_root / "release-manifest.json"
    _assert_safe_mutation_path(install_root, manifest, require_file=True)
    if manifest.is_file():
        payload = read_json(manifest)
        if not isinstance(payload, dict):
            raise RuntimeError("installed release manifest is invalid")
        return payload.get("version")
    try:
        result = subprocess.run(
            ["git", "-C", str(install_root), "describe", "--tags", "--abbrev=0"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=5
        )
        if result.returncode == 0 and version_tuple(result.stdout.strip()):
            return result.stdout.strip().lstrip("v")
    except (OSError, subprocess.SubprocessError):
        pass
    for name in ("README.md", "CHANGELOG.md"):
        path = install_root / name
        if path.is_file():
            match = re.search(r"v(\d+\.\d+\.\d+)", path.read_text(encoding="utf-8", errors="replace"))
            if match:
                return match.group(1)
    return None


def compatible_upgrade(current: Optional[str], target_manifest: dict) -> bool:
    policy = target_manifest["compatibility"]
    current_tuple = version_tuple(current)
    migration = declared_migration(current, target_manifest.get("version", ""), target_manifest)
    if current_tuple is None:
        return bool(policy.get("allow_unversioned_legacy") and migration)
    minimum = version_tuple(policy["minimum"])
    maximum = version_tuple(policy["maximum_exclusive"])
    return bool(minimum and maximum and minimum <= current_tuple < maximum and migration)


def _backup_file(
    install_root: Path, source: Path, backup_root: Path, relative: str
) -> None:
    relative = _canonical_portable_relative(relative)
    target = backup_root / "files" / relative
    _assert_safe_mutation_path(install_root, source, require_file=True, allow_missing=False)
    _assert_safe_mutation_path(install_root, target, require_file=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _rollback_record(install_root: Path, record: dict, backup_root: Path) -> None:
    transaction = _assert_transaction_id(backup_root.name)
    record = _validated_transaction_record(record, transaction)
    _preflight_rollback_paths(install_root, record, backup_root)
    for relative in reversed(record["created"]):
        target = install_root / relative
        if target.is_file() or target.is_symlink():
            target.unlink()
    for relative in record["replaced"] + record["removed"]:
        source = backup_root / "files" / relative
        target = install_root / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".rollback-tmp")
            shutil.copy2(source, temporary)
            os.replace(temporary, target)


def _restore_previous_state(install_root: Path, backup_root: Path) -> None:
    state_path = install_root / STATE_DIR / "install-state.json"
    previous = backup_root / "previous-install-state.json"
    _assert_safe_mutation_path(install_root, state_path, require_file=True)
    _assert_safe_mutation_path(install_root, state_path.with_name(state_path.name + ".tmp"), require_file=True)
    _assert_safe_mutation_path(install_root, previous, require_file=True)
    if previous.is_file():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_name(state_path.name + ".tmp")
        shutil.copy2(previous, temporary)
        os.replace(temporary, state_path)
    elif state_path.is_file():
        state_path.unlink()


def locally_modified_managed_files(install_root: Path, state: dict) -> list[str]:
    install_root = _resolve_mutation_root(install_root)
    if not isinstance(state, dict):
        raise RuntimeError("install state is invalid")
    expected = _canonical_persisted_hashes(state.get("managed_hashes", {}))
    changed = []
    for relative, digest in expected.items():
        target = install_root / relative
        _assert_safe_mutation_path(install_root, target)
        if not target.is_file() or sha256_path(target).lower() != str(digest).lower():
            changed.append(relative)
    return sorted(changed)


def apply_release_archive(archive: Path, install_root: Path, expected_hash: Optional[str] = None, auto: bool = False) -> dict:
    return _load_release_component("release_install", archive, expected_hash).apply_release_archive(globals(), archive, install_root, expected_hash, auto)


def rollback(install_root: Path, transaction: Optional[str] = None) -> dict:
    return _load_release_component("release_install").rollback(globals(), install_root, transaction)


def check_update(channel_value: str, install_root: Path) -> dict:
    install_root = _resolve_mutation_root(install_root)
    channel, source = load_channel(channel_value)
    latest = channel["latest"]
    current = detect_current_version(install_root)
    current_tuple, latest_tuple = version_tuple(current), version_tuple(latest["version"])
    available = current_tuple is None or (latest_tuple is not None and latest_tuple > current_tuple)
    state_path = install_root / STATE_DIR / "install-state.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, state_path, require_file=True)
    state = read_json(state_path) if state_path.is_file() else {}
    modified = locally_modified_managed_files(install_root, state) if state else []
    status = "UPDATE_AVAILABLE" if available else (
        "REPAIR_AVAILABLE" if modified else "CURRENT"
    )
    return {
        "status": status,
        "current": current or "unversioned",
        "latest": latest["version"],
        "channel": source,
        "asset": resolve_channel_asset(latest["url"], source),
        "sha256": latest["sha256"],
        "modified": modified,
    }


def update_from_channel(channel_value: str, install_root: Path, apply: bool, auto: bool) -> dict:
    plan = check_update(channel_value, install_root)
    if not apply:
        return plan
    with tempfile.TemporaryDirectory(prefix="video-autopilot-download-") as temporary:
        archive = Path(temporary) / "release.zip"
        payload, _resolved = _read_url_or_path(plan["asset"], plan["channel"])
        archive.write_bytes(payload)
        return apply_release_archive(archive, install_root, plan["sha256"], auto=auto)


def sync_codex_skill(repo_root: Path, destination: Path, adopt: bool = False) -> dict:
    return _load_release_component("release_install").sync_codex_skill(globals(), repo_root, destination, adopt)


def auto_update(channel: str, install_root: Path, max_age_hours: float) -> dict:
    install_root = _resolve_mutation_root(install_root)
    cache = install_root / STATE_DIR / "update-cache.json"
    _assert_safe_mutation_path(install_root, install_root / STATE_DIR)
    _assert_safe_mutation_path(install_root, cache, require_file=True)
    _assert_safe_mutation_path(install_root, cache.with_name(cache.name + ".tmp"), require_file=True)
    if cache.is_file():
        age = time.time() - cache.stat().st_mtime
        if age < max_age_hours * 3600:
            return {"status": "CACHED", "next_check_seconds": round(max_age_hours * 3600 - age)}
    try:
        result = update_from_channel(channel, install_root, apply=True, auto=True)
        atomic_json(cache, {"checked_at": utc_now(), "result": result})
        return result
    except Exception as exc:  # network/update failure must not block editing work
        atomic_json(cache, {"checked_at": utc_now(), "status": "CHECK_FAILED", "error": "update failed: " + type(exc).__name__})
        return {"status": "CHECK_FAILED", "error": "update failed: " + type(exc).__name__, "non_blocking": True}


def self_test() -> None:
    """Lazy-load release fixtures without a circular or duplicate module import."""
    if __package__:
        from .release_manager_selftest import run_self_test
    else:
        from release_manager_selftest import run_self_test

    run_self_test(sys.modules[__name__])


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Safe release and upgrade manager")
    subs = parser.add_subparsers(dest="command", required=True)
    build = subs.add_parser("build")
    build.add_argument("--root", default=str(ROOT))
    build.add_argument("--dist")
    build.add_argument("--base-url")
    check = subs.add_parser("check")
    check.add_argument("--channel", default=DEFAULT_CHANNEL)
    check.add_argument("--install-root", default=str(ROOT))
    update = subs.add_parser("update")
    update.add_argument("--channel", default=DEFAULT_CHANNEL)
    update.add_argument("--install-root", default=str(ROOT))
    update.add_argument("--apply", action="store_true")
    update.add_argument("--auto", action="store_true")
    automatic = subs.add_parser("auto")
    automatic.add_argument("--channel", default=DEFAULT_CHANNEL)
    automatic.add_argument("--install-root", default=str(ROOT))
    automatic.add_argument("--max-age-hours", type=float, default=24)
    back = subs.add_parser("rollback")
    back.add_argument("--install-root", default=str(ROOT))
    back.add_argument("--transaction")
    skill = subs.add_parser("install-skill")
    skill.add_argument("--repo-root", default=str(ROOT))
    skill.add_argument("--destination", default=str(Path.home() / ".codex" / "skills" / "video-autopilot"))
    skill.add_argument("--adopt", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_release(Path(args.root), Path(args.dist) if args.dist else None, args.base_url)
    elif args.command == "check":
        result = check_update(args.channel, Path(args.install_root))
    elif args.command == "update":
        result = update_from_channel(args.channel, Path(args.install_root), args.apply, args.auto)
    elif args.command == "auto":
        result = auto_update(args.channel, Path(args.install_root), args.max_age_hours)
    elif args.command == "rollback":
        result = rollback(Path(args.install_root), args.transaction)
    elif args.command == "install-skill":
        result = sync_codex_skill(Path(args.repo_root), Path(args.destination), args.adopt)
    else:
        self_test()
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("status") in {"CHECK_FAILED"} and not result.get("non_blocking") else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": "release command failed: " + type(exc).__name__}))
        raise SystemExit(1) from None
