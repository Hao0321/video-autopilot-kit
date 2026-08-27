"""
silent_vlog_maker.routing — Content type + layout 自動偵測 (2026-05-24 v1; 2026-06-20 從 content_routing 拆出).

接到 raw_dir → 自動判斷：
- Content type（旅遊 / 教學 / 開箱 / DIY / Reflective）
- Layout（portrait / landscape / mixed）
- Recommended pipeline path（Path D / E / B / Auto）
- Recommended BGM
- Recommended preset family

決策邏輯基於 R1 v2 audit (audit.py) 11 維度結果。Mass production 第一步。
"""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from asset_registry import recommend_bgm_scene
from project_paths import asset_path
from .audit import ClipAudit, audit_raw_files


# ─────────────────────────────────────────────────────────────────────
# Routing decision dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Auto-routing recommendation for a batch of raw clips."""
    # Layout
    layout: str  # "portrait" / "landscape" / "mixed"
    portrait_pct: float = 0.0  # % of clips that are portrait
    landscape_pct: float = 0.0

    # Content type (heuristic)
    content_type: str = "unknown"  # "vlog" / "teaching" / "diy" / "reflective" / "mixed"
    content_confidence: float = 0.0  # 0.0-1.0

    # Pipeline recommendation
    recommended_path: str = "Path E (ffmpeg-only)"  # one of A-E
    recommended_path_reason: str = ""

    # Asset recommendations
    recommended_bgm: Optional[str] = None  # scene FOLDER in assets/bgm/ (2026-07-24 r3 資料夾制), e.g. "旅遊/"
    recommended_preset_family: str = "portrait"  # "portrait" / "landscape"

    # Stats
    total_clips: int = 0
    total_duration_sec: float = 0.0
    date_range: list[str] = field(default_factory=list)
    has_gps: bool = False
    cameras: list[str] = field(default_factory=list)

    # Flags
    needs_hdr_tonemap: bool = False
    needs_audio_strip: bool = False  # B-roll has audio that should be stripped (旅遊 default)
    warnings: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Auto-routing logic
# ─────────────────────────────────────────────────────────────────────

def detect_layout(audits: list[ClipAudit]) -> tuple[str, float, float]:
    """Detect layout based on clip orientation.

    Returns: (layout_str, portrait_pct, landscape_pct)
        layout_str: "portrait" (>70% portrait) / "landscape" (>70% landscape) / "mixed"
    """
    if not audits:
        return "unknown", 0.0, 0.0
    portrait_count = sum(1 for a in audits if a.is_portrait)
    landscape_count = len(audits) - portrait_count
    p_pct = portrait_count / len(audits)
    l_pct = landscape_count / len(audits)

    if p_pct >= 0.7:
        return "portrait", p_pct, l_pct
    elif l_pct >= 0.7:
        return "landscape", p_pct, l_pct
    return "mixed", p_pct, l_pct


def detect_content_type(audits: list[ClipAudit], hint_dir: Path = None) -> tuple[str, float]:
    """Heuristic content type detection.

    Signals (cumulative score):
      - Dir/filename keywords：「旅遊」「馬來西亞」「Vlog」「教學」「DIY」 etc.
      - GPS coverage：>50% with GPS → travel vlog
      - Duration distribution：mean <8s + many clips → vlog / mean >30s + few clips → teaching
      - Camera：iPhone → personal vlog likely / non-iPhone → could be teaching screencast
      - Audio：has audio + high bitrate → talking-head, low bitrate → B-roll
      - Dates：1-2 day span → trip / event；scattered → ongoing project

    Returns: (content_type, confidence 0-1)
    """
    if not audits:
        return "unknown", 0.0

    scores = Counter()

    # Signal 1: directory name keywords
    if hint_dir:
        d_str = str(hint_dir).lower()
        keywords = {
            "vlog": ["馬來西亞", "日本", "vlog", "旅遊", "travel", "trip", "出差", "假期"],
            "teaching": ["教學", "tutorial", "demo", "claude", "ai-tools", "course"],
            "diy": ["diy", "開箱", "unbox", "review", "手作"],
            "reflective": ["心得", "分享", "反思", "reflective", "經驗"],
        }
        for ctype, kws in keywords.items():
            if any(kw in d_str for kw in kws):
                scores[ctype] += 3

    # Signal 2: GPS coverage (high = travel vlog likely)
    gps_pct = sum(1 for a in audits if a.has_gps) / len(audits)
    if gps_pct > 0.5:
        scores["vlog"] += 2

    # Signal 3: Duration distribution
    avg_dur = sum(a.duration_sec for a in audits) / len(audits)
    if avg_dur < 8:
        scores["vlog"] += 1  # short B-roll clips typical
    elif avg_dur > 30:
        scores["teaching"] += 1  # long-form talking head likely

    # Signal 4: Date span
    dates = {a.creation_date_local for a in audits if a.creation_date_local}
    if 1 <= len(dates) <= 3:
        scores["vlog"] += 1  # event/trip
    elif len(dates) > 5:
        scores["teaching"] += 1  # ongoing recording sessions

    # Signal 5: Audio characteristics
    has_audio_count = sum(1 for a in audits if a.audio_codec)
    audio_pct = has_audio_count / len(audits) if audits else 0
    if audio_pct > 0.8:
        # Most clips have audio — could be teaching or just iPhone with mic
        # High bitrate audio (>200k) suggests intentional recording
        high_quality_audio = sum(1 for a in audits if (a.audio_bitrate_kbps or 0) > 200)
        if high_quality_audio / len(audits) > 0.5:
            scores["teaching"] += 1

    # Determine winner
    if not scores:
        return "unknown", 0.0
    winner, top_score = scores.most_common(1)[0]
    total = sum(scores.values())
    confidence = top_score / total if total > 0 else 0
    return winner, confidence


