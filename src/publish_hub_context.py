"""Publish hub context; canonical implementation."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import runpy
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from project_paths import discover_project_root
from publish_contract import reviewed_artifact_ready
from publish_hub_layout import HUB, PUBLISHED, READY, iter_manifests, root_entry_text


HERE = Path(__file__).resolve().parent


ROOT = discover_project_root(HERE)


VIDEOS = ROOT / "videos"


SHORTS_ROOT = VIDEOS / "_INBOX" / "直式-vertical-Shorts-Reels"


LONGFORM_ROOT = VIDEOS / "_INBOX" / "橫式-landscape-YT長片"


LEGACY_READY = VIDEOS / "_待發布Shorts"


STATE_PATH = HERE / "channel_state.json"


INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


WITHDRAWN_PATH = HUB / "_STATE" / "withdrawn_content.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".publish-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _atomic_json(path: Path, payload: Any) -> None:
    _atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _root_entry_text() -> str:
    return root_entry_text(HERE / "publish_hub.py", ROOT)


def _withdrawn_state() -> dict[str, Any]:
    if not WITHDRAWN_PATH.is_file():
        return {"schema_version": 1, "updated_at": None, "items": []}
    return json.loads(WITHDRAWN_PATH.read_text(encoding="utf-8-sig"))


def _withdrawn_ids() -> set[str]:
    return {str(row.get("content_id") or "").upper()
            for row in _withdrawn_state().get("items") or []
            if row.get("state") == "WITHDRAWN"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _slug(text: str, *, fallback: str) -> str:
    clean = INVALID.sub("_", text).strip(" ._")
    clean = re.sub(r"\s+", "_", clean)
    return clean[:80] or fallback


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _safe_eval(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_safe_eval(row, env) for row in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Dict):
        return {_safe_eval(k, env): _safe_eval(v, env)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand, env)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _safe_eval(node.left, env) + _safe_eval(node.right, env)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        value = {}
        for keyword in node.keywords:
            value[keyword.arg] = _safe_eval(keyword.value, env)
        return value
    raise ValueError(f"unsupported plan expression: {type(node).__name__}")


def load_plan(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        return {}, {}
    env: dict[str, Any] = {}
    for node in ast.parse(path.read_text(encoding="utf-8-sig")).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            env[target.id] = _safe_eval(node.value, env)
        except (KeyError, TypeError, ValueError):
            continue
    spec, copy = env.get("SPEC", {}), env.get("COPY", {})
    if spec and copy:
        return spec, copy
    # Newer plans are intentionally modular and may build SPEC/COPY with
    # helper calls that the conservative AST reader cannot evaluate. These
    # are trusted local plans, so execute them only as a compatibility
    # fallback instead of silently publishing a package named "current".
    runtime = runpy.run_path(str(path))
    return runtime.get("SPEC", {}), runtime.get("COPY", {})


def _short_key(short_id: str | int) -> tuple[str, str]:
    """Normalize a base or split-battle Shorts folder id."""
    raw = str(short_id).strip()
    if raw.isdigit():
        return raw, f"S{int(raw):03d}"
    head, sep, tail = raw.partition("-")
    if sep and head.isdigit() and tail and all(part.isdigit() for part in tail.split("-")):
        return raw, f"S{int(head):03d}-{tail}"
    raise ValueError(f"invalid Shorts folder id: {short_id!r}")


def _short_plan(short_id: str | int) -> tuple[dict[str, Any], dict[str, Any], Path]:
    folder_key, _ = _short_key(short_id)
    path = SHORTS_ROOT / folder_key / "_plan.py"
    spec, copy = load_plan(path)
    return spec, copy, path


def find_short_source(short_id: str | int) -> Path | None:
    folder_key, _ = _short_key(short_id)
    current = SHORTS_ROOT / folder_key / "_out" / "current.mp4"
    if current.is_file():
        return current
    if LEGACY_READY.is_dir():
        matches = sorted(LEGACY_READY.glob(f"s{folder_key}_*.mp4"))
        if matches:
            return matches[0]
    published = VIDEOS / "_planning" / "Shorts_13-18"
    matches = sorted(published.glob(f"s{folder_key}_*.mp4")) if published.is_dir() else []
    if matches:
        return matches[0]
    out_dir = SHORTS_ROOT / folder_key / "_out"
    candidates = [path for path in out_dir.glob("*.mp4")
                  if all(token not in path.stem.lower() for token in ("_cap", "_vis"))]
    return sorted(candidates)[0] if candidates else None


def _short_identity(short_id: str | int, spec: dict[str, Any], source: Path) -> tuple[str, str]:
    _, content_id = _short_key(short_id)
    display = str(spec.get("what") or spec.get("place") or spec.get("name") or source.stem)
    return content_id, _slug(display, fallback=source.stem)


def _hardlink(source: Path, target: Path, *, allow_refresh: bool = False) -> None:
    """Link ``source`` into a package, optionally refreshing an unpublished item.

    Ready/review packages are working release candidates: a rebuild of the
    canonical source must update them. Published packages remain immutable.
    The refresh is staged beside the target and swapped atomically so a failed
    copy cannot leave the publishing hub with a partial video.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if _sha256(target) == _sha256(source):
            return
        if not allow_refresh:
            raise RuntimeError(f"target exists with different content: {target}")
        fd, staged_name = tempfile.mkstemp(
            prefix=f".{target.stem}-refresh-", suffix=target.suffix, dir=target.parent
        )
        os.close(fd)
        staged = Path(staged_name)
        staged.unlink()
        try:
            try:
                os.link(source, staged)
            except OSError:
                shutil.copy2(source, staged)
            os.replace(staged, target)
        finally:
            if staged.exists():
                staged.unlink()
        return
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _content_manifests(content_id: str) -> list[Path]:
    matches: list[Path] = []
    for manifest in iter_manifests():
        try:
            row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if str(row.get("content_id") or "") == content_id:
            matches.append(manifest)
    return matches


def _state_entries() -> list[dict[str, Any]]:
    if not STATE_PATH.is_file():
        return []
    raw = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    for key in ("videos", "published", "content"):
        if isinstance(raw.get(key), list):
            return raw[key]
    return raw if isinstance(raw, list) else []


def _has_current_visual_review(source: Path) -> bool:
    quality_path = source.parent / "_qa" / "QUALITY_95.json"
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8-sig"))
        return reviewed_artifact_ready(source, quality)
    except (OSError, ValueError, TypeError):
        return False


def _longform_candidates() -> list[tuple[int, Path, str]]:
    candidates: list[tuple[int, Path, str]] = []
    for current in sorted(LONGFORM_ROOT.glob("*/_out/current.mp4")) if LONGFORM_ROOT.exists() else []:
        folder = current.parent.parent.name
        if not folder.isdigit():
            continue
        number = int(folder)
        status = "ready" if _has_current_visual_review(current) else "review"
        candidates.append((number, current, status))
    return candidates


def _longform_state(number: int) -> dict[str, Any] | None:
    expected = f"長片{number:02d}"
    return next((row for row in _state_entries() if row.get("name") == expected), None)


def _package_rows() -> list[dict[str, Any]]:
    rows = []
    for base in (READY, PUBLISHED):
        for path in base.rglob("publish.json") if base.exists() else []:
            row = json.loads(path.read_text(encoding="utf-8-sig"))
            row["package"] = _relative(path.parent)
            rows.append(row)
    return sorted(rows, key=lambda row: row["content_id"])

# PUBLIC_FIXTURE: retired legacy routing contains no maintainer media paths.
