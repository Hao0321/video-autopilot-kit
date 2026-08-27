# -*- coding: utf-8 -*-
"""Standalone bootstrap for both fresh installs and pre-updater legacy copies."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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


def _migrate_workspace(install_root: Path) -> dict:
    path = install_root / "src" / "workspace_migrator.py"
    if not path.is_file():
        return {"status": "NOT_AVAILABLE"}
    source_root = str(path.parent)
    inserted = source_root not in sys.path
    if inserted:
        sys.path.insert(0, source_root)
    try:
        module = _load_manager(path)
        return module.migrate(install_root, apply=True)
    finally:
        if inserted and source_root in sys.path:
            sys.path.remove(source_root)


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
    install_root = Path(args.install_root).resolve()
    local_manager = install_root / "src" / "release_manager.py"
    if local_manager.is_file():
        manager = _load_manager(local_manager)
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
        print(json.dumps({"status": "BOOTSTRAP_AVAILABLE", "latest": latest["version"], "asset": asset}, indent=2))
        return 0
    with tempfile.TemporaryDirectory(prefix="video-autopilot-bootstrap-") as temporary:
        archive = Path(temporary) / "release.zip"
        payload, _ = _read(asset, channel_source)
        archive.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        if digest.lower() != latest["sha256"].lower():
            raise RuntimeError("release archive SHA-256 mismatch")
        with zipfile.ZipFile(archive) as package:
            manager_path = Path(temporary) / "release_manager.py"
            manager_path.write_bytes(package.read("src/release_manager.py"))
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
    raise SystemExit(main())
