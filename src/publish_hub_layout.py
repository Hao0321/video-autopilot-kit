# -*- coding: utf-8 -*-
"""Single-source publishing layout, migration and package validation.

The publishing hub is an operational surface, not another render cache.  A
package therefore owns exactly one delivery video.  Superseded artifacts are
retired outside the hub with a SHA-256 audit trail; raw sources are untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from project_paths import discover_project_root, is_within


ROOT = discover_project_root(Path(__file__).resolve().parent)
VIDEOS = ROOT / "videos"
HUB = VIDEOS / "_PUBLISH_HUB"
READY = HUB / "READY"
PUBLISHED = HUB / "PUBLISHED"
HUB_STATE = HUB / "_STATE"
HUB_AUDIT = HUB / "_AUDIT"
REGISTRY = HUB_STATE / "publish_registry.json"
RESEARCH_QUEUE = HUB_STATE / "publish_research_queue.json"
START_HERE = HUB / "START_HERE.md"

LEGACY_READY = VIDEOS / "_READY_TO_PUBLISH"
LEGACY_PUBLISHED = VIDEOS / "_PUBLISHED"
LEGACY_REGISTRY = VIDEOS / "_registry" / "publish_hub.json"
LEGACY_RESEARCH_QUEUE = VIDEOS / "_state" / "publish_research_queue.json"
RETIRED = VIDEOS / "_archive" / "publish-hub-retired"
VERSIONED_RETIRED = VIDEOS / "_archive" / "versioned-render-retirement"

MEDIA_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
VERSION_LIKE = re.compile(
    r"(?:^|[-_ .])(?:v\d+|ver\d+|final|old|backup|bak|draft|preview|初剪)(?:[-_ .]|$)",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".publish-layout-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def package_media(package: Path) -> list[Path]:
    return sorted(
        path for path in package.iterdir()
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
    ) if package.is_dir() else []


def iter_manifests(*, include_legacy: bool = False) -> Iterable[Path]:
    roots = [READY, PUBLISHED]
    if include_legacy:
        roots.extend((LEGACY_READY, LEGACY_PUBLISHED))
    for base in roots:
        if base.exists():
            yield from sorted(base.rglob("publish.json"))


def validate_package(manifest: Path) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    try:
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return [{"path": relative(manifest), "error": f"invalid publish.json: {exc}"}]
    content_id = str(row.get("content_id") or "UNKNOWN")
    if int(row.get("schema_version") or 0) < 2:
        failures.append({"id": content_id, "error": "publish schema must be version 2 or newer"})
    if int(row.get("artifact_revision") or 0) < 1:
        failures.append({"id": content_id, "error": "artifact_revision must be a positive integer"})
    media = package_media(manifest.parent)
    if len(media) != 1:
        failures.append({
            "id": content_id,
            "path": relative(manifest.parent),
            "error": "package must contain exactly one delivery video",
            "media_count": len(media),
            "media": [path.name for path in media],
        })
    declared = manifest.parent / str(row.get("video") or "")
    if not declared.is_file():
        failures.append({"id": content_id, "error": "declared video is missing"})
        return failures
    if len(media) == 1 and media[0].resolve() != declared.resolve():
        failures.append({"id": content_id, "error": "declared video is not the sole package video"})
    if VERSION_LIKE.search(declared.stem):
        failures.append({"id": content_id, "error": "version-like delivery filename is forbidden",
                         "video": declared.name})
    actual_hash = sha256(declared)
    if str(row.get("sha256") or "").lower() != actual_hash:
        failures.append({"id": content_id, "error": "sha256 mismatch"})
    if row.get("bytes") is not None and int(row["bytes"]) != declared.stat().st_size:
        failures.append({"id": content_id, "error": "byte size mismatch"})
    for required in ("發布文案_可複製.md", "publish.json"):
        if not (manifest.parent / required).is_file():
            failures.append({"id": content_id, "error": f"missing {required}"})
    return failures


def audit_version_like_media() -> dict[str, Any]:
    """Inventory downgrade-prone media names without deleting user sources."""
    rows: list[dict[str, Any]] = []
    for path in sorted(VIDEOS.rglob("*")) if VIDEOS.exists() else []:
        if not path.is_file() or path.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        if not VERSION_LIKE.search(path.stem):
            continue
        if is_within(path, HUB):
            classification = "publish-blocker"
        elif is_within(path, RETIRED) or "_archive" in path.parts:
            classification = "audited-archive"
        elif "_INBOX" in path.parts:
            classification = "protected-working-or-source"
        else:
            classification = "legacy-review"
        rows.append({
            "path": relative(path),
            "bytes": path.stat().st_size,
            "classification": classification,
            "action": "block-from-publishing" if classification == "publish-blocker" else "retain-and-review",
        })
    payload = {
        "status": "RED" if any(row["classification"] == "publish-blocker" for row in rows) else "GREEN",
        "count": len(rows),
        "publish_blockers": sum(row["classification"] == "publish-blocker" for row in rows),
        "items": rows,
        "generated_at": now(),
    }
    atomic_json(HUB_AUDIT / "version-like-media-latest.json", payload)
    return payload


def retire_versioned_job_outputs(*, apply: bool = False) -> dict[str, Any]:
    """Retire named render iterations only when ``current.mp4`` exists."""
    inbox = VIDEOS / "_INBOX"
    candidates: list[Path] = []
    if inbox.exists():
        for path in sorted(inbox.rglob("*")):
            if (path.is_file() and path.parent.name == "_out"
                    and path.suffix.lower() in MEDIA_SUFFIXES
                    and VERSION_LIKE.search(path.stem)
                    and (path.parent / "current.mp4").is_file()):
                candidates.append(path)
    run = timestamp()
    actions: list[dict[str, Any]] = []
    for source in candidates:
        if not is_within(source, inbox):
            raise RuntimeError(f"version retirement source escaped INBOX: {source}")
        target = VERSIONED_RETIRED / run / source.relative_to(VIDEOS)
        digest = sha256(source)
        row = {
            "from": relative(source), "to": relative(target),
            "sha256": digest, "bytes": source.stat().st_size,
            "reason": "version-like generated render has current.mp4 sibling",
            "action": "moved-to-audited-archive" if apply else "would-move-to-audited-archive",
        }
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if sha256(target) != digest:
                    raise RuntimeError(f"version retirement collision: {target}")
                source.unlink()
                row["action"] = "verified-source-link-retired"
            else:
                shutil.move(str(source), str(target))
            if sha256(target) != digest:
                raise RuntimeError(f"version retirement hash mismatch: {target}")
        actions.append(row)
    payload = {
        "status": "GREEN", "mode": "apply" if apply else "preview",
        "candidate_count": len(candidates), "actions": actions,
        "generated_at": now(),
    }
    if apply:
        atomic_json(HUB_AUDIT / f"versioned-render-retirement-{run}.json", payload)
    return payload


def _target_for_legacy(manifest: Path) -> Path:
    if is_within(manifest, LEGACY_READY):
        return READY / manifest.parent.relative_to(LEGACY_READY)
    if is_within(manifest, LEGACY_PUBLISHED):
        return PUBLISHED / manifest.parent.relative_to(LEGACY_PUBLISHED)
    raise ValueError(f"manifest is outside a legacy publishing root: {manifest}")


def migration_plan() -> dict[str, Any]:
    packages: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for manifest in iter_manifests(include_legacy=True):
        if is_within(manifest, HUB):
            continue
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        declared = manifest.parent / str(row.get("video") or "")
        if not declared.is_file():
            errors.append({"path": relative(manifest.parent), "error": "declared video missing"})
            continue
        actual = sha256(declared)
        if actual != str(row.get("sha256") or "").lower():
            errors.append({"path": relative(manifest.parent), "error": "declared SHA mismatch"})
            continue
        target = _target_for_legacy(manifest)
        extras = []
        for media in package_media(manifest.parent):
            if media.resolve() == declared.resolve():
                continue
            extras.append({"name": media.name, "sha256": sha256(media), "bytes": media.stat().st_size})
        packages.append({
            "content_id": row.get("content_id"),
            "source": relative(manifest.parent),
            "target": relative(target),
            "video": declared.name,
            "sha256": actual,
            "extra_media": extras,
        })
    return {
        "status": "GREEN" if not errors else "RED",
        "mode": "preview",
        "hub": relative(HUB),
        "packages": packages,
        "package_count": len(packages),
        "extra_media_count": sum(len(row["extra_media"]) for row in packages),
        "errors": errors,
    }


def _retire_extra(path: Path, *, content_id: str, run: str) -> dict[str, Any]:
    if not is_within(path, HUB):
        raise RuntimeError(f"retirement source outside hub: {path}")
    digest = sha256(path)
    target = RETIRED / run / content_id / path.name
    if not is_within(target, RETIRED):
        raise RuntimeError(f"retirement target outside archive: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) != digest:
            raise RuntimeError(f"retirement collision: {target}")
        path.unlink()
        action = "verified-source-link-retired"
    else:
        shutil.move(str(path), str(target))
        if sha256(target) != digest:
            raise RuntimeError(f"retirement hash mismatch: {target}")
        action = "moved-to-audited-archive"
    return {"from": relative(path), "to": relative(target), "sha256": digest,
            "bytes": target.stat().st_size, "action": action}


def _remove_empty_legacy_root(base: Path) -> list[str]:
    removed: list[str] = []
    if not base.exists():
        return removed
    for generated in (base / "INDEX.md",):
        if generated.is_file():
            generated.unlink()
            removed.append(relative(generated))
    for directory in sorted((p for p in base.rglob("*") if p.is_dir()),
                            key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        base.rmdir()
        removed.append(relative(base))
    except OSError:
        pass
    return removed


def migrate_legacy_layout(*, apply: bool = False) -> dict[str, Any]:
    plan = migration_plan()
    if not apply or plan["status"] == "RED":
        return plan
    run = timestamp()
    HUB.mkdir(parents=True, exist_ok=True)
    moves: list[dict[str, Any]] = []
    retired: list[dict[str, Any]] = []
    for item in plan["packages"]:
        source = ROOT / item["source"]
        target = ROOT / item["target"]
        if not (is_within(source, LEGACY_READY) or is_within(source, LEGACY_PUBLISHED)):
            raise RuntimeError(f"legacy source escaped boundary: {source}")
        if not is_within(target, HUB):
            raise RuntimeError(f"hub target escaped boundary: {target}")
        if target.exists():
            raise RuntimeError(f"hub migration target exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        manifest = target / "publish.json"
        row = json.loads(manifest.read_text(encoding="utf-8-sig"))
        for media in package_media(target):
            if media.name != row.get("video"):
                retired.append(_retire_extra(media, content_id=str(row["content_id"]), run=run))
        row["schema_version"] = max(2, int(row.get("schema_version") or 1))
        row["artifact_revision"] = int(row.get("artifact_revision") or 1)
        row["hub_path"] = relative(target)
        row["migration"] = {"from": item["source"], "at": now()}
        atomic_json(manifest, row)
        failures = validate_package(manifest)
        if failures:
            raise RuntimeError(f"migrated package validation failed: {failures}")
        moves.append({"content_id": row["content_id"], "from": item["source"],
                      "to": item["target"]})
    removed = []
    removed.extend(_remove_empty_legacy_root(LEGACY_READY))
    removed.extend(_remove_empty_legacy_root(LEGACY_PUBLISHED))
    report = {
        "status": "GREEN",
        "mode": "applied",
        "hub": relative(HUB),
        "moved_packages": moves,
        "retired_noncanonical_media": retired,
        "removed_empty_legacy_roots": removed,
        "generated_at": now(),
    }
    atomic_json(HUB_AUDIT / f"layout-migration-{run}.json", report)
    return report


def retire_superseded_package_media(package: Path, *, keep_name: str,
                                    keep_sha256: str) -> list[dict[str, Any]]:
    """Enforce one-video packages before a newly rendered artifact is linked."""
    actions: list[dict[str, Any]] = []
    run = timestamp()
    content_id = package.name.split("_", 1)[0]
    for media in package_media(package):
        digest = sha256(media)
        if media.name == keep_name and digest == keep_sha256:
            continue
        if digest == keep_sha256:
            size = media.stat().st_size
            media.unlink()
            actions.append({"from": relative(media), "sha256": digest,
                            "bytes": size,
                            "action": "exact-link-retired"})
        else:
            actions.append(_retire_extra(media, content_id=content_id, run=run))
    if actions:
        atomic_json(HUB_AUDIT / f"package-retirement-{run}-{content_id}.json", {
            "status": "GREEN", "content_id": content_id, "actions": actions,
            "generated_at": now(),
        })
    return actions


def cleanup_legacy_generated_state() -> list[str]:
    removed = []
    for old, current in ((LEGACY_REGISTRY, REGISTRY),
                         (LEGACY_RESEARCH_QUEUE, RESEARCH_QUEUE)):
        if old.is_file() and current.is_file():
            old.unlink()
            removed.append(relative(old))
    return removed


def selftest() -> None:
    assert is_within(READY, HUB) and is_within(PUBLISHED, HUB)
    assert not is_within(RETIRED, HUB)
    assert VERSION_LIKE.search("movie_v12_FINAL")
    assert not VERSION_LIKE.search("S025_龍王閃擊對決榮耀女武神")
    print("publish_hub_layout self-test GREEN")


if __name__ == "__main__":
    selftest()