def recommend_path(audits: list[ClipAudit], content_type: str, layout: str) -> tuple[str, str]:
    """Recommend the canonical Editkin v4 durable workflow for every content type.

    Editorial intent is emitted as ``hao.video-autopilot.edit-plan/v4`` commands.
    ``workflow_contract.py`` binds sources, audits the plan, applies it atomically,
    renders, and records matching apply/render/human-review receipts.  ffmpeg may
    still be used by bounded media-preparation and delivery-QA helpers, never as
    an untracked substitute for the editable project.

    Returns: (path_label, reason)
    """
    n = len(audits)
    if n == 0:
        return "N/A", "No clips"
    total_dur = sum(a.duration_sec for a in audits)

    # Universal Editkin v4 path; content_type only varies editorial intent.
    sub_flows = {
        "teaching": "教學長片 — 雙語字幕、螢幕示範、章節與證據鏡頭均寫入 v4 plan",
        "vlog": "Vlog — caption、節奏、地點卡與花字 opt-in 均寫入 v4 plan",
        "food": "食記 — 菜品對位、店家資訊 outro 與原聲節點均寫入 v4 plan",
        "diy": "DIY — 步驟、close-up 與安全提示均寫入 v4 plan",
        "reflective": "Reflective — 留白、J/L cut 與克制字卡均寫入 v4 plan",
    }
    sub = sub_flows.get(content_type, f"{content_type or 'unknown'} — generic Editkin v4 plan")

    return (
        "Path Editkin-v4",
        f"{n} clips / {total_dur:.0f}s — {sub}; audit → atomic apply → render → receipts"
    )


def recommend_bgm(content_type: str) -> Optional[str]:
    """Map content_type → assets/bgm/ scene FOLDER（2026-07-24 r3 改資料夾制）.

    2026-06-22 起 bgm/ 是場景資料夾制（`場景/主題-NN.wav`），本函數回「資料夾名/」；
    呼叫端在夾內選曲（同場景 -01/-02 變體換著用避免重曲；機器索引 = 各夾 bgm_index.json，
    人類約定 = assets/bgm/README.md）。舊版回單一檔名（教學-01.mp3 平面制）已淘汰——
    那批 2026-05 mp3 已搬 _通用/ 當 fallback。
    """
    return recommend_bgm_scene(content_type or "general") + "/"


# 🆕 M59 v2 (2026-05-25): basic preset 是所有 content type 預設，花字 only opt-in
def should_use_flower_text(content_type: str = None, user_explicit: bool = False) -> bool:
    """M59 v2 (2026-05-25 用戶簡化): basic preset is universal default.

    花字 ONLY when user_explicit=True (user 明說「我要花字」).
    教學 / 旅遊 / Demo / DIY 統一 default basic preset Huninn（繁中全字集）。

    Args:
        content_type: 留參數 backward compat (現已不參與決策)
        user_explicit: True 只在用戶 explicit 要求花字時

    Returns: True only if user_explicit=True.
    """
    return user_explicit


def recommend_caption_style(content_type: str = None, layout: str = "portrait",
                           user_wants_flower: bool = False) -> dict:
    """Decide caption style. M59 v2 — all content_type default basic preset; flower opt-in only.

    Returns: {
        "use_flower_text": bool,
        "preset_name": str,
        "font": str,  # project-owned font family
        "y_position": str,  # ffmpeg expr — 'h-200' (landscape lower-third) / '380' (portrait upper)
        "size_hint": int,
    }
    """
    if layout == "landscape":
        y_pos = "h-200"
        size = 56
    else:
        y_pos = "380"
        size = 56

    return {
        "use_flower_text": user_wants_flower,  # only True if user explicit
        "preset_name": "white_outline_with_box",  # basic preset 全 type 通用
        "font": "Huninn",  # project-owned, Traditional-Chinese-safe
        "font_asset": "assets/fonts/_active/Huninn-Regular.ttf",
        "y_position": y_pos,
        "size_hint": size,
        "note": "Editkin v4 command 可調字體/位置/色彩；變更必進 plan 並產生新 receipt",
    }


