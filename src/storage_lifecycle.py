# -*- coding: utf-8 -*-
"""storage_lifecycle.py — M115 自動剪輯儲存生命週期。

目標不是定期叫人手動清資料，而是讓 pipeline 天生不再製造 ``v2/v3/v4``
完整副本：

* 原始素材永遠不碰；
* 每個 job 只有 ``_out/current.mp4`` 一個目前成片；
* render 先寫 candidate，成功後用 ``os.replace`` 原子換版；
* 每次修改只追加一行 JSONL metadata，不保存整支影片；
* QA 綠後只刪本次 pipeline 明確註冊的可重建中間檔；
* 同磁碟交付優先 hard link，避免再複製一份位元完全相同的影片；
* 舊資料第一次啟用時列為 grandfathered，只報告、不擅自刪除。

CLI（所有清理命令預設 dry-run）：

    python storage_lifecycle.py audit videos
    python storage_lifecycle.py check <job>/_out
    python storage_lifecycle.py prune <job>/_out/_work
    python storage_lifecycle.py prune <job>/_out/_work --apply
    python storage_lifecycle.py deliver <job>/_out/current.mp4 <destination.mp4>
    python storage_lifecycle.py snapshot <job>/_out/current.mp4 <job> --label approved
    python storage_lifecycle.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Iterable


POLICY_VERSION = 1
CURRENT_BASENAME = "current.mp4"
POLICY_FILE = ".storage-policy.json"
HISTORY_FILE = ".autocut-history.jsonl"
MAX_MILESTONES = 2
WARN_JOB_BYTES = 4 * 1024 ** 3

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
VERSION_LIKE = re.compile(
    r"(?:^|[_\-. ])v\d+(?:[_\-. ]|$)|(?:^|[_\-. ])(?:final|old|backup|bak|copy)(?:[_\-. ]|$)",
    re.IGNORECASE,
)

# 只允許刪除這些由 build_one_short 明確產生、可 100% 重建的檔名。
# ``*_vis.mp4/json`` 是昂貴但可重用的視覺 cache，刻意不在此列。
TRANSIENT_PATTERNS = (
    "*_cap.mp4",
    "*_cards.mp4",
    "*_mux.mp4",
    "*_candidate.mp4",
    "*_motion_*.mp4",
)
TRANSIENT_DIR_PATTERNS = ("*_cards",)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def canonical_output_path(out_dir: os.PathLike | str) -> Path:
    return _resolved(out_dir) / CURRENT_BASENAME


def activate_policy(out_dir: os.PathLike | str) -> dict:
    """第一次啟用時凍結既有輸出清單；之後新增的版本檔就無法混入。

    舊成片不自動移動或刪除，符合「先報告、不破壞用戶資料」；但 baseline 只會建立
    一次，因此政策啟用後再產生 ``foo_v8.mp4`` 會被 storage gate 擋下。
    """
    root = _resolved(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / POLICY_FILE
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if int(state.get("version", 0)) != POLICY_VERSION:
            raise RuntimeError("unsupported storage policy version: %r" % state.get("version"))
        return state

    legacy = sorted(
        p.name for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS and p.name != CURRENT_BASENAME
    )
    state = {
        "version": POLICY_VERSION,
        "activated_at": _utc_now(),
        "current": CURRENT_BASENAME,
        "legacy_files": legacy,
        "rules": {
            "direct_current_videos": 1,
            "max_milestones": MAX_MILESTONES,
            "versioned_outputs": "blocked_after_activation",
        },
    }
    _write_json_atomic(state_path, state)
    return state


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(".%s.tmp" % path.name)
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def atomic_publish(candidate: os.PathLike | str, current: os.PathLike | str) -> Path:
    """將已完成的 candidate 原子換成 current，不在半成品上覆寫舊成片。"""
    src, dst = _resolved(candidate, strict=True), _resolved(current)
    if src == dst:
        raise ValueError("candidate and current must be different paths")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.parent != dst.parent:
        tmp = dst.with_name(".%s.publish-tmp" % dst.name)
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        src.unlink()
    else:
        os.replace(src, dst)
    return dst


def link_or_copy(src: os.PathLike | str, dst: os.PathLike | str) -> dict:
    """建立穩定交付檔；同 volume 優先 hard link，失敗才 copy。

    先寫臨時路徑再 replace。未來 current 用 :func:`atomic_publish` 換 inode 時，已交付
    hard link 仍指向舊的核准內容，不會跟著被改寫。
    """
    source, target = _resolved(src, strict=True), _resolved(dst)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target.exists() and os.path.samefile(source, target):
            return {"method": "existing-hardlink", "path": str(target), "bytes_added": 0}
    except OSError:
        pass
    tmp = target.with_name(".%s.delivery-tmp" % target.name)
    if tmp.exists():
        tmp.unlink()
    method = "hardlink"
    try:
        os.link(source, tmp)
        bytes_added = 0
    except OSError:
        method = "copy"
        shutil.copy2(source, tmp)
        bytes_added = source.stat().st_size
    os.replace(tmp, target)
    return {"method": method, "path": str(target), "bytes_added": bytes_added}


def create_milestone(current: os.PathLike | str, job_root: os.PathLike | str,
                     label: str) -> dict:
    """建立核准／已發布 binary milestone；到 2 份就 fail，不擅自淘汰舊決策。"""
    if label not in {"approved", "published"}:
        raise ValueError("milestone label must be approved or published")
    job = _resolved(job_root)
    source = _resolved(current, strict=True)
    if not _is_within(source, job):
        raise ValueError("current output is outside job root")
    milestone_dir = job / "_milestones"
    milestone_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(p for p in milestone_dir.glob("*.mp4") if p.is_file())
    if len(existing) >= MAX_MILESTONES:
        raise RuntimeError(
            "milestone limit reached (%d); choose which approved/published milestone to replace"
            % MAX_MILESTONES
        )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = milestone_dir / ("%s-%s.mp4" % (label, stamp))
    result = link_or_copy(source, target)
    result.update({"label": label, "milestones": len(existing) + 1,
                   "limit": MAX_MILESTONES})
    return result


def append_history(job_root: os.PathLike | str, current: os.PathLike | str,
                   *, qa: dict | None = None, label: str = "build") -> Path:
    """只記 metadata，不用整支 vN 影片當版本紀錄。"""
    root = _resolved(job_root)
    video = _resolved(current, strict=True)
    if video != root and not _is_within(video, root):
        raise ValueError("current output is outside job root")
    row = {
        "at": _utc_now(),
        "label": label,
        "current": video.relative_to(root).as_posix(),
        "bytes": video.stat().st_size,
        "mtime_ns": video.stat().st_mtime_ns,
        "qa_green": bool((qa or {}).get("all_green")),
    }
    history = root / HISTORY_FILE
    with history.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return history


def transient_candidates(work_dir: os.PathLike | str) -> list[Path]:
    root = _resolved(work_dir)
    if not root.is_dir():
        return []
    found: set[Path] = set()
    for pattern in TRANSIENT_PATTERNS:
        found.update(p for p in root.glob(pattern) if p.is_file())
    for pattern in TRANSIENT_DIR_PATTERNS:
        found.update(p for p in root.glob(pattern) if p.is_dir())
    return sorted(found, key=lambda p: str(p).lower())


def prune_transients(work_dir: os.PathLike | str, *, apply: bool = False) -> dict:
    """只處理白名單中間檔；預設 dry-run，絕不碰 raw／current／vis cache。"""
    root = _resolved(work_dir)
    items = transient_candidates(root)
    bytes_total = sum(
        p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        for p in items
    )
    removed: list[str] = []
    if apply:
        for item in items:
            safe, _ = _assert_inside(item, root)
            if safe.is_dir():
                shutil.rmtree(safe)
            else:
                safe.unlink()
            removed.append(str(safe))
    return {
        "mode": "apply" if apply else "dry-run",
        "work_dir": str(root),
        "candidates": [str(p) for p in items],
        "count": len(items),
        "bytes": bytes_total,
        "removed": removed,
    }


def prune_registered(work_dir: os.PathLike | str, paths: Iterable[os.PathLike | str],
                     *, apply: bool = False) -> dict:
    """長片等 pipeline 可傳「本輪確定產生」的精確路徑，不做 wildcard 猜測。"""
    root = _resolved(work_dir)
    items: list[Path] = []
    for raw in paths:
        p = _resolved(raw)
        if not p.exists():
            continue
        safe, _ = _assert_inside(p, root)
        items.append(safe)
    # 保持順序但去重；拒絕 current／visual cache 等保留資產。
    unique = list(dict.fromkeys(items))
    for p in unique:
        low = p.name.lower()
        if low == CURRENT_BASENAME or low.endswith(("_vis.mp4", "_vis.json")):
            raise ValueError("registered transient points at a protected file: %s" % p)
    bytes_total = sum(
        p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        for p in unique
    )
    removed: list[str] = []
    if apply:
        for p in unique:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(str(p))
    return {
        "mode": "apply" if apply else "dry-run",
        "work_dir": str(root),
        "candidates": [str(p) for p in unique],
        "count": len(unique),
        "bytes": bytes_total,
        "removed": removed,
    }


def assert_output_policy(out_dir: os.PathLike | str, state: dict | None = None) -> dict:
    """阻止政策啟用後新增第二支成片或版本號輸出。"""
    root = _resolved(out_dir)
    state = state or activate_policy(root)
    legacy = set(state.get("legacy_files") or [])
    direct = sorted(
        p.name for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )
    current = root / CURRENT_BASENAME
    unexpected = [n for n in direct if n != CURRENT_BASENAME and n not in legacy]
    versioned_new = [n for n in unexpected if is_version_like(n)]
    problems = []
    if not current.is_file():
        problems.append("missing %s" % CURRENT_BASENAME)
    if unexpected:
        problems.append("new extra output videos: %s" % ", ".join(unexpected))
    if versioned_new:
        problems.append("version-number output is forbidden: %s" % ", ".join(versioned_new))
    if problems:
        raise AssertionError("storage policy failed — " + " | ".join(problems))
    return {
        "current": str(current),
        "legacy_count": len(legacy),
        "direct_video_count": len(direct),
        "new_extra_count": 0,
    }


def finalize_success(job_root: os.PathLike | str, current: os.PathLike | str,
                     work_dir: os.PathLike | str, qa: dict,
                     registered_transients: Iterable[os.PathLike | str] = ()) -> dict:
    """QA 綠後的唯一 cleanup 入口。紅燈時不清，保留 debug 證據。"""
    if not bool((qa or {}).get("all_green")):
        return {"finalized": False, "reason": "qa_not_green", "removed_bytes": 0}
    job = _resolved(job_root)
    video = _resolved(current, strict=True)
    work, _ = _assert_inside(work_dir, job)
    if not _is_within(video, job):
        raise ValueError("current output is outside job root")
    pruned = prune_transients(work, apply=True)
    registered = prune_registered(work, registered_transients, apply=True)
    history = append_history(job, video, qa=qa)
    policy = assert_output_policy(video.parent)
    return {
        "finalized": True,
        "removed_files": pruned["count"] + registered["count"],
        "removed_bytes": pruned["bytes"] + registered["bytes"],
        "history": str(history),
        "policy": policy,
    }


def _iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix.lower() != ".pyc":
            yield p


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
                h = hashlib.sha256()
                with p.open("rb") as fh:
                    for block in iter(lambda: fh.read(4 * 1024 ** 2), b""):
                        h.update(block)
                hashes.setdefault(h.hexdigest(), []).append(p)
            for digest, same in hashes.items():
                if len(same) > 1:
                    duplicate_groups.append({
                        "sha256": digest,
                        "bytes_each": size,
                        "paths": [str(p) for p in same],
                    })
                    reclaimable += size * (len(same) - 1)
    return {
        "root": str(base),
        "files": len(files),
        "videos": len(videos),
        "bytes": total,
        "warn_over_4gb": total > WARN_JOB_BYTES,
        "version_like_files": len(versioned),
        "version_like_examples": [str(p) for p in versioned[:30]],
        "version_like_video_files": len(versioned_videos),
        "version_like_video_examples": [str(p) for p in versioned_videos[:30]],
        "version_like_dirs": len(versioned_dirs),
        "version_like_dir_examples": [str(p) for p in versioned_dirs[:30]],
        "duplicate_groups": duplicate_groups,
        "reclaimable_bytes": reclaimable,
    }


def _human_bytes(n: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return "%.2f %s" % (value, unit)
        value /= 1024
    return "%d B" % n


def _selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="storage_lifecycle_") as td:
        job = Path(td) / "job"
        out = job / "_out"
        work = out / "_work"
        out.mkdir(parents=True)
        work.mkdir()

        legacy = out / "old_v7.mp4"
        legacy.write_bytes(b"legacy")
        state = activate_policy(out)
        assert state["legacy_files"] == ["old_v7.mp4"]
        assert is_version_like("movie_v12_FINAL.mp4")
        assert not is_version_like("current.mp4")

        candidate = work / "current_candidate.mp4"
        candidate.write_bytes(b"revision-one")
        current = atomic_publish(candidate, canonical_output_path(out))
        delivered = Path(td) / "published.mp4"
        info = link_or_copy(current, delivered)
        assert info["method"] in ("hardlink", "copy") and delivered.read_bytes() == b"revision-one"

        # 原子換 current 後，先前 hard link/copy 必須仍是上一版內容。
        candidate.write_bytes(b"revision-two")
        atomic_publish(candidate, current)
        assert current.read_bytes() == b"revision-two"
        assert delivered.read_bytes() == b"revision-one"

        one = create_milestone(current, job, "approved")
        two = create_milestone(current, job, "published")
        assert one["milestones"] == 1 and two["milestones"] == 2
        try:
            create_milestone(current, job, "approved")
        except RuntimeError:
            pass
        else:
            raise AssertionError("third binary milestone was not blocked")

        (work / "current_vis.mp4").write_bytes(b"cache")
        (work / "current_vis.json").write_text("{}", encoding="utf-8")
        (work / "current_cap.mp4").write_bytes(b"throwaway")
        (work / "burned.mp4").write_bytes(b"longform-throwaway")
        cards = work / "current_cards"
        cards.mkdir()
        (cards / "a.png").write_bytes(b"png")
        dry = prune_transients(work)
        assert dry["count"] == 2 and (work / "current_cap.mp4").exists()
        qa = {"all_green": True}
        final = finalize_success(job, current, work, qa,
                                 registered_transients=[work / "burned.mp4"])
        assert final["finalized"] and not (work / "current_cap.mp4").exists()
        assert not (work / "burned.mp4").exists()
        assert (work / "current_vis.mp4").exists() and legacy.exists()

        # baseline 之後的新 vN 不能進來。
        bad = out / "movie_v8.mp4"
        bad.write_bytes(b"bad")
        try:
            assert_output_policy(out, state)
        except AssertionError:
            pass
        else:
            raise AssertionError("new versioned output was not blocked")
    print("storage_lifecycle self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="M115 auto-edit storage lifecycle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit")
    a.add_argument("root")
    a.add_argument("--hash-duplicates", action="store_true")
    a.add_argument("--min-size-mb", type=float, default=20.0)
    c = sub.add_parser("check")
    c.add_argument("out_dir")
    p = sub.add_parser("prune")
    p.add_argument("work_dir")
    p.add_argument("--apply", action="store_true")
    d = sub.add_parser("deliver")
    d.add_argument("current")
    d.add_argument("destination")
    s = sub.add_parser("snapshot")
    s.add_argument("current")
    s.add_argument("job_root")
    s.add_argument("--label", choices=["approved", "published"], required=True)
    sub.add_parser("selftest")
    ns = ap.parse_args(argv)

    if ns.cmd == "selftest":
        _selftest()
        return 0
    if ns.cmd == "audit":
        result = audit_tree(ns.root, hash_duplicates=ns.hash_duplicates,
                            min_hash_bytes=int(ns.min_size_mb * 1024 ** 2))
    elif ns.cmd == "check":
        result = assert_output_policy(ns.out_dir)
    elif ns.cmd == "prune":
        result = prune_transients(ns.work_dir, apply=ns.apply)
    elif ns.cmd == "snapshot":
        result = create_milestone(ns.current, ns.job_root, ns.label)
    else:
        result = link_or_copy(ns.current, ns.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if ns.cmd in ("audit", "prune"):
        print("size:", _human_bytes(result.get("bytes", 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
