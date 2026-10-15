"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Iterable


WARN_JOB_BYTES = 4 * 1024 ** 3


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}


VERSION_LIKE = re.compile(
    r"(?:^|[_\-. ])v\d+(?:[_\-. ]|$)|(?:^|[_\-. ])(?:final|old|backup|bak|copy)(?:[_\-. ]|$)",
    re.IGNORECASE,
)


def _resolved(path: os.PathLike | str, *, strict: bool = False) -> Path:
    return Path(path).expanduser().resolve(strict=strict)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assert_inside(path: os.PathLike | str, root: os.PathLike | str) -> tuple[Path, Path]:
    p, r = _resolved(path), _resolved(root)
    if p == r or not _is_within(p, r):
        raise ValueError("target must be a child of the declared job/output root: %s" % p)
    return p, r


def is_version_like(path: os.PathLike | str) -> bool:
    """只看 basename；避免父層歷史名稱污染新 current 輸出。"""
    return bool(VERSION_LIKE.search(Path(path).stem))


def _iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix.lower() != ".pyc":
            yield p


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 ** 2), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_tree(root: os.PathLike | str, *, hash_duplicates: bool = False,
               min_hash_bytes: int = 20 * 1024 ** 2) -> dict:
    """唯讀容量盤點；hash 選項只對同大小大檔算，避免每次健康檢查很慢。"""
    base = _resolved(root, strict=True)
    files = list(_iter_files(base))
    total = sum(p.stat().st_size for p in files)
    versioned = [p for p in files if is_version_like(p)]
    versioned_dirs = [p for p in base.rglob("*") if p.is_dir() and is_version_like(p)]
    videos = [p for p in files if p.suffix.lower() in VIDEO_EXTS]
    versioned_videos = [p for p in videos if is_version_like(p)]
    duplicate_groups = []
    hardlink_groups = []
    reclaimable = 0
    if hash_duplicates:
        size_groups: dict[int, list[Path]] = {}
        for p in files:
            size = p.stat().st_size
            if size >= min_hash_bytes:
                size_groups.setdefault(size, []).append(p)
        for size, group in size_groups.items():
            if len(group) < 2:
                continue
            hashes: dict[str, list[Path]] = {}
            for p in group:
                hashes.setdefault(_sha256(p), []).append(p)
            for digest, same in hashes.items():
                if len(same) > 1:
                    distinct: list[Path] = []
                    aliases: list[Path] = []
                    for candidate in same:
                        try:
                            linked = any(os.path.samefile(candidate, item) for item in distinct)
                        except OSError:
                            linked = False
                        (aliases if linked else distinct).append(candidate)
                    row = {
                        "sha256": digest,
                        "bytes_each": size,
                        "paths": [str(p) for p in same],
                        "distinct_storage_copies": len(distinct),
                        "hardlinked_paths": [str(p) for p in aliases],
                    }
                    if len(distinct) > 1:
                        duplicate_groups.append(row)
                        reclaimable += size * (len(distinct) - 1)
                    else:
                        hardlink_groups.append(row)
    hardlink_saved = sum(
        row["bytes_each"] * len(row["hardlinked_paths"])
        for row in hardlink_groups
    )
    return {
        "root": str(base),
        "files": len(files),
        "videos": len(videos),
        "bytes": total,
        "physical_bytes": total - hardlink_saved,
        "hardlink_saved_bytes": hardlink_saved,
        "warn_over_4gb": total - hardlink_saved > WARN_JOB_BYTES,
        "version_like_files": len(versioned),
        "version_like_examples": [str(p) for p in versioned[:30]],
        "version_like_video_files": len(versioned_videos),
        "version_like_video_examples": [str(p) for p in versioned_videos[:30]],
        "version_like_dirs": len(versioned_dirs),
        "version_like_dir_examples": [str(p) for p in versioned_dirs[:30]],
        "duplicate_groups": duplicate_groups,
        "hardlink_groups": hardlink_groups,
        "reclaimable_bytes": reclaimable,
    }


def deduplicate_archive_copies(root: os.PathLike | str, *, apply: bool = False,
                               min_hash_bytes: int = 20 * 1024 ** 2) -> dict:
    """Replace proven archive duplicates with hard links while preserving every path.

    Only a file below ``_archive`` is eligible, and only when a byte-identical survivor
    exists elsewhere below the same declared root.  No directory is removed and no
    delivery/current path is selected as a target.
    """
    base = _resolved(root, strict=True)
    archive = (base / "_archive").resolve()
    if not archive.is_dir() or not _is_within(archive, base):
        return {
            "status": "GREEN", "mode": "apply" if apply else "dry-run",
            "root": str(base), "archive": str(archive), "candidates": [],
            "candidate_count": 0, "replaced": [], "reclaimed_bytes": 0,
            "skipped_groups": 0, "errors": [],
        }

    audit = audit_tree(base, hash_duplicates=True, min_hash_bytes=min_hash_bytes)
    candidates, skipped = [], 0
    for group in audit["duplicate_groups"]:
        paths = [_resolved(path, strict=True) for path in group["paths"]]
        outside = sorted((p for p in paths if not _is_within(p, archive)), key=str)
        targets = sorted((p for p in paths if _is_within(p, archive)), key=str)
        if not outside or not targets:
            skipped += 1
            continue
        keeper = outside[0]
        for target in targets:
            if not _is_within(keeper, base) or not _is_within(target, archive):
                continue
            try:
                already_linked = os.path.samefile(keeper, target)
            except OSError:
                already_linked = False
            if already_linked:
                continue
            candidates.append({
                "target": str(target), "keeper": str(keeper),
                "sha256": group["sha256"], "bytes": int(group["bytes_each"]),
            })

    replaced, errors, reclaimed = [], [], 0
    if apply:
        for row in candidates:
            target = _resolved(row["target"], strict=True)
            keeper = _resolved(row["keeper"], strict=True)
            temp = target.with_name(".%s.dedupe-tmp" % target.name)
            try:
                _assert_inside(target, archive)
                if not _is_within(keeper, base) or _is_within(keeper, archive):
                    raise ValueError("keeper must remain outside _archive and inside root")
                if target.stat().st_size != keeper.stat().st_size:
                    raise RuntimeError("size changed after duplicate scan")
                if _sha256(target) != row["sha256"] or _sha256(keeper) != row["sha256"]:
                    raise RuntimeError("hash changed after duplicate scan")
                if temp.exists():
                    temp.unlink()
                os.link(keeper, temp)
                if _sha256(temp) != row["sha256"]:
                    raise RuntimeError("hard-link verification failed")
                os.replace(temp, target)
                if not os.path.samefile(keeper, target):
                    raise RuntimeError("replacement is not a verified hard link")
                replaced.append(row)
                reclaimed += row["bytes"]
            except (OSError, ValueError, RuntimeError) as exc:
                if temp.exists():
                    temp.unlink()
                errors.append({"target": row["target"], "error": str(exc)})
    return {
        "status": "GREEN" if not errors else "RED",
        "mode": "apply" if apply else "dry-run", "root": str(base),
        "archive": str(archive), "candidates": candidates,
        "candidate_count": len(candidates), "replaced": replaced,
        "reclaimed_bytes": reclaimed if apply else sum(row["bytes"] for row in candidates),
        "skipped_groups": skipped, "errors": errors,
    }
