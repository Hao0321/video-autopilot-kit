# -*- coding: utf-8 -*-
"""Storage retirement, exact dedupe and remix planning for publish_hub."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_paths import discover_project_root, is_within
from publish_hub_layout import PUBLISHED, READY
from publishing_copy import build_publish_copy, render_copy_markdown
import storage_lifecycle


ROOT = discover_project_root(Path(__file__).resolve().parent)
VIDEOS = ROOT / "videos"
LEGACY_READY = VIDEOS / "_待發布Shorts"
REPORTS = ROOT / "reports" / "storage"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".publish-ops-", suffix=".tmp", dir=path.parent)
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


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _package_rows() -> list[dict[str, Any]]:
    rows = []
    for base in (READY, PUBLISHED):
        for manifest in base.rglob("publish.json") if base.exists() else []:
            row = json.loads(manifest.read_text(encoding="utf-8-sig"))
            row["package"] = _relative(manifest.parent)
            rows.append(row)
    return rows


def retire_legacy_ready(*, apply: bool) -> dict[str, Any]:
    actions, errors = [], []
    registry = {row["content_id"]: row for row in _package_rows()}
    for source in sorted(LEGACY_READY.glob("*.mp4")):
        match = re.match(r"s(\d+)_", source.name, re.I)
        content_id = f"S{int(match.group(1)):03d}" if match else None
        row = registry.get(content_id) if content_id else None
        target = ROOT / row["package"] / row["video"] if row else None
        if not target or not target.is_file() or _sha256(source) != _sha256(target):
            errors.append({"path": str(source), "error": "no verified hub twin"})
            continue
        actions.append({"path": _relative(source), "verified_twin": _relative(target),
                        "sha256": row["sha256"], "action": "delete" if apply else "would-delete"})
        if apply:
            source.unlink()
    if apply and LEGACY_READY.exists() and not any(LEGACY_READY.iterdir()):
        LEGACY_READY.rmdir()
    report = {"status": "GREEN" if not errors else "RED", "applied": apply,
              "actions": actions, "errors": errors, "generated_at": _now()}
    _atomic_json(REPORTS / "legacy-ready-retirement.json", report)
    return report


def _keeper_rank(path: Path) -> tuple[int, int, str]:
    text = path.as_posix().lower()
    if "/_inbox/" in text:
        rank = 0
    elif "/_archive/" in text and not path.name.lower().startswith("v2_"):
        rank = 1
    elif "/_planning/" in text:
        rank = 2
    elif "/_publish_hub/ready/" in text or "/_publish_hub/published/" in text:
        rank = 3
    else:
        rank = 4
    return rank, len(path.parts), str(path)


def _replace_with_hardlink(keeper: Path, target: Path) -> None:
    if keeper.stat().st_dev != target.stat().st_dev:
        raise RuntimeError("cross-volume duplicate cannot become a hard link")
    temporary = target.with_name(f".{target.name}.dedupe.tmp")
    if temporary.exists():
        temporary.unlink()
    os.link(keeper, temporary)
    os.replace(temporary, target)
    if _sha256(target) != _sha256(keeper) or target.stat().st_ino != keeper.stat().st_ino:
        raise RuntimeError(f"post-dedupe verification failed: {target}")


def consolidate_verified_duplicates(*, apply: bool) -> dict[str, Any]:
    audit_data = storage_lifecycle.audit_tree(VIDEOS, hash_duplicates=True)
    actions, errors, reclaimable = [], [], 0
    for group in audit_data["duplicate_groups"]:
        paths = [Path(value).resolve() for value in group["paths"]]
        keeper = min(paths, key=_keeper_rank)
        for target in paths:
            if target == keeper or target.stat().st_ino == keeper.stat().st_ino:
                continue
            if not is_within(target, VIDEOS) or target.name.upper().startswith("IMG_"):
                errors.append({"path": str(target), "error": "protected or outside videos"})
                continue
            action = {"keeper": _relative(keeper), "target": _relative(target),
                      "sha256": group["sha256"], "bytes": group["bytes_each"],
                      "action": "hardlink-replaced" if apply else "would-hardlink-replace"}
            try:
                if apply:
                    _replace_with_hardlink(keeper, target)
            except (OSError, RuntimeError) as exc:
                errors.append({**action, "error": str(exc)})
            else:
                actions.append(action)
                reclaimable += int(group["bytes_each"])
    report = {"status": "GREEN" if not errors else "RED", "applied": apply,
              "physical_bytes_reclaimed": reclaimable if apply else 0,
              "potential_bytes": reclaimable, "actions": actions, "errors": errors,
              "generated_at": _now()}
    _atomic_json(REPORTS / "verified-dedupe.json", report)
    return report


def create_miaoli_remix_plan() -> dict[str, Any]:
    """Compatibility entrypoint that writes a synthetic public demo route."""
    output = VIDEOS / "_planning" / "remix" / "R001_public-demo-day-trip"
    plan = {
        "schema_version": 1, "content_id": "R001", "status": "planned",
        "format": "shorts", "target_seconds": 52,
        "title": "示範一日遊 4 站｜從晨間市集走到河畔公園",
        "source_rule": "使用 S101-S104 的示範原始素材，不串接已上字幕成片",
        "sources": [
            {"content_id": "S101", "stop": "晨光市場", "folder": "videos/_INBOX/demo/101", "range": "00:03-00:12"},
            {"content_id": "S102", "stop": "綠徑公園", "folder": "videos/_INBOX/demo/102", "range": "00:12-00:23"},
            {"content_id": "S103", "stop": "工藝車站", "folder": "videos/_INBOX/demo/103", "range": "00:23-00:35"},
            {"content_id": "S104", "stop": "河畔步道", "folder": "videos/_INBOX/demo/104", "range": "00:35-00:47"},
        ],
        "beats": [
            {"range": "00:00-00:03", "purpose": "四站 payoff 快閃", "caption": "示範一日遊・4 站"},
            {"range": "00:03-00:47", "purpose": "依示範順序走完四站", "caption": "每站只留地名與一個體驗重點"},
            {"range": "00:47-00:52", "purpose": "路線回顧與回圈", "caption": "這條示範路線你會先去哪站？"},
        ],
        "research_topic": "demo_day_trip", "candidate_score": 80,
        "score_basis": ["synthetic fixture", "four distinct demo stops", "original-source rule exercised"],
        "fixture_origin": "PUBLIC_FIXTURE: demo_day_trip",
        "updated_at": _now(),
    }
    _atomic_json(output / "remix_plan.json", plan)
    copy = build_publish_copy(
        {"niche": "travel", "place": "示範城", "what": "示範一日遊 四站"},
        {"yt_title": plan["title"],
         "text": "從晨光市場出發，依序走綠徑公園、工藝車站，最後到河畔步道。這是公開版的合成示範資料。\n#示範一日遊 #旅行Shorts"},
    )
    _atomic_text(output / "發布文案_可複製.md", render_copy_markdown(copy))
    return plan
