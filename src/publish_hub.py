# -*- coding: utf-8 -*-
"""Unified, searchable publish packages for Shorts, long-form and remixes."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
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
from publishing_copy import build_publish_copy, render_copy_markdown
from publish_hub_layout import (HUB, HUB_AUDIT, LEGACY_PUBLISHED,
                                LEGACY_READY as LEGACY_PACKAGE_READY,
                                PUBLISHED, READY, REGISTRY, RESEARCH_QUEUE,
                                START_HERE, cleanup_legacy_generated_state,
                                audit_version_like_media, iter_manifests, migrate_legacy_layout,
                                package_media, retire_superseded_package_media,
                                retire_versioned_job_outputs, validate_package)
from publish_hub_ops import (consolidate_verified_duplicates,
                             create_miaoli_remix_plan, retire_legacy_ready)
from remix_planner import create_plans as create_remix_plans


HERE = Path(__file__).resolve().parent
ROOT = discover_project_root(HERE)
VIDEOS = ROOT / "videos"
SHORTS_ROOT = VIDEOS / "_INBOX" / "直式-vertical-Shorts-Reels"
LEGACY_READY = VIDEOS / "_待發布Shorts"
STATE_PATH = HERE / "channel_state.json"
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


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
    return env.get("SPEC", {}), env.get("COPY", {})


def _short_plan(short_id: int) -> tuple[dict[str, Any], dict[str, Any], Path]:
    path = SHORTS_ROOT / str(short_id) / "_plan.py"
    spec, copy = load_plan(path)
    return spec, copy, path


def find_short_source(short_id: int) -> Path | None:
    current = SHORTS_ROOT / str(short_id) / "_out" / "current.mp4"
    if current.is_file():
        return current
    if LEGACY_READY.is_dir():
        matches = sorted(LEGACY_READY.glob(f"s{short_id}_*.mp4"))
        if matches:
            return matches[0]
    published = VIDEOS / "_planning" / "Shorts_13-18"
    matches = sorted(published.glob(f"s{short_id}_*.mp4")) if published.is_dir() else []
    if matches:
        return matches[0]
    out_dir = SHORTS_ROOT / str(short_id) / "_out"
    candidates = [path for path in out_dir.glob("*.mp4")
                  if all(token not in path.stem.lower() for token in ("_cap", "_vis"))]
    return sorted(candidates)[0] if candidates else None


def _short_identity(short_id: int, spec: dict[str, Any], source: Path) -> tuple[str, str]:
    content_id = f"S{short_id:03d}"
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


def promote_short(short_id: int, *, status: str = "ready",
                  published: dict[str, Any] | None = None) -> dict:
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
    filename = f"{content_id}_{display}{source.suffix.lower()}"
    return _write_package(source, package, filename, content_id=content_id,
                          kind="shorts", status=status, spec=spec, copy=copy,
                          plan_path=plan_path, published=published)


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
    return [promote_short(short_id) for short_id in sorted(ids - published_ids)]


def _longform_candidates() -> list[tuple[int, Path, str]]:
    candidates = [
        (1, VIDEOS / "_INBOX" / "橫式-landscape-YT長片" / "1" / "_完成_長片01_AI工具_v1.mp4", "ready"),
        (2, VIDEOS / "_planning" / "長片02_AI遊戲" / "build" / "out" / "長片02_AI遊戲_v4.mp4", "review"),
        (3, VIDEOS / "_planning" / "長片03_SocialPost" / "build" / "out" / "長片03_SocialPost_初剪.mp4", "draft"),
    ]
    return [(number, path, status) for number, path, status in candidates if path.is_file()]


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
        results.append(_write_package(source, package, f"{content_id}_{_slug(title, fallback=source.stem)}.mp4",
                                      content_id=content_id, kind="longform", status=status,
                                      spec=spec, copy=copy, published=published))
    return results


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
            lines.append(f"| {row['content_id']} | {row['format']} | {row.get('niche') or '-'} | "
                         f"{row.get('what') or '-'} | {row['status']} | `{row['package']}` |")
        _atomic_text(base / "INDEX.md", "\n".join(lines) + "\n")
    ready_rows = [row for row in rows if is_within(ROOT / row["package"], READY)]
    published_rows = [row for row in rows if is_within(ROOT / row["package"], PUBLISHED)]
    start = [
        "# 發布中樞｜從這裡開始",
        "",
        "> 這是唯一入口。不要再到 INBOX、planning 或舊的待發布資料夾找成片。",
        "",
        f"- **準備發布：{len(ready_rows)} 支** → [READY 索引](READY/INDEX.md)",
        f"- **已發布：{len(published_rows)} 支** → [PUBLISHED 索引](PUBLISHED/INDEX.md)",
        f"- **待查證文案：{len(research_queue)} 支** → [_STATE/publish_research_queue.json](_STATE/publish_research_queue.json)",
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
    payload["start_here"] = _relative(START_HERE)
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


def selftest() -> None:
    assert _slug('a:b/c*', fallback="x") == "a_b_c"
    assert READY.parent == HUB and PUBLISHED.parent == HUB
    assert HUB.name == "_PUBLISH_HUB"
    print("publish_hub self-test GREEN")


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hao unified publishing hub")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("sync")
    subs.add_parser("audit")
    migration = subs.add_parser("migrate-layout")
    migration.add_argument("--apply", action="store_true")
    subs.add_parser("remix-plan")
    retire = subs.add_parser("retire-legacy-ready")
    retire.add_argument("--apply", action="store_true")
    dedupe = subs.add_parser("dedupe-verified")
    dedupe.add_argument("--apply", action="store_true")
    versioned = subs.add_parser("retire-versioned-renders")
    versioned.add_argument("--apply", action="store_true")
    subs.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "selftest":
        selftest()
        return 0
    if args.command == "sync":
        hub_migration = migrate_legacy_layout(apply=True)
        layout = migrate_status_layout()
        payload = {"hub_migration": hub_migration, "layout_migrations": layout,
                   "ready_shorts": migrate_ready_shorts(),
                   "published_shorts": import_published_shorts(),
                   "longform": import_longform(),
                   "legacy_miaoli_remix": create_miaoli_remix_plan(),
                   "remix": create_remix_plans()}
        payload["registry"] = rebuild_index()
    elif args.command == "audit":
        payload = audit()
    elif args.command == "migrate-layout":
        payload = migrate_legacy_layout(apply=args.apply)
    elif args.command == "remix-plan":
        payload = create_remix_plans()
    elif args.command == "retire-legacy-ready":
        payload = retire_legacy_ready(apply=args.apply)
    elif args.command == "dedupe-verified":
        payload = consolidate_verified_duplicates(apply=args.apply)
    else:
        payload = retire_versioned_job_outputs(apply=args.apply)
    _print(payload)
    return 0 if payload.get("status", "GREEN") != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
