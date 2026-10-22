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
from publish_contract import (completion_failures, desired_short_status, reviewed_artifact_ready,
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
                             create_demo_remix_plan, retire_legacy_ready)
from remix_planner import create_plans as create_remix_plans
from autonomy_standard import (initialize_control_state,
                               queue_summary as autonomy_queue_summary,
                               resolve_review)


from publish_hub_context import (
    HERE,
    ROOT,
    VIDEOS,
    SHORTS_ROOT,
    LONGFORM_ROOT,
    LEGACY_READY,
    STATE_PATH,
    INVALID,
    WITHDRAWN_PATH,
    _now,
    _atomic_text,
    _atomic_json,
    _root_entry_text,
    _withdrawn_state,
    _withdrawn_ids,
    _sha256,
    _slug,
    _relative,
    _safe_eval,
    load_plan,
    _short_key,
    _short_plan,
    find_short_source,
    _short_identity,
    _hardlink,
    _content_manifests,
    _state_entries,
    _has_current_visual_review,
    _longform_candidates,
    _longform_state,
    _package_rows,
)
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
from publish_hub_registry import (
    ROOT_ENTRY,
    migrate_status_layout,
    refresh_package_identities,
    reconcile_duplicate_packages,
    rebuild_index,
    audit,
    withdraw_content,
    mark_published,
)


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
    if status == "ready" and not _has_current_visual_review(source):
        status = "review"
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
    ``review`` bucket until Hao approves the aesthetic review, and reuse the
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
                    if quality_status == "CERTIFIED_95":
                        status = "ready"
                except (OSError, ValueError):
                    pass
        results.append(promote_short(short_id, status=status))
    return results


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
