# -*- coding: utf-8 -*-
"""Usage-memory and path-migration helpers for the virtual asset registry.

Separated from selection/ranking so the registry remains a read-mostly index.
All writes are bounded, additive or atomic; media is never copied or deleted.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from project_paths import discover_project_root


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _root(value: str | os.PathLike | None = None) -> Path:
    return Path(value).expanduser().resolve() if value else discover_project_root()


def load_usage_snapshot(project_root: str | os.PathLike | None = None,
                        recent_content_window: int = 20) -> dict[str, dict]:
    """Return bounded usage statistics used by selection and fatigue QA.

    Lifetime counts are useful for inventory, but they must not permanently
    punish a good asset. Selection therefore uses unique recent content IDs
    plus a consecutive-use streak; compacted lifetime history stays separate.
    """
    root = _root(project_root)
    usage_dir = root / "assets" / "_usage"
    summary = _read_json(usage_dir / "asset_usage_summary.json", {}).get("assets", {})
    result = {key: {**value, "lifetime_count": int(value.get("count", 0))}
              for key, value in summary.items() if isinstance(value, dict)}
    history = usage_dir / "asset_usage.jsonl"
    events: list[dict] = []
    if history.is_file():
        for line in history.read_text(encoding="utf-8", errors="replace").splitlines()[-2400:]:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("asset_id") and event.get("content_id"):
                events.append(event)

    recent_ids: list[str] = []
    for event in reversed(events):
        content_id = str(event["content_id"])
        if content_id not in recent_ids:
            recent_ids.append(content_id)
        if len(recent_ids) >= max(1, int(recent_content_window)):
            break
    recent_set = set(recent_ids)
    for event in events:
        asset_id = str(event["asset_id"])
        row = result.setdefault(asset_id, {"lifetime_count": 0})
        row["lifetime_count"] = int(row.get("lifetime_count", 0)) + 1
        row["last_used"] = event.get("at", row.get("last_used"))
        if str(event["content_id"]) in recent_set:
            used = row.setdefault("recent_content_ids", [])
            if event["content_id"] not in used:
                used.append(event["content_id"])

    for row in result.values():
        used = set(row.get("recent_content_ids", []))
        row["recent_content_count"] = len(used)
        streak = 0
        for content_id in recent_ids:
            if content_id in used:
                streak += 1
            else:
                break
        row["consecutive_content_streak"] = streak
        density = len(used) / max(1, len(recent_ids))
        row["fatigue_score"] = round(min(1.0, density * 1.35 + max(0, streak - 1) * .16), 3)
        row["fatigue_level"] = "high" if row["fatigue_score"] >= .72 else \
            "medium" if row["fatigue_score"] >= .42 else "low"
    return result


def asset_fatigue_report(asset_ids: Iterable[str],
                         project_root: str | os.PathLike | None = None) -> dict:
    snapshot = load_usage_snapshot(project_root)
    rows = []
    for asset_id in dict.fromkeys(str(value) for value in asset_ids if value):
        stats = snapshot.get(asset_id, {})
        rows.append({"asset_id": asset_id,
                     "recent_content_count": int(stats.get("recent_content_count", 0)),
                     "consecutive_content_streak": int(stats.get("consecutive_content_streak", 0)),
                     "fatigue_score": float(stats.get("fatigue_score", 0)),
                     "fatigue_level": stats.get("fatigue_level", "low")})
    peak = max((row["fatigue_score"] for row in rows), default=0.0)
    return {"status": "REVIEW" if peak >= .72 else "GREEN",
            "peak": round(peak, 3), "assets": rows}


def _compact_usage(history: Path, keep_recent: int = 1200, trigger: int = 2400) -> None:
    """Fold old JSONL events into a summary while retaining recent evidence."""
    lines = history.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) <= trigger:
        return
    old, recent = lines[:-keep_recent], lines[-keep_recent:]
    summary_path = history.with_name("asset_usage_summary.json")
    summary = _read_json(summary_path, {"schema_version": 1, "assets": {}})
    assets = summary.setdefault("assets", {})
    for line in old:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        asset_id = event.get("asset_id")
        if not asset_id:
            continue
        row = assets.setdefault(asset_id, {"count": 0})
        row["count"] = int(row.get("count", 0)) + 1
        row["last_used"] = event.get("at", row.get("last_used"))
    summary["compacted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".asset-usage-", suffix=".tmp", dir=summary_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.replace(temp_name, summary_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    history.write_text("\n".join(recent) + "\n", encoding="utf-8")


def _append_usage(rows: list[dict], content_id: str, feedback: str, root: Path) -> int:
    if not rows:
        return 0
    usage_dir = root / "assets" / "_usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    history = usage_dir / "asset_usage.jsonl"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with history.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({
                "at": stamp,
                "content_id": content_id,
                "asset_id": row["asset_id"],
                "path": row.get("path"),
                "feedback": str(feedback or "")[:160],
            }, ensure_ascii=False) + "\n")
    _compact_usage(history)
    return len(rows)


def record_plan_usage(plan_path: str | os.PathLike, content_id: str, feedback: str = "") -> int:
    """Commit actually-used selections; planning alone never pollutes memory."""
    plan = _read_json(Path(plan_path).resolve(), {})
    selected = []
    music = (plan.get("music") or {}).get("selected") or {}
    if music.get("asset_id"):
        selected.append(music)
    for cue in plan.get("cues", []):
        item = cue.get("selected") or {}
        if item.get("asset_id"):
            selected.append(item)
        selected.extend(row for row in cue.get("sfx_candidates", [])[:1] if row.get("asset_id"))
    return _append_usage(selected, content_id, feedback, _root())


def record_asset_paths(
    paths: Iterable[str | os.PathLike],
    content_id: str,
    feedback: str = "",
    project_root: str | os.PathLike | None = None,
) -> int:
    """Record renderer-consumed paths, ignoring anything outside the registry."""
    from asset_registry import AssetRegistry  # lazy import avoids a module cycle

    registry = AssetRegistry(project_root)
    by_path = {row["path"]: row for row in registry.records}
    selected = []
    for value in paths:
        row = by_path.get(registry._canonical_path(value))
        if row and all(item["asset_id"] != row["asset_id"] for item in selected):
            selected.append(row)
    return _append_usage(selected, content_id, feedback, registry.root)


def migrate_index_paths(write: bool = False, project_root: str | os.PathLike | None = None) -> dict:
    """Convert legacy absolute metadata to portable paths without moving assets."""
    root = _root(project_root)
    index_path = root / "assets" / "index.json"
    data = _read_json(index_path, {})
    converted, external = 0, []

    def portable(child):
        nonlocal converted
        if not isinstance(child, str) or not Path(child).is_absolute():
            return child
        try:
            converted += 1
            return Path(child).resolve().relative_to(root).as_posix()
        except ValueError:
            external.append(child)
            return child

    def walk(value):
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if isinstance(child, str):
                    value[key] = portable(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, str):
                    value[index] = portable(child)
                else:
                    walk(child)

    walk(data)
    meta = data.setdefault("_meta", {})
    meta["schema_version"] = "0.4"
    meta["path_policy"] = "project_relative; resolve at runtime via asset_registry"
    meta["description"] = "Portable asset metadata; selection remains asset_registry's responsibility."
    counts = meta.setdefault("counts", {})
    for label, key in (("broll", "broll_actual"), ("sfx", "sfx_actual"),
                       ("font_families", "fonts_actual"), ("face", "face")):
        counts[label] = sum(not str(name).startswith("_") for name in data.get(key, {}))
    counts["face"] = int(data.get("face", {}).get("count", counts.get("face", 0)))
    counts["bgm_indexed"] = sum(
        len(_read_json(path, {}).get("tracks", []))
        for path in (root / "assets" / "bgm").rglob("bgm_index.json")
    )
    meta["asset_count"] = sum(int(value) for value in counts.values())
    meta["asset_count_scope"] = "central indexes + BGM pointers; public kit is virtual"
    if write:
        meta["portable_path_migration_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=".asset-index-", suffix=".tmp", dir=index_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.replace(temp_name, index_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    return {
        "converted": converted,
        "external_paths": external,
        "written": bool(write),
        "index": str(index_path),
    }
