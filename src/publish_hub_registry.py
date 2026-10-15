"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations
from pathlib import Path

import json
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any
from project_paths import is_within
from publish_contract import completion_failures, longform_completion_failures
from publish_hub_layout import HUB, HUB_AUDIT, LEGACY_PUBLISHED, LEGACY_READY as LEGACY_PACKAGE_READY, PUBLISHED, READY, REGISTRY, RESEARCH_QUEUE, START_HERE, cleanup_legacy_generated_state, audit_version_like_media, iter_manifests, validate_package
from autonomy_standard import initialize_control_state, queue_summary as autonomy_queue_summary, resolve_review
from publish_hub_context import ROOT, SHORTS_ROOT, LONGFORM_ROOT, WITHDRAWN_PATH, _now, _atomic_text, _atomic_json, _root_entry_text, _withdrawn_state, _withdrawn_ids, _sha256, _relative, _content_manifests, _package_rows


ROOT_ENTRY = ROOT / "00_發布中樞_從這裡開始.md"


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