def route_content(raw_dir: Path, tz_offset_hours: int = 8, audits: list = None) -> RoutingDecision:
    """One-shot: audit raw → return RoutingDecision.

    Usage:
        decision = route_content(Path("videos/current/raw/<topic>/"))
        print(f"Type: {decision.content_type} (conf {decision.content_confidence:.0%})")
        print(f"Layout: {decision.layout} ({decision.portrait_pct:.0%} portrait)")
        print(f"Path: {decision.recommended_path}")
        print(f"BGM: {decision.recommended_bgm}")
    """
    # perf (2026-06-10 audit): run_full_audit() 已掃過的 folder 不重 probe —
    # 傳 audits= 進來省 56 次 ffprobe subprocess (workflow: route_content(raw_dir, audits=result["audits"]))
    if audits is None:
        audits = audit_raw_files(raw_dir, tz_offset_hours=tz_offset_hours)
    if not audits:
        return RoutingDecision(
            layout="unknown",
            content_type="unknown",
            warnings=["No clips found in raw_dir"],
        )

    layout, p_pct, l_pct = detect_layout(audits)
    content_type, confidence = detect_content_type(audits, hint_dir=raw_dir)
    path_label, path_reason = recommend_path(audits, content_type, layout)
    bgm = recommend_bgm(content_type)

    # Layout → preset family
    preset_family = "landscape" if layout == "landscape" else "portrait"

    # Warnings
    warnings = []
    any_hdr = any(a.is_hdr for a in audits)
    if any_hdr:
        warnings.append("⚠️ HDR detected — must apply R10 tonemap (TONEMAP_FILTER) in ffmpeg pipeline")
    if layout == "mixed":
        warnings.append(f"⚠️ Mixed orientation ({p_pct:.0%}p / {l_pct:.0%}l) — pick one layout or split into 2 projects")
    if content_type == "unknown" or confidence < 0.3:
        warnings.append(f"⚠️ Content type uncertain ({content_type} conf {confidence:.0%}) — manually confirm")

    return RoutingDecision(
        layout=layout,
        portrait_pct=p_pct,
        landscape_pct=l_pct,
        content_type=content_type,
        content_confidence=confidence,
        recommended_path=path_label,
        recommended_path_reason=path_reason,
        recommended_bgm=bgm,
        recommended_preset_family=preset_family,
        total_clips=len(audits),
        total_duration_sec=sum(a.duration_sec for a in audits),
        date_range=sorted({a.creation_date_local for a in audits if a.creation_date_local}),
        has_gps=any(a.has_gps for a in audits),
        cameras=sorted({a.camera_model for a in audits if a.camera_model}),
        needs_hdr_tonemap=any_hdr,
        needs_audio_strip=(content_type == "vlog"),  # 旅遊 B-roll 預設 strip audio (M29)
        warnings=warnings,
    )


def print_routing_decision(d: RoutingDecision) -> None:
    """Print human-readable routing decision."""
    print("=" * 70)
    print("🛣️  Content Routing Decision")
    print("=" * 70)
    print(f"Total clips: {d.total_clips} / {d.total_duration_sec:.0f}s ({d.total_duration_sec / 60:.1f} min)")
    print(f"Date range: {', '.join(d.date_range)}")
    print(f"Cameras: {', '.join(d.cameras) if d.cameras else 'unknown'}")
    print()
    print(f"📐 Layout: {d.layout}  ({d.portrait_pct:.0%} portrait / {d.landscape_pct:.0%} landscape)")
    print(f"📊 Content type: {d.content_type}  (confidence {d.content_confidence:.0%})")
    print(f"🛤️  Recommended path: {d.recommended_path}")
    print(f"   Reason: {d.recommended_path_reason}")
    print(f"🎵 Recommended BGM folder: assets/bgm/{d.recommended_bgm}")
    print(f"🎨 Preset family: {d.recommended_preset_family}")
    print()
    print(f"Flags:")
    print(f"  HDR tonemap needed: {'YES' if d.needs_hdr_tonemap else 'no'}")
    print(f"  Audio strip needed: {'YES (B-roll)' if d.needs_audio_strip else 'no'}")
    print(f"  GPS available: {'YES' if d.has_gps else 'no'}")
    if d.warnings:
        print()
        print("Warnings:")
        for w in d.warnings:
            print(f"  {w}")


# ── minimal self-test（2026-07-24 r3；跑法：python -m silent_vlog_maker.routing）──
def _selftest() -> int:
    """recommend_bgm 資料夾制 self-test：映射正確 + 資料夾真的存在。console ASCII only."""
    fails = []

    def check(name, ok):
        print(("[PASS] " if ok else "[FAIL] ") + name)
        if not ok:
            fails.append(name)

    check("vlog -> travel folder", recommend_bgm("vlog") == "旅遊/")
    check("teaching -> teaching folder", recommend_bgm("teaching") == "教學/")
    check("unknown -> fallback", recommend_bgm("unknown") == "_通用/")
    check("unmapped type -> fallback", recommend_bgm("whatever") == "_通用/")
    bgm_root = asset_path("bgm")
    if bgm_root.is_dir():
        for ct in ("vlog", "teaching", "food", "diy", "unknown"):
            folder = bgm_root / recommend_bgm(ct).rstrip("/")
            check("folder exists for %s" % ct, folder.is_dir())
    else:
        print("[SKIP] assets/bgm not found - folder existence checks skipped")
    print("selftest:", "OK" if not fails else "FAILED %d" % len(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
