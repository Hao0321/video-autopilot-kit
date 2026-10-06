# -*- coding: utf-8 -*-
"""Bounded asset-usage persistence without registry or catalog dependencies."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from project_paths import discover_project_root


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_text_atomic(path: Path, text: str) -> None:
    """Unique temp file in the target directory, fsync, then os.replace."""
    data = text.encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, str(path))
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _lines_digest(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _compacted_prefix(summary: dict, lines: list[str]) -> int:
    """Leading history lines that the summary already counted (a compaction interrupted
    after its summary write but before its history rewrite leaves them in place)."""
    marker = summary.get("compaction") if isinstance(summary, dict) else None
    count = marker.get("lines") if isinstance(marker, dict) else None
    if type(count) is not int or not 0 < count <= len(lines):
        return 0
    return count if _lines_digest(lines[:count]) == marker.get("sha256") else 0


def project_root(value: str | os.PathLike | None = None) -> Path:
    return Path(value).expanduser().resolve() if value else discover_project_root()


def load_usage_snapshot(
    root_value: str | os.PathLike | None = None,
    recent_content_window: int = 20,
) -> dict[str, dict]:
    root = project_root(root_value)
    usage_dir = root / "assets" / "_usage"
    document = read_json(usage_dir / "asset_usage_summary.json", {})
    summary = document.get("assets", {}) if isinstance(document, dict) else {}
    result = {
        key: {**value, "lifetime_count": int(value.get("count", 0))}
        for key, value in summary.items() if isinstance(value, dict)
    }
    events: list[dict] = []
    history = usage_dir / "asset_usage.jsonl"
    if history.is_file():
        lines = history.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[_compacted_prefix(document, lines):][-2400:]:
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
            if content_id not in used:
                break
            streak += 1
        row["consecutive_content_streak"] = streak
        density = len(used) / max(1, len(recent_ids))
        row["fatigue_score"] = round(min(1.0, density * 1.35 + max(0, streak - 1) * .16), 3)
        row["fatigue_level"] = "high" if row["fatigue_score"] >= .72 else "medium" if row["fatigue_score"] >= .42 else "low"
    return result


def asset_fatigue_report(
    asset_ids: Iterable[str],
    root_value: str | os.PathLike | None = None,
) -> dict:
    snapshot = load_usage_snapshot(root_value)
    rows = []
    for asset_id in dict.fromkeys(str(value) for value in asset_ids if value):
        stats = snapshot.get(asset_id, {})
        rows.append({
            "asset_id": asset_id,
            "recent_content_count": int(stats.get("recent_content_count", 0)),
            "consecutive_content_streak": int(stats.get("consecutive_content_streak", 0)),
            "fatigue_score": float(stats.get("fatigue_score", 0)),
            "fatigue_level": stats.get("fatigue_level", "low"),
        })
    peak = max((row["fatigue_score"] for row in rows), default=0.0)
    return {"status": "REVIEW" if peak >= .72 else "GREEN", "peak": round(peak, 3), "assets": rows}


def _compact_usage(history: Path, keep_recent: int = 1200, trigger: int = 2400) -> None:
    """Fold old history lines into the summary; safe to retry after a crash.

    The summary records how many leading history lines it has counted (plus
    their digest) before the history is atomically rewritten, so a run that
    dies between the two writes is finished by the next run, never re-counted.
    """
    lines = history.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) <= trigger:
        return
    summary_path = history.with_name("asset_usage_summary.json")
    summary = (read_json(summary_path, None) if summary_path.exists()
               else {"schema_version": 1, "assets": {}})
    if not isinstance(summary, dict) or not isinstance(summary.setdefault("assets", {}), dict):
        return  # never rebuild lifetime counts over an unreadable summary
    done = _compacted_prefix(summary, lines)
    cut = max(done, len(lines) - keep_recent)
    assets = summary["assets"]
    for line in lines[done:cut]:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        asset_id = event.get("asset_id") if isinstance(event, dict) else None
        if not asset_id:
            continue
        row = assets.setdefault(asset_id, {"count": 0})
        row["count"] = int(row.get("count", 0)) + 1
        row["last_used"] = event.get("at", row.get("last_used"))
    summary["compacted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["compaction"] = {"lines": cut, "sha256": _lines_digest(lines[:cut])}
    write_text_atomic(summary_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    write_text_atomic(history, "\n".join(lines[cut:]) + "\n")


def record_asset_rows(
    rows: Iterable[dict],
    content_id: str,
    feedback: str = "",
    root_value: str | os.PathLike | None = None,
) -> int:
    selected = [row for row in rows if row.get("asset_id")]
    if not selected:
        return 0
    root = project_root(root_value)
    usage_dir = root / "assets" / "_usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    history = usage_dir / "asset_usage.jsonl"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with history.open("a", encoding="utf-8", newline="\n") as handle:
        for row in selected:
            handle.write(json.dumps({
                "at": stamp, "content_id": content_id, "asset_id": row["asset_id"],
                "path": row.get("path"), "feedback": str(feedback or "")[:160],
            }, ensure_ascii=False) + "\n")
    _compact_usage(history)
    return len(selected)


def record_plan_usage(plan_path: str | os.PathLike, content_id: str, feedback: str = "") -> int:
    plan = read_json(Path(plan_path).resolve(), {})
    selected = []
    music = (plan.get("music") or {}).get("selected") or {}
    if music.get("asset_id"):
        selected.append(music)
    for cue in plan.get("cues", []):
        item = cue.get("selected") or {}
        if item.get("asset_id"):
            selected.append(item)
        selected.extend(row for row in cue.get("sfx_candidates", [])[:1] if row.get("asset_id"))
    return record_asset_rows(selected, content_id, feedback)


def _selftest() -> None:
    """Interrupted compaction is finished by the next run and never double counts."""
    rows = [{"asset_id": "bgm:fixture", "path": "assets/bgm/fixture.mp3"}]
    real_writer = globals()["write_text_atomic"]

    def crash_before_history_rewrite(path: Path, text: str) -> None:
        if path.name == "asset_usage.jsonl":
            raise RuntimeError("simulated crash")
        real_writer(path, text)

    with tempfile.TemporaryDirectory(prefix="asset-usage-test-") as td:
        root = Path(td)
        history = root / "assets" / "_usage" / "asset_usage.jsonl"
        for index in range(12):
            record_asset_rows(rows, "c%02d" % index, root_value=root)
        globals()["write_text_atomic"] = crash_before_history_rewrite
        try:
            _compact_usage(history, keep_recent=4, trigger=8)
            raise AssertionError("simulated crash did not happen")
        except RuntimeError:
            pass
        finally:
            globals()["write_text_atomic"] = real_writer

        def lifetime() -> int:
            return load_usage_snapshot(root)["bgm:fixture"]["lifetime_count"]

        assert lifetime() == 12, "an interrupted compaction must not double count"
        record_asset_rows(rows, "c12", root_value=root)
        _compact_usage(history, keep_recent=4, trigger=8)
        assert lifetime() == 13 and len(history.read_text(encoding="utf-8").splitlines()) == 4
        _compact_usage(history, keep_recent=2, trigger=3)
        assert lifetime() == 13, "repeated compaction keeps the lifetime total"
        history.with_name("asset_usage_summary.json").write_text("{broken", encoding="utf-8")
        before = history.read_bytes()
        _compact_usage(history, keep_recent=1, trigger=1)
        assert history.read_bytes() == before, "an unreadable summary is never rebuilt over"
        assert sorted(p.name for p in history.parent.iterdir()) == [
            "asset_usage.jsonl", "asset_usage_summary.json"], "no temp files left behind"
    print("asset_usage self-test GREEN")


if __name__ == "__main__":
    _selftest()
