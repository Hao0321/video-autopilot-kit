"""
silent_vlog_maker.asset_scanner — Auto-populate assets/index.json by scanning filesystem.

掃 D:\\Hao0321_YT_Claude\\assets\\ + 自動建/更新 index.json：
- bgm/ — ffprobe duration + bitrate
- fonts/ — font metadata (Noto / SmileySans / etc.)
- broll/ — placeholder（待用戶 populate）
- end-screen-templates/ + thumbnail-templates/ — file inventory

執行後 video-autopilot 各 mode 可直接讀 index.json 找 asset by tag。
"""
import json
import subprocess
from pathlib import Path
from typing import Optional


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


# ─────────────────────────────────────────────────────────────────────
# BGM scanner (ffprobe-based)
# ─────────────────────────────────────────────────────────────────────

def scan_bgm() -> dict:
    """Scan assets/bgm/ for mp3 files + ffprobe metadata.

    Returns dict matching index.json `bgm_actual` schema.
    """
    bgm_dir = ASSETS_DIR / "bgm"
    if not bgm_dir.exists():
        return {}

    entries = {}
    for f in sorted(bgm_dir.iterdir()):
        if f.suffix.lower() != ".mp3":
            continue
        # ffprobe metadata
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate",
             "-of", "default=nw=1", str(f)],
            capture_output=True, text=True
        )
        dur = 0.0
        bitrate_kbps = 0
        for line in result.stdout.splitlines():
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

        # Heuristic: classify by filename prefix
        stem = f.stem
        if stem.startswith("教學"):
            content_types = ["教學-Demo", "教學-Reflective", "教學-Update"]
            tags = ["AI 教學", "lo-fi tech", "focus"]
        elif stem.startswith("旅遊"):
            content_types = ["Vlog", "旅遊-Vlog", "Silent-Vlog"]
            tags = ["旅遊", "輕快", "戶外"]
        elif stem.startswith("DIY") or stem.startswith("興趣"):
            content_types = ["Low-DIY", "Low-開箱"]
            tags = ["DIY", "手作", "興趣"]
        elif stem.startswith("chill"):
            content_types = ["通用", "Low-X", "Silent-Vlog"]
            tags = ["chill", "lo-fi", "通用", "fallback"]
        else:
            content_types = ["unknown"]
            tags = []

        entries[f.name] = {
            "filepath": str(f).replace("\\", "\\\\"),
            "duration_sec": dur,
            "bit_rate_kbps": bitrate_kbps,
            "loop_for_full_video": True,
            "best_for_content_type": content_types,
            "tags": tags,
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
            "filepath": str(f).replace("\\", "\\\\"),
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
            "filepath": str(f).replace("\\", "\\\\"),
            "size_kb": f.stat().st_size // 1024,
            "ext": f.suffix.lower(),
        }
    return entries


# ─────────────────────────────────────────────────────────────────────
# Full scan + write index.json
# ─────────────────────────────────────────────────────────────────────

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

    # Scan each category
    bgm = scan_bgm()
    fonts = scan_fonts()
    end_screen = scan_templates("end-screen-templates")
    thumbnail = scan_templates("thumbnail-templates")
    broll_files = scan_templates("broll")
    gameplay_files = scan_templates("gameplay")

    # Update existing structure (preserve _meta + _example_template + naming conventions)
    existing.setdefault("_meta", {})["last_scan"] = datetime.now().isoformat(timespec="seconds")
    existing["_meta"]["asset_count"] = (
        len(bgm) + len(fonts) + len(end_screen) + len(thumbnail) +
        len(broll_files) + len(gameplay_files)
    )
    existing["_meta"]["scanner_version"] = "asset_scanner v1 (2026-05-24)"

    # bgm_actual: merge — keep existing manual entries, add discovered ones
    existing.setdefault("bgm_actual", {})
    for name, meta in bgm.items():
        if name in existing["bgm_actual"]:
            # Preserve manual fields (notes, custom tags) — only refresh duration / bitrate
            existing["bgm_actual"][name]["duration_sec"] = meta["duration_sec"]
            existing["bgm_actual"][name]["bit_rate_kbps"] = meta["bit_rate_kbps"]
        else:
            existing["bgm_actual"][name] = meta

    # fonts_actual: new section
    existing["fonts_actual"] = fonts

    # template inventories (file-level only — manual semantic tags above _example_template stay)
    existing["end_screen_actual"] = end_screen
    existing["thumbnail_actual"] = thumbnail
    existing["broll_actual"] = broll_files
    existing["gameplay_actual"] = gameplay_files

    if write:
        idx = get_index_file()  # 確保 assets/ 目錄存在（mkdir）+ env-aware（2026-06-10 fix）
        if backup and idx.exists():
            idx.with_suffix(".json.bak").write_text(
                idx.read_text(encoding="utf-8"), encoding="utf-8"
            )
        idx.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    return existing


def find_assets_by_cue(cue_text: str, category: str = None,
                       content_type: str = None) -> list[dict]:
    """Find b-roll / bgm assets that match a script cue or theme.

    Args:
        cue_text: e.g. "寫程式 montage" / "沖咖啡 開頭" / "社群 CTA"
        category: optional filter "broll" / "bgm" / "fonts"
        content_type: optional filter "教學-Demo" / "Vlog" / etc.

    Returns: list of matching entries (sorted by tag relevance)
    """
    if not INDEX_FILE.exists():
        return []
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    matches = []
    cue_lower = cue_text.lower()

    def score(entry: dict) -> int:
        s = 0
        # Exact cue match in matches_cues = +5
        for c in entry.get("matches_cues", []):
            if cue_lower in c.lower():
                s += 5
        # Tag match = +2
        for t in entry.get("tags", []):
            if cue_lower in t.lower() or t.lower() in cue_lower:
                s += 2
        # Theme match = +3 (only if theme is non-empty)
        theme = entry.get("theme", "").strip()
        if theme and (cue_lower in theme.lower() or theme.lower() in cue_lower):
            s += 3
        # Content type filter
        if content_type:
            if not any(content_type.lower() in ct.lower()
                       for ct in entry.get("best_for_content_type", [])):
                s = -1  # exclude
        return s

    # Walk all *_actual sections
    sections = []
    if category in (None, "broll"):
        sections.append(("broll", index.get("broll_actual", {})))
    if category in (None, "bgm"):
        sections.append(("bgm", index.get("bgm_actual", {})))
    if category in (None, "fonts"):
        sections.append(("fonts", index.get("fonts_actual", {})))

    for cat_name, entries in sections:
        for name, entry in entries.items():
            if name.startswith("_"):
                continue
            s = score(entry)
            if s > 0:
                matches.append({
                    "name": name,
                    "category": cat_name,
                    "score": s,
                    **entry,
                })

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


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
