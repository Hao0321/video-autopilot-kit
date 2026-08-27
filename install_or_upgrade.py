# -*- coding: utf-8 -*-
"""Standalone bootstrap for both fresh installs and pre-updater legacy copies."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


DEFAULT_CHANNEL = (
    "https://github.com/Hao0321/video-autopilot-kit/releases/latest/"
    "download/release-channel.json"
)
BOOTSTRAP_RUNTIME_MEMBERS = (
    "src/release_integrity.py",
    "src/release_manager.py",
)


def _read(value: str, base: Optional[str] = None) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in {"http", "https"}:
        with urllib.request.urlopen(value, timeout=30) as response:  # nosec B310
            return response.read(), value
    path = Path(value)
    if not path.is_absolute() and base and urllib.parse.urlparse(base).scheme not in {"http", "https"}:
        path = Path(base).parent / path
    resolved = path.resolve()
    return resolved.read_bytes(), str(resolved)


def _asset_url(value: str, source: str) -> str:
    if urllib.parse.urlparse(value).scheme in {"http", "https"}:
        return value
    if urllib.parse.urlparse(source).scheme in {"http", "https"}:
        return urllib.parse.urljoin(source, value)
    return str((Path(source).parent / value).resolve())


def _load_manager(path: Path):
    spec = importlib.util.spec_from_file_location("video_autopilot_release_manager", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load release manager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_bootstrap_runtime(package: zipfile.ZipFile, root: Path) -> Path:
    """Materialize the complete verified updater runtime without archive extraction."""
    runtime = root / "src"
    runtime.mkdir(parents=True, exist_ok=True)
    try:
        for member in BOOTSTRAP_RUNTIME_MEMBERS:
            (runtime / Path(member).name).write_bytes(package.read(member))
    except KeyError:
        raise RuntimeError("release bootstrap runtime is incomplete") from None
    return runtime / "release_manager.py"


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _safe_local_runtime_member(install_root: Path, member: str) -> bool:
    cursor = install_root
    if _is_link_or_reparse(cursor):
        return False
    for part in Path(member).parts:
        cursor = cursor / part
        try:
            cursor.lstat()
        except OSError:
            return False
        if _is_link_or_reparse(cursor):
            return False
    return cursor.is_file()


def _local_runtime_complete(install_root: Path) -> bool:
    return all(
        _safe_local_runtime_member(install_root, member)
        for member in BOOTSTRAP_RUNTIME_MEMBERS
    )


def _migrate_workspace(install_root: Path) -> dict:
    path = install_root / "src" / "workspace_migrator.py"
    if not path.is_file():
        return {"status": "NOT_AVAILABLE"}
    resolved_root = install_root.resolve()
    environment = os.environ.copy()
    environment["VIDEO_AUTOPILOT_ROOT"] = str(resolved_root)
    completed = subprocess.run(
        [sys.executable, str(path), "apply", "--root", str(resolved_root)],
        cwd=resolved_root, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        if completed.returncode != 0:
            raise RuntimeError("workspace migration failed") from None
        raise RuntimeError("workspace migration returned invalid output") from exc
    if not isinstance(result, dict):
        if completed.returncode != 0:
            raise RuntimeError("workspace migration failed")
        raise RuntimeError("workspace migration returned invalid output")
    if completed.returncode == 0:
        return result
    if completed.returncode == 1 and result.get("status") == "ATTENTION":
        return result
    raise RuntimeError("workspace migration failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or safely upgrade video-autopilot-kit")
    parser.add_argument("--channel", default=DEFAULT_CHANNEL)
    parser.add_argument("--install-root", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--install-skill", action="store_true")
    parser.add_argument("--adopt-skill", action="store_true")
    args = parser.parse_args()
    install_root = Path(os.path.abspath(args.install_root))
    local_manager = install_root / "src" / "release_manager.py"
    manager = None
    if _local_runtime_complete(install_root):
        try:
            manager = _load_manager(local_manager)
        except Exception:
            # A partial/corrupt updater must take the verified bootstrap repair
            # path without exposing a machine-local absolute path.
            manager = None
    if manager is not None:
        if args.check:
            result = manager.check_update(args.channel, install_root)
        else:
            result = manager.update_from_channel(
                args.channel, install_root, apply=args.apply or args.auto, auto=args.auto
            )
        if args.install_skill and result.get("status") in {"UPDATED", "CURRENT"}:
            result["codex_skill"] = manager.sync_codex_skill(
                install_root,
                Path.home() / ".codex" / "skills" / "video-autopilot",
                adopt=args.adopt_skill,
            )
        if result.get("status") in {"UPDATED", "CURRENT"}:
            result["workspace_schema"] = _migrate_workspace(install_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    channel_bytes, channel_source = _read(args.channel)
    channel = json.loads(channel_bytes.decode("utf-8"))
    latest = channel["latest"]
    asset = _asset_url(latest["url"], channel_source)
    if args.check or not (args.apply or args.auto):
        print(json.dumps({
            "status": "BOOTSTRAP_AVAILABLE", "latest": latest["version"],
            "asset": asset,
            "repair": any(
                _safe_local_runtime_member(install_root, member)
                for member in BOOTSTRAP_RUNTIME_MEMBERS
            ),
        }, indent=2))
        return 0
    with tempfile.TemporaryDirectory(prefix="video-autopilot-bootstrap-") as temporary:
        archive = Path(temporary) / "release.zip"
        payload, _ = _read(asset, channel_source)
        archive.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        if digest.lower() != latest["sha256"].lower():
            raise RuntimeError("release archive SHA-256 mismatch")
        with zipfile.ZipFile(archive) as package:
            manager_path = _extract_bootstrap_runtime(package, Path(temporary))
        manager = _load_manager(manager_path)
        result = manager.apply_release_archive(archive, install_root, latest["sha256"], auto=args.auto)
        if args.install_skill and result.get("status") in {"UPDATED", "CURRENT"}:
            result["codex_skill"] = manager.sync_codex_skill(
                install_root,
                Path.home() / ".codex" / "skills" / "video-autopilot",
                adopt=args.adopt_skill,
            )
        if result.get("status") in {"UPDATED", "CURRENT"}:
            result["workspace_schema"] = _migrate_workspace(install_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "status": "FAILED",
            "error": "bootstrap failed: " + type(exc).__name__,
        }))
        raise SystemExit(1) from None
