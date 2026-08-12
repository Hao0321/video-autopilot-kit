"""
silent_vlog_maker.asset_scanner — Auto-populate assets/index.json by scanning filesystem.

掃描專案 assets/ 並自動建立或更新 index.json：
- bgm/ — recursive 場景資料夾制掃描（2026-07-24 r3），ffprobe duration + bitrate
- fonts/ — font metadata (Noto / SmileySans / etc.)
- broll/ — file inventory（v0.3 index 下只補缺不覆蓋 M9 desc）
- end-screen-templates/ + thumbnail-templates/ — file inventory

執行後 video-autopilot 各 mode 可直接讀 index.json 找 asset by tag。
⚠️ index.json v0.3（2026-07-24）起 BGM 段是 pointer——選曲讀 assets/bgm/README.md
（人類約定）+ 各夾 bgm_index.json（機器索引，assets/bgm/_build_index.py 產）；
scan_all_assets 在 v0.3 模式只補缺不清洗人工語意層。
self-test：python -m silent_vlog_maker.asset_scanner
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Support both ``python -m silent_vlog_maker.asset_scanner`` and the health
# runner's direct ``python asset_scanner.py`` invocation.
_AUTOPILOT_DIR = Path(__file__).resolve().parent.parent
if str(_AUTOPILOT_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOPILOT_DIR))


# 2026-06-10 adopter fix: 用環境變數解析 root（不寫死層數）。淺 checkout 時
# parents[4] 會 IndexError / 解析到磁碟根 → 寫 D:\assets 失敗。改 lazy + env-aware。
import os


def _resolve_project_root() -> Path:
    env = os.environ.get("VIDEO_KIT_PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # 找含 assets/ 的最近祖先；找不到就退回套件上 2 層
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets").is_dir():
            return p
    return here.parents[min(2, len(here.parents) - 1)]


def get_assets_dir() -> Path:
    d = _resolve_project_root() / "assets"
    d.mkdir(parents=True, exist_ok=True)   # 確保可寫（之前無 mkdir → FileNotFoundError）
    return d


def get_index_file() -> Path:
    return get_assets_dir() / "index.json"


# 向後相容的 module-level 值（import 時解析一次；要動態請用 get_* 函數）
_PROJECT_ROOT = _resolve_project_root()
ASSETS_DIR = _PROJECT_ROOT / "assets"
INDEX_FILE = ASSETS_DIR / "index.json"


def _portable_path(path: Path) -> str:
    """Store project-relative POSIX paths; resolve them only at runtime."""
    try:
        return path.resolve().relative_to(_PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


# ─────────────────────────────────────────────────────────────────────
# BGM scanner (ffprobe-based)
# ─────────────────────────────────────────────────────────────────────

BGM_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def scan_bgm() -> dict:
    """Scan assets/bgm/ RECURSIVELY for audio files + ffprobe metadata（2026-07-24 r3）.

    2026-06-22 起 bgm/ 是場景資料夾制（`場景/主題-NN.wav`）；舊版只掃 root mp3
    （場景制下會掃到 0 檔）。現在：
    - recursive 全格式（BGM_AUDIO_EXTS）
    - entry key = 相對 bgm/ 的 POSIX 路徑（e.g. "教學/AI科技軟體教學-01.wav"）
    - scene（=場景資料夾名）當 content_type/tags；root 散檔標 "root-未歸檔"
    - 人類約定 = assets/bgm/README.md；bpm/RMS 機器索引 = 各夾 bgm_index.json
    """
    bgm_dir = ASSETS_DIR / "bgm"
    if not bgm_dir.exists():
        return {}

    entries = {}
    for f in sorted(bgm_dir.rglob("*"), key=lambda p: str(p).lower()):
        if not f.is_file() or f.suffix.lower() not in BGM_AUDIO_EXTS:
            continue
        # ffprobe metadata
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate",
             "-of", "default=nw=1", str(f)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        dur = 0.0
        bitrate_kbps = 0
        for line in (result.stdout or "").splitlines():
            if line.startswith("duration="):
                try:
                    dur = round(float(line.split("=")[1]), 2)
                except (ValueError, IndexError):
                    pass
            elif line.startswith("bit_rate="):
                try:
                    bitrate_kbps = int(line.split("=")[1]) // 1000
                except (ValueError, IndexError):
                    pass

        rel = f.relative_to(bgm_dir).as_posix()
        scene = rel.split("/")[0] if "/" in rel else "root-未歸檔"
        entries[rel] = {
            "filepath": _portable_path(f),
            "duration_sec": dur,
            "bit_rate_kbps": bitrate_kbps,
            "scene": scene,
            "loop_for_full_video": True,
            "best_for_content_type": [scene],
            "tags": [scene],
        }
    return entries


# ─────────────────────────────────────────────────────────────────────
# Fonts scanner
# ─────────────────────────────────────────────────────────────────────

def scan_fonts() -> dict:
    """Scan assets/fonts/ for .ttf / .otf / .ttc."""
    fonts_dir = ASSETS_DIR / "fonts"
    if not fonts_dir.exists():
        return {}

    entries = {}
    for f in sorted(fonts_dir.iterdir()):
        if f.suffix.lower() not in (".ttf", ".otf", ".ttc"):
            continue
        stem = f.stem.lower()
        # Heuristic tags
        if "noto" in stem and "serif" in stem:
            tags = ["serif", "中文", "Vlog narrative", "M43 whitelist"]
            use_case = "Vlog narrative / sub caption"
        elif "noto" in stem:
            tags = ["sans-serif", "中文", "通用"]
            use_case = "Fallback / 通用"
        elif "smiley" in stem:
            tags = ["手寫感", "限拉丁字"]
            use_case = "Latin emphasis only (中文 coverage 不全 → 不建議純中文)"
        else:
            tags = []
            use_case = "?"

        entries[f.name] = {
            "filepath": _portable_path(f),
            "size_kb": f.stat().st_size // 1024,
            "tags": tags,
            "use_case": use_case,
        }
    return entries


# ─────────────────────────────────────────────────────────────────────
# Template scanners (broll / end-screen / thumbnail)
# ─────────────────────────────────────────────────────────────────────

def scan_templates(category: str) -> dict:
    """Generic template scanner — lists files with size + extension."""
    cat_dir = ASSETS_DIR / category
    if not cat_dir.exists():
        return {}

    entries = {}
    for f in sorted(cat_dir.rglob("*")):
        if not f.is_file():
            continue
        # Skip junk
        if f.suffix.lower() in (".db", ".tmp", ".cache"):
            continue
        rel = f.relative_to(cat_dir)
        entries[str(rel).replace("\\", "/")] = {
            "filepath": _portable_path(f),
            "size_kb": f.stat().st_size // 1024,
            "ext": f.suffix.lower(),
        }
    return entries


# ─────────────────────────────────────────────────────────────────────
# Full scan + write index.json
# ─────────────────────────────────────────────────────────────────────

def _scan_category_payload() -> dict[str, dict]:
    return {
        "bgm": scan_bgm(),
        "fonts": scan_fonts(),
        "end_screen": scan_templates("end-screen-templates"),
        "thumbnail": scan_templates("thumbnail-templates"),
        "broll": scan_templates("broll"),
        "gameplay": scan_templates("gameplay"),
    }


def _merge_legacy_index(existing: dict, scanned: dict[str, dict]) -> None:
    existing.setdefault("bgm_actual", {})
    for name, meta in scanned["bgm"].items():
        if name in existing["bgm_actual"]:
            existing["bgm_actual"][name]["duration_sec"] = meta["duration_sec"]
            existing["bgm_actual"][name]["bit_rate_kbps"] = meta["bit_rate_kbps"]
        else:
            existing["bgm_actual"][name] = meta
    existing["_meta"]["asset_count"] = sum(len(rows) for rows in scanned.values())
    for key, source in (
        ("fonts_actual", "fonts"), ("end_screen_actual", "end_screen"),
        ("thumbnail_actual", "thumbnail"), ("broll_actual", "broll"),
        ("gameplay_actual", "gameplay"),
    ):
        existing[key] = scanned[source]


def _merge_current_index(existing: dict, scanned: dict[str, dict]) -> None:
    broll = existing.setdefault("broll_actual", {})
    seen = set(scanned["broll"])
    for rel, meta in scanned["broll"].items():
        if rel not in broll:
            broll[rel] = {**meta, "desc": "unknown（scanner 補入，尚未 M9 看首幀）", "tags": []}
    for rel, entry in broll.items():
        if rel.startswith("_"):
            continue
        entry["missing"] = rel not in seen
        if not entry["missing"]:
            entry.pop("missing", None)
    for key, source in (
        ("end_screen_actual", "end_screen"),
        ("thumbnail_actual", "thumbnail"),
        ("gameplay_actual", "gameplay"),
    ):
        files = scanned[source]
        if files:
            notes = {k: v for k, v in existing.get(key, {}).items() if k.startswith("_")}
            existing[key] = {**notes, **files}
    existing["_meta"].setdefault("counts", {})["broll"] = sum(
        not key.startswith("_") for key in broll
    )


def _write_asset_index(payload: dict, *, backup: bool) -> None:
    idx = get_index_file()
    if backup and idx.exists():
        idx.with_suffix(".json.bak").write_text(
            idx.read_text(encoding="utf-8"), encoding="utf-8"
        )
    idx.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def scan_all_assets(write: bool = True, backup: bool = True) -> dict:
    """Scan all asset categories + update index.json.

    Args:
        write: write the result to assets/index.json
        backup: backup existing index.json to index.json.bak before overwrite
    """
    from datetime import datetime

    # Load existing schema (preserve _meta + _example_templates)
    existing = {}
    if INDEX_FILE.exists():
        existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    scanned = _scan_category_payload()

    # Update existing structure (preserve _meta + naming conventions)
    existing.setdefault("_meta", {})["last_scan"] = datetime.now().isoformat(timespec="seconds")
    existing["_meta"]["scanner_version"] = "asset_scanner v2 (2026-07-24 r3)"

    # 2026-07-24 r3：index.json v0.3 起 BGM 段=pointer（single source = bgm/README.md +
    # 各夾 bgm_index.json）、broll_actual 帶 M9 人寫 desc、fonts_actual 是 family 制。
    # v0.3 模式下 scanner 只「補缺不覆蓋」，避免把人工語意層打掉。
    v03 = str(existing.get("_meta", {}).get("schema_version", "0.2")) >= "0.3"

    (_merge_current_index if v03 else _merge_legacy_index)(existing, scanned)

    if write:
        _write_asset_index(existing, backup=backup)

    return existing


def _hub_asset_matches(cue_text: str, category: str | None,
                       content_type: str | None) -> list[dict]:
    from asset_registry import AssetRegistry
    from domain_taxonomy import infer_domain

    registry = AssetRegistry(_resolve_project_root())
    domain = infer_domain(f"{content_type or ''} {cue_text}")
    selected = []
    if category in (None, "broll"):
        selected.extend(("broll", item) for item in
                        registry.select_broll(cue_text, domain, "landscape", .55, limit=5)
                        if item.get("confidence", 0) >= .2)
    if category in (None, "bgm"):
        selected.extend(("bgm", item) for item in
                        registry.select_music(cue_text, domain, 30, .55, limit=5))
    if category == "sfx":
        selected.extend(("sfx", item) for item in
                        registry.select_sfx(cue_text, domain, .55, limit=5))
    output = []
    for cat_name, item in selected:
        path = Path(item["path"])
        absolute = path if path.is_absolute() else registry.root / path
        output.append({
            "name": path.name, "category": cat_name, "score": item.get("score", 0),
            "confidence": item.get("confidence", 0), "filepath": str(absolute), **item,
        })
    return sorted(output, key=lambda row: (-row.get("score", 0), row.get("path", "")))


def _legacy_asset_score(entry: dict, cue_lower: str,
                        content_type: str | None) -> int:
    score = sum(5 for cue in entry.get("matches_cues", []) if cue_lower in cue.lower())
    score += sum(2 for tag in entry.get("tags", [])
                 if cue_lower in tag.lower() or tag.lower() in cue_lower)
    theme = entry.get("theme", "").strip()
    if theme and (cue_lower in theme.lower() or theme.lower() in cue_lower):
        score += 3
    if content_type and not any(
            content_type.lower() in value.lower()
            for value in entry.get("best_for_content_type", [])):
        return -1
    return score


def _legacy_asset_matches(cue_text: str, category: str | None,
                          content_type: str | None) -> list[dict]:
    if not INDEX_FILE.exists():
        return []
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    section_names = {
        "broll": "broll_actual", "bgm": "bgm_actual", "fonts": "fonts_actual",
    }
    categories = section_names if category is None else (category,)
    matches = []
    for cat_name in categories:
        entries = index.get(section_names.get(cat_name, ""), {})
        for name, entry in entries.items():
            if name.startswith("_"):
                continue
            score = _legacy_asset_score(entry, cue_text.lower(), content_type)
            if score > 0:
                matches.append({"name": name, "category": cat_name, "score": score, **entry})
    return sorted(matches, key=lambda item: item["score"], reverse=True)


def find_assets_by_cue(cue_text: str, category: str = None,
                       content_type: str = None) -> list[dict]:
    """Use the current hub, with legacy index lookup retained for fonts."""
    if category in (None, "broll", "bgm", "sfx"):
        return _hub_asset_matches(cue_text, category, content_type)
    return _legacy_asset_matches(cue_text, category, content_type)


def print_asset_summary(index: dict = None) -> None:
    """Print human-readable asset library summary."""
    if index is None:
        if not INDEX_FILE.exists():
            print("No index.json found. Run scan_all_assets() first.")
            return
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    print("\n📦 Asset Library Summary")
    print("=" * 60)
    print(f"Last scan: {index.get('_meta', {}).get('last_scan', 'never')}")

    if "_pointer" in index.get("bgm", {}):
        print("\n🎵 BGM: pointer mode (v0.3) — see assets/bgm/README.md + per-folder bgm_index.json")
    else:
        bgm = index.get("bgm_actual", {})
        bgm_real = {k: v for k, v in bgm.items() if not k.startswith("_")}
        print(f"\n🎵 BGM ({len(bgm_real)} tracks):")
        for name, meta in bgm_real.items():
            types = ", ".join(meta.get("best_for_content_type", ["?"])[:2])
            print(f"  {name:<25} {meta.get('duration_sec', 0):>6.1f}s  →  {types}")

    fonts = index.get("fonts_actual", {})
    print(f"\n✏️  Fonts ({len(fonts)} files):")
    for name, meta in fonts.items():
        print(f"  {name:<35} {meta.get('size_kb', 0):>4} KB  ({meta.get('use_case', '?')})")

    for cat_name, cat_key in [("End screens", "end_screen_actual"),
                              ("Thumbnails", "thumbnail_actual"),
                              ("B-roll", "broll_actual"),
                              ("Gameplay", "gameplay_actual")]:
        cat = index.get(cat_key, {})
        if cat:
            print(f"\n📁 {cat_name} ({len(cat)} files)")


# ── minimal self-test（2026-07-24 r3；跑法：python -m silent_vlog_maker.asset_scanner）──
def _selftest() -> int:
    """scan_bgm recursive 制 + v0.3 不覆蓋保證。唯讀（write=False），console ASCII only."""
    fails = []

    def check(name, ok, detail=""):
        print(("[PASS] " if ok else "[FAIL] ") + name + ((" -- " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    bgm = scan_bgm()
    check("scan_bgm finds tracks recursively", len(bgm) >= 100, "found %d" % len(bgm))
    check("scan_bgm keys are scene-relative", all("/" in k or v["scene"] == "root-未歸檔"
                                                  for k, v in bgm.items()))
    check("teaching folder scanned", any(k.startswith("教學/") for k in bgm))
    check("non-mp3 formats included", any(k.lower().endswith(".wav") for k in bgm))
    check("asset hub restores BGM cue search", bool(find_assets_by_cue("AI 教學", "bgm", "teaching")))

    idx_before = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else {}
    result = scan_all_assets(write=False)
    if str(idx_before.get("_meta", {}).get("schema_version", "")) >= "0.3":
        check("v0.3: no bgm_actual resurrection", "bgm_actual" not in result)
        check("v0.3: bgm pointer intact", "_pointer" in result.get("bgm", {}))
        descs = [v for k, v in result.get("broll_actual", {}).items()
                 if not k.startswith("_") and isinstance(v, dict)]
        check("v0.3: broll desc preserved", bool(descs) and
              sum(1 for v in descs if v.get("desc")) >= len(descs) - 2)
    else:
        print("[SKIP] index.json not v0.3 - legacy merge path not asserted")
    print("selftest:", "OK" if not fails else "FAILED %d" % len(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
