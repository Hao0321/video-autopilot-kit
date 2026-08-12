# -*- coding: utf-8 -*-
"""Portable path resolution for the Hao video workspace.

No production module should know a drive letter or Windows user name.  The
project root is resolved from an environment override or a workspace marker.
"""
from __future__ import annotations

import os
import json
import tempfile
from pathlib import Path


MANIFEST_NAMES = ("AUTOPILOT_MANIFEST.json", "release-manifest.json")
ROOT_ENV_VARS = ("VIDEO_AUTOPILOT_ROOT", "VIDEO_KIT_PROJECT_ROOT", "HAO_AUTOPILOT_ROOT")
ROOT_REGISTRY = Path.home() / ".codex" / "hao_autopilot_root.json"


def _looks_like_root(path: Path) -> bool:
    return any((path / name).is_file() for name in MANIFEST_NAMES) or (
        (path / ".claude" / "skills").is_dir() and (path / "assets").is_dir()
    )


def discover_project_root(start: str | os.PathLike | None = None, *, required: bool = True) -> Path | None:
    """Find the workspace without embedding a machine-specific absolute path."""
    for name in ROOT_ENV_VARS:
        raw = os.environ.get(name)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if _looks_like_root(candidate):
                return candidate
            if required:
                raise RuntimeError(f"{name} does not point to a video workspace: {candidate}")

    seeds = []
    if start is not None:
        seeds.append(Path(start))
    seeds.extend((Path.cwd(), Path(__file__)))
    seen: set[Path] = set()
    for seed in seeds:
        seed = seed.expanduser().resolve()
        if seed.is_file():
            seed = seed.parent
        for candidate in (seed, *seed.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if _looks_like_root(candidate):
                return candidate

    # Installed skills usually live outside the video workspace.  Keep the
    # machine-specific root in user config, never in production source.
    if ROOT_REGISTRY.is_file():
        try:
            raw = json.loads(ROOT_REGISTRY.read_text(encoding="utf-8-sig"))
            candidate = Path(raw["root"]).expanduser().resolve()
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if required:
                raise RuntimeError(f"Invalid autopilot root registry: {ROOT_REGISTRY}: {exc}")
        else:
            if _looks_like_root(candidate):
                return candidate
            if required:
                raise RuntimeError(
                    f"Registered autopilot root is not a workspace: {candidate}"
                )
    if required:
        raise RuntimeError(
            f"Cannot find a project manifest; run inside the workspace or set VIDEO_AUTOPILOT_ROOT."
        )
    return None


def project_path(*parts: str, root: str | os.PathLike | None = None) -> Path:
    base = Path(root).expanduser().resolve() if root else discover_project_root()
    return base.joinpath(*parts)


def asset_path(*parts: str, root: str | os.PathLike | None = None) -> Path:
    return project_path("assets", *parts, root=root)


def video_path(*parts: str, root: str | os.PathLike | None = None) -> Path:
    return project_path("videos", *parts, root=root)


def capcut_drafts_root() -> Path:
    override = os.environ.get("CAPCUT_DRAFTS_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data).expanduser() if local_app_data else Path.home() / "AppData" / "Local"
    return base / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def is_within(path: str | os.PathLike, root: str | os.PathLike) -> bool:
    candidate = Path(path).expanduser().resolve()
    boundary = Path(root).expanduser().resolve()
    try:
        candidate.relative_to(boundary)
        return True
    except ValueError:
        return False


def self_test() -> None:
    saved = {name: os.environ.get(name) for name in ROOT_ENV_VARS}
    try:
        for name in ROOT_ENV_VARS:
            os.environ.pop(name, None)
        with tempfile.TemporaryDirectory(prefix="hao-paths-") as temp:
            root = Path(temp)
            (root / MANIFEST_NAMES[0]).write_text("{}", encoding="utf-8")
            nested = root / ".claude" / "skills" / "x"
            nested.mkdir(parents=True)
            assert discover_project_root(nested) == root.resolve()
            assert is_within(root / "assets" / "x", root)
            assert not is_within(root.parent, root)
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    print("project_paths self-test GREEN")


if __name__ == "__main__":
    self_test()
