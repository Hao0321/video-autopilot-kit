# -*- coding: utf-8 -*-
"""Unified, searchable publish packages for Shorts, long-form and remixes."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import runpy
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

from project_paths import discover_project_root, is_within
from publish_contract import (completion_failures, desired_short_status,
                              longform_completion_failures)
from publishing_copy import build_publish_copy, render_copy_markdown
from publish_hub_layout import (HUB, HUB_AUDIT, LEGACY_PUBLISHED,
                                LEGACY_READY as LEGACY_PACKAGE_READY,
                                PUBLISHED, READY, REGISTRY, RESEARCH_QUEUE,
                                START_HERE, cleanup_legacy_generated_state,
                                audit_version_like_media, iter_manifests, migrate_legacy_layout,
                                package_media, retire_superseded_package_media,
                                retire_versioned_job_outputs, root_entry_text,
                                validate_package)
from publish_hub_ops import (consolidate_verified_duplicates,
                             create_miaoli_remix_plan, retire_legacy_ready)
from remix_planner import create_plans as create_remix_plans
from autonomy_standard import (initialize_control_state,
                               queue_summary as autonomy_queue_summary,
                               resolve_review)


HERE = Path(__file__).resolve().parent
ROOT = discover_project_root(HERE)
VIDEOS = ROOT / "videos"
SHORTS_ROOT = VIDEOS / "_INBOX" / "直式-vertical-Shorts-Reels"
LONGFORM_ROOT = VIDEOS / "_INBOX" / "橫式-landscape-YT長片"
LEGACY_READY = VIDEOS / "_待發布Shorts"
STATE_PATH = HERE / "channel_state.json"
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
ROOT_ENTRY = ROOT / "00_發布中樞_從這裡開始.md"
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


def _package_payload(*, content_id: str, kind: str, status: str, source: Path,
                     target: Path, spec: dict[str, Any], copy: dict[str, Any],
                     plan_path: Path | None = None, published: dict[str, Any] | None = None,
                     artifact_revision: int = 1) -> dict:
    stat = target.stat()
    return {
        "schema_version": 2,
        "artifact_revision": artifact_revision,
        "content_id": content_id,
        "format": kind,
        "status": status,
        "topic": copy.get("topic_key"),
        "niche": spec.get("niche", "auto"),
        "place": spec.get("place", ""),
        "what": spec.get("what", target.stem),
        "video": target.name,
        "sha256": _sha256(target),
        "bytes": stat.st_size,
        "file_identity": {"device": stat.st_dev, "inode": stat.st_ino,
                          "hardlinks": getattr(stat, "st_nlink", None)},
        "canonical_source": _relative(source),
        "hub_path": _relative(target.parent),
        "plan": _relative(plan_path) if plan_path and plan_path.exists() else None,
        "copy_research": {
            "status": copy.get("research_status"),
            "last_verified": copy.get("last_verified"),
            "sources": copy.get("sources", []),
            "issues": copy.get("issues", []),
        },
        "published": published,
        "updated_at": _now(),
    }


def _write_package(source: Path, package: Path, filename: str, *, content_id: str,
                   kind: str, status: str, spec: dict[str, Any], copy: dict[str, Any],
                   plan_path: Path | None = None, published: dict[str, Any] | None = None) -> dict:
    source_hash = _sha256(source)
    old_manifest = package / "publish.json"
    old: dict[str, Any] = {}
    if old_manifest.is_file():
        try:
            old = json.loads(old_manifest.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            old = {}
    old_revision = max(1, int(old.get("artifact_revision") or 1))
    artifact_revision = old_revision + 1 if old.get("sha256") not in {None, source_hash} else old_revision
    retire_superseded_package_media(
        package, keep_name=filename, keep_sha256=source_hash
    )
    target = package / filename
    _hardlink(source, target, allow_refresh=status in {"ready", "review"})
    payload = _package_payload(content_id=content_id, kind=kind, status=status,
                               source=source, target=target, spec=spec, copy=copy,
                               plan_path=plan_path, published=published,
                               artifact_revision=artifact_revision)
    _atomic_text(package / "發布文案_可複製.md", render_copy_markdown(copy))
    _atomic_json(package / "publish.json", payload)
    return payload


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


def _reuse_or_relocate_package(content_id: str, source: Path, target: Path) -> dict | None:
    """Keep published packages immutable and relocate unpublished candidates.

    Status is folder metadata in the hub.  A technical rebuild may move a
    candidate between ``review`` and ``ready`` but must not leave a second
    package with the same content ID.
    """
    matches = _content_manifests(content_id)
    published = [path for path in matches if is_within(path, PUBLISHED)]
    if published:
        if len(published) != 1:
            raise RuntimeError(f"multiple published packages for {content_id}")
        manifest = published[0]
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if str(row.get("sha256") or "").lower() != _sha256(source):
            raise RuntimeError(
                f"{content_id} is already published with different media; "
                "use a new content ID or an explicit correction workflow"
            )
        return row

    candidates = [path for path in matches if is_within(path, READY)]
    if len(candidates) > 1:
        reconcile_duplicate_packages()
        candidates = [path for path in _content_manifests(content_id) if is_within(path, READY)]
    if not candidates:
        return None
    current = candidates[0].parent
    if current.resolve() == target.resolve():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError(f"publishing status relocation target already exists: {target}")
    current.rename(target)
    return None


def promote_short(short_id: str | int, *, status: str = "ready",
                  published: dict[str, Any] | None = None) -> dict:
    _, content_id = _short_key(short_id)
    if content_id in _withdrawn_ids():
        raise RuntimeError(
            f"{content_id} was withdrawn by the creator; use a new content ID "
            "or an explicit revival workflow"
        )
    source = find_short_source(short_id)
    if not source:
        raise FileNotFoundError(f"No completed source for Shorts {short_id}")
    spec, source_copy, plan_path = _short_plan(short_id)
    copy = build_publish_copy(spec, source_copy)
    if not copy["release_ready"] and status == "ready":
        status = "review"
    content_id, display = _short_identity(short_id, spec, source)
    base = PUBLISHED if status == "published" else READY
    bucket = "published" if status == "published" else status
    package = base / "shorts" / bucket / f"{content_id}_{_slug(str(spec.get('name', display)), fallback=display)}"
    immutable = _reuse_or_relocate_package(content_id, source, package)
    if immutable is not None:
        return immutable
    filename = f"{content_id}_{display}{source.suffix.lower()}"
    return _write_package(source, package, filename, content_id=content_id,
                          kind="shorts", status=status, spec=spec, copy=copy,
                          plan_path=plan_path, published=published)


def register_completed_short(folder_id: str | int, qa: dict[str, Any]) -> dict[str, Any]:
    """Commit a green Shorts build to the single publishing control plane."""
    short_id, content_id = _short_key(folder_id)
    requested_status = desired_short_status(qa)
    package = promote_short(short_id, status=requested_status)
    registry = rebuild_index()
    failures = [row for row in completion_failures(
        root=ROOT, shorts_root=SHORTS_ROOT, manifests=iter_manifests()
    ) if row.get("id") == content_id]
    if failures:
        raise RuntimeError(f"publishing registration failed for {content_id}: {failures}")
    return {
        "status": "REGISTERED",
        "content_id": content_id,
        "hub_status": package.get("status"),
        "package": package.get("hub_path"),
        "sha256": package.get("sha256"),
        "registry": registry.get("hub"),
        "start_here": _relative(START_HERE),
    }


def register_completed_remix(content_id: str, source: str | Path,
                             qa: dict[str, Any], *,
                             spec: dict[str, Any] | None = None,
                             source_copy: dict[str, Any] | None = None,
                             plan_path: str | Path | None = None) -> dict[str, Any]:
    """Commit one technically green remix to the publishing control plane.

    Remixes are first-class release candidates, not loose renders hidden in a
    planning folder. They keep a distinct ``R###`` identity, remain in the
    ``review`` bucket until creator approves the aesthetic review, and reuse the
    same immutable/one-package rules as Shorts and long-form videos.
    """
    normalized_id = str(content_id).strip().upper()
    if not re.fullmatch(r"R\d{3,}", normalized_id):
        raise ValueError(f"invalid remix content ID: {content_id!r}")
    media = Path(source).resolve()
    if not media.is_file() or media.suffix.lower() not in VIDEO_SUFFIXES:
        raise FileNotFoundError(f"No canonical remix output: {media}")
    requested_status = desired_short_status(qa)
    plan = Path(plan_path).resolve() if plan_path else None
    plan_data: dict[str, Any] = {}
    if plan and plan.is_file():
        try:
            plan_data = json.loads(plan.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            plan_data = {}
    title = str((spec or {}).get("what") or plan_data.get("title") or media.stem)
    normalized_spec = {
        "name": plan_data.get("title") or title,
        "niche": "auto",
        "place": "",
        "what": title,
        **(spec or {}),
    }
    copy = build_publish_copy(normalized_spec, source_copy or {
        "yt_title": title,
        "text": title,
    })
    if not copy["release_ready"] and requested_status == "ready":
        requested_status = "review"
    package = (READY / "remix" / requested_status /
               f"{normalized_id}_{_slug(str(normalized_spec.get('name') or title), fallback=media.stem)}")
    immutable = _reuse_or_relocate_package(normalized_id, media, package)
    payload = immutable or _write_package(
        media, package,
        f"{normalized_id}_{_slug(title, fallback=media.stem)}{media.suffix.lower()}",
        content_id=normalized_id, kind="remix", status=requested_status,
        spec=normalized_spec, copy=copy, plan_path=plan,
    )
    registry = rebuild_index()
    manifests = _content_manifests(normalized_id)
    failures: list[dict[str, Any]] = []
    if len(manifests) != 1:
        failures.append({"id": normalized_id, "error": "remix must have exactly one package",
                         "packages": [_relative(path.parent) for path in manifests]})
    else:
        failures.extend(validate_package(manifests[0]))
        if str(payload.get("sha256") or "").lower() != _sha256(media):
            failures.append({"id": normalized_id, "error": "remix package hash is stale"})
        if str(payload.get("canonical_source") or "") != _relative(media):
            failures.append({"id": normalized_id, "error": "remix canonical source is stale"})
    if failures:
        raise RuntimeError(f"publishing registration failed for {normalized_id}: {failures}")
    return {
        "status": "REGISTERED",
        "content_id": normalized_id,
        "hub_status": payload.get("status"),
        "package": payload.get("hub_path"),
        "sha256": payload.get("sha256"),
        "registry": registry.get("hub"),
        "start_here": _relative(START_HERE),
    }


def _state_entries() -> list[dict[str, Any]]:
    if not STATE_PATH.is_file():
        return []
    raw = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    for key in ("videos", "published", "content"):
        if isinstance(raw.get(key), list):
            return raw[key]
    return raw if isinstance(raw, list) else []


def import_published_shorts() -> list[dict]:
    results = []
    for row in _state_entries():
        match = re.match(r"s(\d+)_", str(row.get("name", "")), re.I)
        if not match or not row.get("published"):
            continue
        short_id = int(match.group(1))
        if not find_short_source(short_id):
            continue
        details = {"date": row.get("published"), "platform": "youtube",
                   "video_id": row.get("video_id") or None,
                   "url": (f"https://youtu.be/{row['video_id']}" if row.get("video_id") else None),
                   "snapshots": row.get("snapshots", {}),
                   "metrics": row.get("metrics", {}),
                   "note": row.get("note"),
                   "evaluation": evaluate_published(row)}
        results.append(promote_short(short_id, status="published", published=details))
    return results


def evaluate_published(row: dict[str, Any]) -> dict[str, Any]:
    yt = (row.get("metrics") or {}).get("yt", {}).get("D2", {})
    overdue = [name for name, snapshot in (row.get("snapshots") or {}).items()
               if not snapshot.get("done_on") and not snapshot.get("waived")]
    if not yt:
        return {"status": "OUTCOME_DATA_NEEDED", "overdue_or_open": overdue,
                "reuse": "可做題材／旅程再製；尚不可從成效宣稱勝出"}
    duration = float(yt.get("dur_s") or 0)
    average = float(yt.get("avg_watch_s") or 0)
    ratio = round(average / duration, 3) if duration else None
    observations = []
    if ratio and ratio > 1:
        observations.append("平均觀看超過片長，具重播訊號")
    if yt.get("swipe_pct") is not None:
        observations.append(f"滑走率 {yt['swipe_pct']}%，再製時優先重做首秒")
    return {"status": "MEASURED", "yt_d2": yt, "average_watch_ratio": ratio,
            "observations": observations, "overdue_or_open": overdue,
            "reuse": "保留有效 payoff，換新 Hook 與集合敘事"}


def migrate_ready_shorts() -> list[dict]:
    ids = {int(match.group(1)) for path in LEGACY_READY.glob("*.mp4")
           if (match := re.match(r"s(\d+)_", path.name, re.I))}
    ids.update(int(path.parent.parent.name) for path in SHORTS_ROOT.glob("*/_out/current.mp4")
               if path.parent.parent.name.isdigit())
    published_ids = {int(match.group(1)) for row in _state_entries()
                     if row.get("published") and
                     (match := re.match(r"s(\d+)_", str(row.get("name", "")), re.I))}
    results = []
    withdrawn = _withdrawn_ids()
    for short_id in sorted(ids - published_ids):
        content_id = f"S{short_id:03d}"
        if content_id in withdrawn:
            continue
        existing = _content_manifests(content_id)
        status = "review"
        if len(existing) == 1:
            try:
                current_status = str(json.loads(
                    existing[0].read_text(encoding="utf-8-sig")
                ).get("status") or "review")
                if current_status in {"ready", "review", "draft"}:
                    status = current_status
            except (OSError, ValueError):
                pass
        else:
            quality_path = SHORTS_ROOT / str(short_id) / "_out" / "_qa" / "QUALITY_95.json"
            if quality_path.is_file():
                try:
                    quality_status = str(json.loads(
                        quality_path.read_text(encoding="utf-8-sig")
                    ).get("status") or "REVIEW").upper()
                    if quality_status in {"CERTIFIED_95", "PASS", "GREEN"}:
                        status = "ready"
                except (OSError, ValueError):
                    pass
        results.append(promote_short(short_id, status=status))
    return results


def _longform_candidates() -> list[tuple[int, Path, str]]:
    candidates: list[tuple[int, Path, str]] = []
    dynamic_ids: set[int] = set()
    for current in sorted(LONGFORM_ROOT.glob("*/_out/current.mp4")) if LONGFORM_ROOT.exists() else []:
        folder = current.parent.parent.name
        if not folder.isdigit():
            continue
        number = int(folder)
        dynamic_ids.add(number)
        quality_path = current.parent / "_qa" / "QUALITY_95.json"
        status = "review"
        if quality_path.is_file():
            try:
                quality_status = str(json.loads(
                    quality_path.read_text(encoding="utf-8-sig")
                ).get("status") or "REVIEW").upper()
                if quality_status in {"CERTIFIED_95", "PASS", "GREEN"}:
                    status = "ready"
            except (OSError, ValueError):
                pass
        candidates.append((number, current, status))
    legacy: list[tuple[int, Path, str]] = []  # PUBLIC_FIXTURE: no maintainer legacy paths
    candidates.extend((number, path, status) for number, path, status in legacy
                      if number not in dynamic_ids and path.is_file())
    return candidates


def _longform_state(number: int) -> dict[str, Any] | None:
    expected = f"長片{number:02d}"
    return next((row for row in _state_entries() if row.get("name") == expected), None)


def import_longform() -> list[dict]:
    results = []
    for number, source, local_status in _longform_candidates():
        content_id = f"L{number:03d}"
        title = re.sub(r"^(?:_完成_)?長片\d+_?", "", source.stem)
        title = re.sub(r"_(?:v\d+|初剪)$", "", title) or source.stem
        spec = {"name": source.stem, "niche": "auto", "what": title, "place": ""}
        copy = build_publish_copy(spec, {"yt_title": title, "text": title})
        state = _longform_state(number)
        status = "published" if state and state.get("published") else local_status
        base = PUBLISHED if status == "published" else READY
        package = base / "longform" / status / f"{content_id}_{_slug(title, fallback=source.stem)}"
        published = None
        if status == "published":
            published = {"date": state.get("published"), "platform": "youtube",
                         "video_id": state.get("video_id") or None,
                         "url": (f"https://youtu.be/{state['video_id']}" if state.get("video_id") else None),
                         "local_source_state": local_status,
                         "source_warning": ("本機檔名仍標示初剪，發布主檔需人工核對"
                                            if "初剪" in source.stem else None),
                         "evaluation": evaluate_published(state)}
        immutable = _reuse_or_relocate_package(content_id, source, package)
        if immutable is not None:
            results.append(immutable)
            continue
        results.append(_write_package(source, package, f"{content_id}_{_slug(title, fallback=source.stem)}.mp4",
                                      content_id=content_id, kind="longform", status=status,
                                      spec=spec, copy=copy, published=published))
    return results


def register_completed_longform(folder_id: str | int, qa: dict[str, Any]) -> dict[str, Any]:
    number = int(folder_id)
    source = LONGFORM_ROOT / str(number) / "_out" / "current.mp4"
    if not source.is_file():
        raise FileNotFoundError(f"No canonical long-form output: {source}")
    requested_status = desired_short_status(qa)
    rows = {row[0]: row for row in _longform_candidates()}
    if number not in rows:
        raise RuntimeError(f"Long-form {number} is not discoverable by the publishing control plane")
    # import_longform uses canonical-first discovery and immutable package rules.
    imported = import_longform()
    content_id = f"L{number:03d}"
    package = next((row for row in imported if row.get("content_id") == content_id), None)
    if package is None:
        raise RuntimeError(f"publishing registration failed for {content_id}")
    if package.get("status") != requested_status and package.get("status") != "published":
        raise RuntimeError(f"unexpected long-form publish status for {content_id}: {package.get('status')}")
    registry = rebuild_index()
    failures = [row for row in longform_completion_failures(
        root=ROOT, longform_root=LONGFORM_ROOT, manifests=iter_manifests()
    ) if row.get("id") == content_id]
    if failures:
        raise RuntimeError(f"publishing registration failed for {content_id}: {failures}")
    return {"status": "REGISTERED", "content_id": content_id,
            "hub_status": package.get("status"), "package": package.get("hub_path"),
            "sha256": package.get("sha256"), "registry": registry.get("hub"),
            "start_here": _relative(START_HERE)}


def _package_rows() -> list[dict[str, Any]]:
    rows = []
    for base in (READY, PUBLISHED):
        for path in base.rglob("publish.json") if base.exists() else []:
            row = json.loads(path.read_text(encoding="utf-8-sig"))
            row["package"] = _relative(path.parent)
            rows.append(row)
    return sorted(rows, key=lambda row: row["content_id"])


def migrate_status_layout() -> list[dict[str, str]]:
    moved = []
    status_names = {"ready", "review", "draft", "published", "planned"}
    for base in (READY, PUBLISHED):
        if not base.exists():
            continue
        for kind in ("shorts", "longform", "remix"):
            kind_dir = base / kind
            if not kind_dir.is_dir():
                continue
            for package in list(kind_dir.iterdir()):
                if not package.is_dir() or package.name in status_names:
                    continue
                manifest = package / "publish.json"
                if not manifest.is_file():
                    continue
                row = json.loads(manifest.read_text(encoding="utf-8-sig"))
                status = "published" if base == PUBLISHED else row.get("status", "review")
                target = kind_dir / status / package.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise RuntimeError(f"layout migration target exists: {target}")
                package.rename(target)
                moved.append({"from": _relative(package), "to": _relative(target)})
    return moved


def refresh_package_identities() -> int:
    changed = 0
    for manifest in [*READY.rglob("publish.json"), *PUBLISHED.rglob("publish.json")]:
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        video = manifest.parent / row["video"]
        if not video.is_file():
            continue
        stat = video.stat()
        identity = {"device": stat.st_dev, "inode": stat.st_ino,
                    "hardlinks": getattr(stat, "st_nlink", None)}
        if row.get("file_identity") == identity and row.get("bytes") == stat.st_size:
            continue
        row["bytes"], row["file_identity"], row["updated_at"] = stat.st_size, identity, _now()
        _atomic_json(manifest, row)
        changed += 1
    return changed


def reconcile_duplicate_packages() -> list[dict[str, str]]:
    manifests = [*READY.rglob("publish.json"), *PUBLISHED.rglob("publish.json")]
    by_id: dict[str, list[Path]] = {}
    for manifest in manifests:
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        by_id.setdefault(row["content_id"], []).append(manifest)
    retired = []
    for content_id, items in by_id.items():
        if len(items) < 2:
            continue
        keep = min(items, key=lambda path: (0 if is_within(path, PUBLISHED) else 1, str(path)))
        keep_row = json.loads(keep.read_text(encoding="utf-8-sig"))
        for stale in items:
            if stale == keep:
                continue
            row = json.loads(stale.read_text(encoding="utf-8-sig"))
            stale_video, keep_video = stale.parent / row["video"], keep.parent / keep_row["video"]
            if not is_within(stale.parent, READY) or _sha256(stale_video) != _sha256(keep_video):
                raise RuntimeError(f"cannot retire unverified duplicate package: {stale.parent}")
            shutil.rmtree(stale.parent)
            retired.append({"content_id": content_id, "retired": _relative(stale.parent),
                            "kept": _relative(keep.parent)})
    return retired


def rebuild_index() -> dict[str, Any]:
    moved = migrate_status_layout()
    retired = reconcile_duplicate_packages()
    refreshed = refresh_package_identities()
    rows = _package_rows()
    payload = {"schema_version": 1, "updated_at": _now(), "layout_migrations": moved,
               "duplicate_packages_retired": retired,
               "identity_refreshes": refreshed, "items": rows}
    _atomic_json(REGISTRY, payload)
    research_queue = []
    for row in rows:
        research = row.get("copy_research") or {}
        if row["status"] == "published" or research.get("status") == "CURRENT":
            continue
        research_queue.append({
            "content_id": row["content_id"], "format": row["format"],
            "topic": row.get("topic"), "place": row.get("place"), "what": row.get("what"),
            "status": research.get("status", "UNRESEARCHED"),
            "action": "發布前搜尋最新官方／第一方資料，更新 topic_research_catalog.json",
            "suggested_query": " ".join(value for value in
                                        (row.get("place"), row.get("what"), "官方 最新") if value),
            "package": row["package"],
        })
    _atomic_json(RESEARCH_QUEUE, {"schema_version": 1, "updated_at": _now(),
                                  "items": research_queue})
    payload["research_queue"] = _relative(RESEARCH_QUEUE)
    payload["research_queue_count"] = len(research_queue)
    _atomic_json(REGISTRY, payload)
    for base, heading in ((READY, "準備發佈"), (PUBLISHED, "已發佈")):
        selected = [row for row in rows if is_within(ROOT / row["package"], base)]
        lines = [f"# {heading}影片索引", "", "| 編號 | 類型 | 題材 | 內容 | 狀態 | 發佈包 |",
                 "|---|---|---|---|---|---|"]
        for row in selected:
            package_path = ROOT / row["package"]
            package_link = os.path.relpath(package_path, base).replace(os.sep, "/")
            video_link = f"{package_link}/{row['video']}"
            copy_link = f"{package_link}/發布文案_可複製.md"
            lines.append(f"| {row['content_id']} | {row['format']} | {row.get('niche') or '-'} | "
                         f"{row.get('what') or '-'} | {row['status']} | "
                         f"[開啟包]({package_link}) · [播放成片]({video_link}) · "
                         f"[複製文案]({copy_link}) |")
        _atomic_text(base / "INDEX.md", "\n".join(lines) + "\n")
    ready_rows = [row for row in rows if is_within(ROOT / row["package"], READY)]
    published_rows = [row for row in rows if is_within(ROOT / row["package"], PUBLISHED)]
    initialize_control_state()
    review_queue = autonomy_queue_summary()
    active_reviews = len(review_queue.get("active") or [])
    start = [
        "# 發布中樞｜從這裡開始",
        "",
        "> 這是唯一入口。不要再到 INBOX、planning 或舊的待發布資料夾找成片。",
        "",
        f"- **準備發布：{len(ready_rows)} 支** → [READY 索引](READY/INDEX.md)",
        f"- **已發布：{len(published_rows)} 支** → [PUBLISHED 索引](PUBLISHED/INDEX.md)",
        f"- **待查證文案：{len(research_queue)} 支** → [_STATE/publish_research_queue.json](_STATE/publish_research_queue.json)",
        f"- **待 creator 審片：{active_reviews} 支** → [_STATE/hao_review_queue.json](_STATE/hao_review_queue.json)",
        "- **自動化能力缺口** → [_STATE/autonomy_gap_backlog.json](_STATE/autonomy_gap_backlog.json)",
        "- **機器總表** → [_STATE/publish_registry.json](_STATE/publish_registry.json)",
        "- **遷移／退役紀錄** → [_AUDIT](_AUDIT/)",
        "",
        "## 固定操作",
        "",
        "1. 要發片：只開 `READY/INDEX.md`，再進該片獨立包。",
        "2. 每包只有一支已命名成片、`發布文案_可複製.md`、`publish.json`。",
        "3. 發布後把整包切換到 `PUBLISHED`；不得複製第二包。",
        "4. `v2 / FINAL / old / backup / 初剪` 只存在歷史封存，不得進發布包。",
        "5. 重剪由原始素材產生新 content ID，不串接已燒字幕成片。",
        "",
        f"更新時間：{_now()}",
    ]
    _atomic_text(START_HERE, "\n".join(start) + "\n")
    _atomic_text(ROOT_ENTRY, _root_entry_text())
    payload["start_here"] = _relative(START_HERE)
    payload["root_entry"] = _relative(ROOT_ENTRY)
    payload["hub"] = _relative(HUB)
    payload["legacy_generated_state_removed"] = cleanup_legacy_generated_state()
    _atomic_json(REGISTRY, payload)
    return payload


def audit() -> dict[str, Any]:
    failures, rows = [], _package_rows()
    manifests = list(iter_manifests())
    for manifest in manifests:
        failures.extend(validate_package(manifest))
    by_id: dict[str, list[str]] = {}
    for row in rows:
        by_id.setdefault(str(row["content_id"]), []).append(str(row["package"]))
    for content_id, packages in by_id.items():
        if len(packages) > 1:
            failures.append({"id": content_id, "error": "content ID appears in multiple packages",
                             "packages": packages})
    for legacy in (LEGACY_PACKAGE_READY, LEGACY_PUBLISHED):
        if legacy.exists() and any(legacy.rglob("publish.json")):
            failures.append({"error": "legacy publishing root still contains packages",
                             "path": _relative(legacy)})
    if not START_HERE.is_file():
        failures.append({"error": "missing single publishing entry point",
                         "path": _relative(START_HERE)})
    if not ROOT_ENTRY.is_file():
        failures.append({"error": "missing project-root publishing shortcut",
                         "path": _relative(ROOT_ENTRY)})
    withdrawn = _withdrawn_ids()
    completion = completion_failures(
        root=ROOT, shorts_root=SHORTS_ROOT, manifests=manifests
    )
    failures.extend(row for row in completion
                    if str(row.get("id") or "").upper() not in withdrawn)
    failures.extend(longform_completion_failures(
        root=ROOT, longform_root=LONGFORM_ROOT, manifests=manifests
    ))
    downgrade_audit = audit_version_like_media()
    return {"status": "GREEN" if not failures else "RED", "packages": len(rows),
            "hub": _relative(HUB), "start_here": _relative(START_HERE),
            "by_format": {kind: sum(row["format"] == kind for row in rows)
                          for kind in ("shorts", "longform", "remix")},
            "failures": failures,
            "version_like_media": {
                "status": downgrade_audit["status"],
                "count": downgrade_audit["count"],
                "publish_blockers": downgrade_audit["publish_blockers"],
                "report": _relative(HUB_AUDIT / "version-like-media-latest.json"),
            }}


def withdraw_content(content_ids: list[str], *, reason: str,
                     actor: str = "creator") -> dict[str, Any]:
    """Withdraw unpublished artifacts without deleting media or losing history.

    Withdrawn IDs are excluded from publishing discovery and completion audits.
    Published packages are immutable and cannot be withdrawn through this path.
    """
    normalized = sorted({str(value or "").strip().upper() for value in content_ids})
    if not normalized or any(not re.fullmatch(r"[SLR]\d{3}", value)
                             for value in normalized):
        raise ValueError("content IDs must look like S023, L004, or R001")
    if not str(reason or "").strip():
        raise ValueError("withdrawal reason is required")
    published = {str(row.get("content_id") or "").upper()
                 for row in _package_rows() if row.get("status") == "published"}
    conflicts = sorted(set(normalized) & published)
    if conflicts:
        raise RuntimeError(f"published content is immutable: {', '.join(conflicts)}")
    state = _withdrawn_state()
    items = list(state.get("items") or [])
    by_id = {str(row.get("content_id") or "").upper(): row for row in items}
    active = autonomy_queue_summary().get("active") or []
    resolved_queue_ids: list[str] = []
    for content_id in normalized:
        artifacts: list[str] = []
        match = re.fullmatch(r"S(\d{3})", content_id)
        if match:
            current = SHORTS_ROOT / str(int(match.group(1))) / "_out" / "current.mp4"
            if current.is_file():
                artifacts.append(_relative(current))
        row = by_id.get(content_id, {"content_id": content_id})
        row.update(state="WITHDRAWN", reason=reason, actor=actor,
                   artifacts=artifacts, updated_at=_now())
        row.setdefault("withdrawn_at", _now())
        if content_id not in by_id:
            items.append(row)
            by_id[content_id] = row
        for queued in active:
            if queued.get("content_id") != content_id:
                continue
            resolve_review(str(queued["queue_id"]), actor=actor,
                           decision=f"WITHDRAWN_BY_CREATOR: {reason}")
            resolved_queue_ids.append(str(queued["queue_id"]))
    state.update(schema_version=1, updated_at=_now(), items=items)
    _atomic_json(WITHDRAWN_PATH, state)
    rebuild_index()
    return {"status": "WITHDRAWN", "content_ids": normalized,
            "ledger": _relative(WITHDRAWN_PATH),
            "resolved_review_items": resolved_queue_ids}


def mark_published(content_id: str, *, date: str | None = None,
                   platform: str = "reported_by_creator", note: str = "") -> dict[str, Any]:
    """Atomically move one existing candidate into the immutable published lane.

    This changes publishing state only.  The authoritative media file and its
    SHA-256 are preserved, and no public upload is performed.
    """
    normalized = str(content_id or "").strip().upper()
    if not re.fullmatch(r"[SLR]\d{3}", normalized):
        raise ValueError("content_id must look like S021, L004, or R001")
    matches = _content_manifests(normalized)
    if len(matches) != 1:
        raise RuntimeError(f"{normalized} must have exactly one publishing package; found {len(matches)}")
    manifest = matches[0]
    row = json.loads(manifest.read_text(encoding="utf-8-sig"))
    old_package = manifest.parent
    if is_within(manifest, PUBLISHED):
        return {"status": "ALREADY_PUBLISHED", "content_id": normalized,
                "package": _relative(old_package), "sha256": row.get("sha256")}
    if not is_within(manifest, READY):
        raise RuntimeError(f"{normalized} is outside READY and cannot be promoted")
    kind = str(row.get("format") or "").strip()
    if kind not in {"shorts", "longform", "remix"}:
        raise RuntimeError(f"{normalized} has unknown format {kind!r}")
    new_package = PUBLISHED / kind / "published" / old_package.name
    new_package.parent.mkdir(parents=True, exist_ok=True)
    if new_package.exists():
        raise RuntimeError(f"published target already exists: {new_package}")
    before_sha = str(row.get("sha256") or "")
    old_package.rename(new_package)
    new_manifest = new_package / "publish.json"
    row["status"] = "published"
    row["hub_path"] = _relative(new_package)
    row["published"] = {
        "date": date or None,
        "reported_on": datetime.now().astimezone().date().isoformat(),
        "platform": platform,
        "video_id": None,
        "url": None,
        "note": note or "creator confirmed this content was already published; exact date/platform ID not supplied.",
    }
    row["updated_at"] = _now()
    _atomic_json(new_manifest, row)
    video = new_package / str(row.get("video") or "")
    if not video.is_file() or _sha256(video) != before_sha:
        raise RuntimeError(f"published promotion integrity check failed for {normalized}")
    audit_row = {
        "schema_version": 1, "action": "mark_published", "content_id": normalized,
        "from": _relative(old_package), "to": _relative(new_package),
        "sha256": before_sha, "published": row["published"], "at": _now(),
    }
    _atomic_json(HUB_AUDIT / f"mark-published-{normalized}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json", audit_row)
    rebuild_index()
    return {"status": "PUBLISHED", "content_id": normalized,
            "package": _relative(new_package), "sha256": before_sha,
            "published": row["published"]}


def selftest() -> None:
    from publish_hub_cli import selftest as cli_selftest
    cli_selftest(sys.modules[__name__])


def open_hub() -> dict[str, Any]:
    from publish_hub_cli import open_hub as cli_open_hub
    return cli_open_hub(sys.modules[__name__])


def main(argv: list[str] | None = None) -> int:
    from publish_hub_cli import main as cli_main
    return cli_main(argv, sys.modules[__name__])


if __name__ == "__main__":
    raise SystemExit(main())
