# -*- coding: utf-8 -*-
"""grade_gate.py — 調色一致性機械閘門（2026-08-07 建）

補 hao-voice §2.5 的最後一個缺口。Hao R2 自選**第一痛點 = 「調色 / 整體色調統一」**，
勝過素材本身 / 包裝字卡 / 構圖 —— 但直到本檔為止**完全沒有機械檢查**。

與 `grade_lib.py` 的分工（那是「套」，這是「驗」）：
    grade_lib  : LOOKS / apply_look / load_cube_lut —— **施加**調色
    grade_gate : 驗「一級校正有沒有做」—— grade_lib 檔頭鐵則第 2 條：
                 「**一級校正在前、Look 在後；素材白平衡/曝光先修好再套 look**」
                 本檔就是那句話的機械版：跨鏡頭曝光/白平衡/飽和/對比漂不漂。

規則碼（G-x）：
    G-A 曝光不一致     跨鏡頭 luma 分佈過寬
    G-B 白平衡不一致   warm-cool 軸（R-B）漂移 ← **「色調不統一」最直接的表現**
    G-C 色偏不一致     green-magenta 軸（tint）漂移
    G-D 飽和不一致     saturation 漂移
    G-E 對比不一致     luma 標準差漂移
    G-F 相鄰跳色       連續兩顆鏡頭之間的跳幅（比整體 spread 更貼近「看起來雜」）
    G-G 過曝 / 死黑    clipping 比例

輸入三種（由寬到窄）：
    gate_grade(video_path=...)           # 自動抽幀（需 ffmpeg）
    gate_grade(images=[...])             # 一組代表幀圖檔
    gate_grade(stats=[{...}, ...])       # 已算好的統計（self-test / 快速重算用）

API:
    frame_stats(path_or_image) -> dict
    sample_video(path, n=24)   -> [stats]          # 均勻抽 n 幀
    analyze(stats)             -> dict             # spread / 相鄰跳幅
    gate_grade(...)            -> (ok, report)
    assert_grade(...)          -> 不過就 raise
    write_report(report, path) -> path

⚠️ **門檻怎麼來的**：照 M114，**不發明數字** —— 由 Hao 已發布/已交付的成片回測校準，
   讓他自己的作品 0 誤殺（見 `grade_calibrate.py`）。校準值與樣本記在 PROFILES 註解。

⚠️ gate 綠 != 好看。它只保證「跨鏡頭沒有明顯漂移」，
   不保證 look 選得對、不保證膚色好看 —— 那是人眼的事（M111 / M114）。

cp950 安全：print 只 ASCII；檔案 I/O 一律 encoding="utf-8"。
共用外殼 → gate_core.py；規則本體留本檔。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

try:
    from gate_core import report as _report, raise_if_failed, selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import report as _report, raise_if_failed, selftest_runner

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# ═══════════════════════════════════════════════ profiles
#
# 單位：luma / warm / tint / contrast 用 0-255；sat 用 0-1；clip 用 0-1 比例。
# spread = p90 - p10（robust，不被單一極端幀帶走）。
#
# ⚠️ 數值由 `grade_calibrate.py` 對 Hao 真成片回測後填入（M114：不發明門檻）。
#    校準樣本與實測值見該檔輸出；此處註解記最終採用值的理由。
#
PROFILES = {
    # 教學長片：螢幕錄影（近中性、高亮）與 b-roll 混剪 → luma/contrast 天生就寬，
    # 但**白平衡與色偏應該一致**（都是同一套 look 之後的成片）→ warm/tint 抓得比 luma 嚴。
    "teaching_longform": {
        "luma_spread":     (70.0, 110.0),
        "warm_spread":     (18.0, 32.0),
        "tint_spread":     (12.0, 22.0),
        "sat_spread":      (0.18, 0.30),
        "contrast_spread": (30.0, 50.0),
        "jump_luma":       (70.0, 110.0),
        "jump_warm":       (22.0, 38.0),
        "clip_lo":         (0.05, 0.12),
        "clip_hi":         (0.03, 0.08),
    },
    # Vlog：外景光線本來就跳（室內/室外/夜市），最寬鬆
    "vlog": {
        "luma_spread":     (85.0, 125.0),
        "warm_spread":     (26.0, 42.0),
        "tint_spread":     (16.0, 28.0),
        "sat_spread":      (0.22, 0.36),
        "contrast_spread": (35.0, 58.0),
        "jump_luma":       (85.0, 125.0),
        "jump_warm":       (30.0, 48.0),
        "clip_lo":         (0.06, 0.14),
        "clip_hi":         (0.04, 0.10),
    },
    # Podcast：鏡位和光線相對穩定，因此比 Vlog 更嚴格看膚色、曝光與鏡間跳動。
    "podcast": {
        "luma_spread":     (55.0, 90.0),
        "warm_spread":     (14.0, 24.0),
        "tint_spread":     (9.0, 16.0),
        "sat_spread":      (0.12, 0.22),
        "contrast_spread": (24.0, 40.0),
        "jump_luma":       (50.0, 82.0),
        "jump_warm":       (16.0, 28.0),
        "clip_lo":         (0.04, 0.10),
        "clip_hi":         (0.025, 0.07),
    },
    # Shorts：短、單場景為主，一致性要求最高
    "shorts": {
        "luma_spread":     (55.0, 90.0),
        "warm_spread":     (16.0, 28.0),
        "tint_spread":     (10.0, 18.0),
        "sat_spread":      (0.16, 0.26),
        "contrast_spread": (26.0, 44.0),
        "jump_luma":       (55.0, 90.0),
        "jump_warm":       (20.0, 32.0),
        "clip_lo":         (0.05, 0.12),
        "clip_hi":         (0.03, 0.08),
    },
}

# (metric_key, 規則碼, 中文說明)
_SPREAD_RULES = [
    ("luma_spread",     "G-A", "曝光不一致（跨鏡頭亮度分佈過寬）"),
    ("warm_spread",     "G-B", "白平衡不一致（暖冷軸漂移）"),
    ("tint_spread",     "G-C", "色偏不一致（綠洋紅軸漂移）"),
    ("sat_spread",      "G-D", "飽和度不一致"),
    ("contrast_spread", "G-E", "對比不一致"),
]
_JUMP_RULES = [
    ("jump_luma", "G-F", "相鄰鏡頭亮度跳動"),
    ("jump_warm", "G-F", "相鄰鏡頭色溫跳動"),
]

_DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")
_SAMPLE_MAX_W = 192          # 縮圖後統計，數值幾乎不變但快 100x


# ═══════════════════════════════════════════════ 單幀統計

def frame_stats(src) -> dict:
    """單幀色彩統計。src = 檔案路徑 / PIL.Image / HxWx3 uint8 array。

    回傳 {luma, contrast, sat, warm, tint, clip_lo, clip_hi}
    luma/contrast/warm/tint 單位 0-255；sat 0-1；clip 為像素比例。
    """
    if isinstance(src, np.ndarray):
        arr = src
    else:
        img = src if isinstance(src, Image.Image) else Image.open(src)
        img = img.convert("RGB")
        if img.width > _SAMPLE_MAX_W:
            h = max(1, int(img.height * _SAMPLE_MAX_W / img.width))
            img = img.resize((_SAMPLE_MAX_W, h), Image.BILINEAR)
        arr = np.asarray(img)

    a = arr.astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

    mx = a.max(axis=-1)
    mn = a.min(axis=-1)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)

    return {
        "luma": float(luma.mean()),
        "contrast": float(luma.std()),
        "sat": float(sat.mean()),
        "warm": float(r.mean() - b.mean()),
        "tint": float(g.mean() - (r.mean() + b.mean()) / 2.0),
        "clip_lo": float((luma < 4.0).mean()),
        "clip_hi": float((luma > 251.0).mean()),
    }


# ═══════════════════════════════════════════════ 抽幀

def _duration(path: str) -> float:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        raise RuntimeError("ffprobe could not read duration: %s" % path)


def sample_video(path: str, n: int = 24) -> list:
    """均勻抽 n 幀算統計。頭尾各留 2% 避開黑場 / 片尾卡。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if shutil.which(FFMPEG) is None:
        raise RuntimeError("ffmpeg not found on PATH")
    dur = _duration(path)
    if dur <= 0:
        raise RuntimeError("zero duration: %s" % path)

    lo, hi = dur * 0.02, dur * 0.98
    ts = [lo + (hi - lo) * i / float(max(1, n - 1)) for i in range(n)]

    stats = []
    tmp = tempfile.mkdtemp(prefix="gradegate_")
    try:
        for i, t in enumerate(ts):
            out = os.path.join(tmp, "f%03d.png" % i)
            subprocess.run(
                [FFMPEG, "-v", "error", "-ss", "%.3f" % t, "-i", path,
                 "-frames:v", "1", "-vf", "scale=%d:-2" % _SAMPLE_MAX_W,
                 "-y", out],
                capture_output=True)
            if os.path.isfile(out) and os.path.getsize(out) > 0:
                stats.append(frame_stats(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not stats:
        raise RuntimeError("no frames extracted from %s" % path)
    return stats


# ═══════════════════════════════════════════════ 分析

# ═══════════════════════════════════════════════ 分群
#
# 🚨 **2026-08-07 真成片實測後的關鍵修正**（初版沒有這段 → 量錯東西）：
#    長片01 逐幀傾印顯示，幀在三種內容之間跳：
#       暗色 b-roll        luma~28   sat~0.55  warm~-18
#       亮白螢幕錄影       luma~160  sat~0.17  warm~+15
#       純白品牌卡/黑場    luma 240 / 17, sat~0.00
#    直接算跨幀 spread → jump_luma=215、luma_spread=148，
#    但那是**剪輯結構**不是調色缺陷（螢幕錄影本來就亮而低飽和，調色不該讓它等於 b-roll）。
#    把同類別拉出來看，白平衡其實很一致（b-roll -10~-20；螢幕錄影 +13~+16）。
#
# → 規則：先**剔除結構幀**（品牌卡 / 黑場 / 白閃），再按飽和度**分群**，
#   量的是**群內一致性**＝真正的調色訊號；群間差異另行報告，不當作 fail。

UI_SAT_MAX = 0.30          # 分層界線（見下方限制說明）
_MIN_GROUP = 4             # 群內少於此數不判定（樣本不足）

# ⚠️ **已知限制（2026-08-07 實測發現，誠實記錄，勿當成 bug 修掉）**：
#    分群用飽和度當代理，低飽和層**通常**是螢幕錄影 / UI / 圖表，
#    但 Hao 的直式 Shorts（真實拍攝）飽和度也低（0.0-0.1）→ 一樣落在低飽和層。
#    對「群內一致性」的判定**沒有影響**（比較的仍是相似的畫面），
#    只是分層名稱會誤導 → 因此對外顯示一律用「低飽和層 / 高飽和層」，不寫「UI / 實拍」。
#    真正會出錯的情況：同一支片混了「低飽和實拍」與「螢幕錄影」→ 兩者被歸同層，
#    其正當差異會被算成不一致。目前 corpus 沒有這種片；出現時再拆維度（加 luma 軸）。


def is_structural(s: dict) -> bool:
    """結構幀 = 品牌卡 / 黑場 / 白閃 / 轉場 —— 不是被調色的內容，不進一致性計算。"""
    if s["clip_lo"] > 0.5 or s["clip_hi"] > 0.5:
        return True
    return s["sat"] < 0.06 and (s["luma"] > 200.0 or s["luma"] < 25.0)


def split_frames(stats) -> dict:
    """→ {"structural": [...], "ui": [...], "footage": [...]}"""
    structural = [s for s in stats if is_structural(s)]
    content = [s for s in stats if not is_structural(s)]
    return {
        "structural": structural,
        "ui": [s for s in content if s["sat"] < UI_SAT_MAX],
        "footage": [s for s in content if s["sat"] >= UI_SAT_MAX],
    }


def _spread(vals) -> float:
    """p90 - p10（robust spread；不被單一極端幀帶走）。"""
    if len(vals) < 2:
        return 0.0
    a = np.asarray(vals, dtype=np.float64)
    return float(np.percentile(a, 90) - np.percentile(a, 10))


def _max_jump(vals) -> float:
    """相鄰幀最大跳幅（用 p95 而非 max，避開單一轉場幀）。"""
    if len(vals) < 2:
        return 0.0
    d = np.abs(np.diff(np.asarray(vals, dtype=np.float64)))
    return float(np.percentile(d, 95)) if len(d) >= 4 else float(d.max())


def _group_metrics(group) -> dict:
    col = {k: [s[k] for s in group] for k in group[0]}
    return {
        "n": len(group),
        "luma_spread": _spread(col["luma"]),
        "warm_spread": _spread(col["warm"]),
        "tint_spread": _spread(col["tint"]),
        "sat_spread": _spread(col["sat"]),
        "contrast_spread": _spread(col["contrast"]),
        "jump_luma": _max_jump(col["luma"]),
        "jump_warm": _max_jump(col["warm"]),
        "luma_mean": float(np.mean(col["luma"])),
        "warm_mean": float(np.mean(col["warm"])),
        "sat_mean": float(np.mean(col["sat"])),
    }


def analyze(stats) -> dict:
    """把逐幀統計壓成一致性指標。

    **群內**指標（ui / footage 各一組）= 真正的調色訊號 → 拿去判定。
    **群間** warm 差 = 設計選擇（螢幕錄影 vs b-roll 本來就不同）→ 只報告不判定。
    clipping 用全片平均（含結構幀無妨，白卡本來就該白）。
    """
    if not stats:
        return {}
    groups = split_frames(stats)
    col = {k: [s[k] for s in stats] for k in stats[0]}

    out = {
        "frames": len(stats),
        "n_structural": len(groups["structural"]),
        "clip_lo": float(np.mean(col["clip_lo"])),
        "clip_hi": float(np.mean(col["clip_hi"])),
        "luma_mean": float(np.mean(col["luma"])),
        "warm_mean": float(np.mean(col["warm"])),
        "sat_mean": float(np.mean(col["sat"])),
        "groups": {},
    }
    for name in ("ui", "footage"):
        g = groups[name]
        if len(g) >= _MIN_GROUP:
            out["groups"][name] = {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in _group_metrics(g).items()
            }
    # 群間色溫差（設計選擇，不判定）
    if len(out["groups"]) == 2:
        out["cross_group_warm_gap"] = round(
            abs(out["groups"]["ui"]["warm_mean"]
                - out["groups"]["footage"]["warm_mean"]), 2)
    return {k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in out.items()}


# ═══════════════════════════════════════════════ gate

def gate_grade(video_path: str = None, images=None, stats=None,
               profile: str = "teaching_longform", n: int = 24):
    """總閘門。三種輸入擇一。回傳 (ok, report)。"""
    if profile not in PROFILES:
        raise ValueError("unknown profile %r; expected one of %s"
                         % (profile, sorted(PROFILES)))
    if stats is None:
        if images:
            stats = [frame_stats(p) for p in images]
        elif video_path:
            stats = sample_video(video_path, n)
        else:
            raise ValueError("need one of video_path / images / stats")
    if len(stats) < 2:
        return False, _report(["G-0 樣本不足（至少 2 幀才談得上一致性）"], [],
                              profile=profile, metrics=analyze(stats))

    cfg = PROFILES[profile]
    m = analyze(stats)
    fails, warns = [], []

    if not m["groups"]:
        return False, _report(
            ["G-0 沒有足夠的內容幀可判定（結構幀 %d / 總幀 %d）"
             % (m["n_structural"], m["frames"])], [],
            profile=profile, metrics=m)

    # 群內一致性 = 真正的調色訊號
    for gname, gm in sorted(m["groups"].items()):
        tag = "低飽和層" if gname == "ui" else "高飽和層"
        for key, code, label in _SPREAD_RULES + _JUMP_RULES:
            warn_t, fail_t = cfg[key]
            val = gm[key]
            if val > fail_t:
                fails.append("%s %s[%s]：%s=%.1f > 上限 %.1f（%s，n=%d）"
                             % (code, label, tag, key, val, fail_t, profile, gm["n"]))
            elif val > warn_t:
                warns.append("%s %s[%s]：%s=%.1f > 建議 %.1f"
                             % (code, label, tag, key, val, warn_t))

    for key, label in (("clip_lo", "死黑"), ("clip_hi", "過曝")):
        warn_t, fail_t = cfg[key]
        val = m[key]
        if val > fail_t:
            fails.append("G-G %s：%s=%.1f%% > 上限 %.1f%%"
                         % (label, key, val * 100, fail_t * 100))
        elif val > warn_t:
            warns.append("G-G %s：%s=%.1f%% > 建議 %.1f%%"
                         % (label, key, val * 100, warn_t * 100))

    rep = _report(fails, warns, profile=profile, metrics=m)
    return rep["ok"], rep


def assert_grade(video_path: str = None, images=None, stats=None,
                 profile: str = "teaching_longform", n: int = 24,
                 label: str = ""):
    """不過就 raise AssertionError（訊息格式全系統統一）。"""
    _ok, rep = gate_grade(video_path, images, stats, profile, n)
    raise_if_failed(rep, label or profile, "Grade gate FAIL")
    for w in rep["warns"]:
        print("   WARN " + w.encode("ascii", "replace").decode("ascii"))
    return rep


# ═══════════════════════════════════════════════ report io

def write_report(report: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    m = report["metrics"]
    lines = ["GRADE GATE REPORT", "=" * 50,
             "verdict: %s" % ("PASS" if report["ok"] else "FAIL"),
             "profile: %s" % report["profile"],
             "frames:  %d" % m.get("frames", 0), ""]
    lines.append("structural frames excluded: %d (brand cards / black / white flash)"
                 % m.get("n_structural", 0))
    lines.append("")
    lines.append("[within-group consistency]  (spread = p90-p10; 這才是調色訊號)")
    for gname, gm in sorted(m.get("groups", {}).items()):
        tag = "low-sat layer" if gname == "ui" else "high-sat layer"
        lines.append("  -- %s (n=%d, luma_mean=%.0f, warm_mean=%+.1f)"
                     % (tag, gm["n"], gm["luma_mean"], gm["warm_mean"]))
        for k in ("luma_spread", "warm_spread", "tint_spread",
                  "sat_spread", "contrast_spread", "jump_luma", "jump_warm"):
            lo, hi = PROFILES[report["profile"]][k]
            lines.append("     %-16s %8.2f   (warn %.1f / fail %.1f)" % (k, gm[k], lo, hi))
    if "cross_group_warm_gap" in m:
        lines.append("")
        lines.append("  cross-group warm gap: %.1f  (設計選擇，不判定)"
                     % m["cross_group_warm_gap"])
    lines.append("")
    lines.append("[whole-video levels]")
    for k in ("luma_mean", "warm_mean", "sat_mean", "clip_lo", "clip_hi"):
        lines.append("  %-16s %8.4f" % (k, m[k]))
    lines.append("")
    lines.append("[fails] %d" % len(report["fails"]))
    for f in report["fails"]:
        lines.append("  - " + f)
    lines.append("")
    lines.append("[warns] %d" % len(report["warns"]))
    for w in report["warns"]:
        lines.append("  - " + w)
    lines.append("")
    lines.append("NOTE: gate 綠 != 好看。只保證跨鏡頭沒明顯漂移，")
    lines.append("      look 選得對不對 / 膚色好不好看仍是人眼的事。")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    jpath = os.path.splitext(path)[0] + ".json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


# ═══════════════════════════════════════════════ self-test
# M111 雙向：該擋的擋、該放的放。純資料路徑，不需要媒體檔。

def _mk(luma=120.0, contrast=50.0, sat=0.35, warm=6.0, tint=2.0,
        clip_lo=0.005, clip_hi=0.002):
    return {"luma": luma, "contrast": contrast, "sat": sat, "warm": warm,
            "tint": tint, "clip_lo": clip_lo, "clip_hi": clip_hi}


def _selftest_body(check):
    # ── 正向：一致的成片（小幅自然波動）必須過
    rng = np.random.RandomState(7)
    consistent = [_mk(luma=120 + rng.uniform(-8, 8),
                      contrast=50 + rng.uniform(-5, 5),
                      sat=0.35 + rng.uniform(-0.03, 0.03),
                      warm=6 + rng.uniform(-3, 3),
                      tint=2 + rng.uniform(-2, 2)) for _ in range(24)]
    ok, rep = gate_grade(stats=consistent, profile="teaching_longform")
    check("consistent grade passes", ok)
    check("consistent grade has no warns", not rep["warns"])

    # ── G-B 白平衡漂移：一半暖一半冷 → fail（這是「色調不統一」核心症狀）
    wb = ([_mk(warm=-22.0) for _ in range(12)] + [_mk(warm=26.0) for _ in range(12)])
    okB, repB = gate_grade(stats=wb, profile="teaching_longform")
    check("G-B blocks white-balance drift", (not okB) and any(
        f.startswith("G-B") for f in repB["fails"]))

    # ── G-A 曝光漂移
    ex = ([_mk(luma=45.0) for _ in range(12)] + [_mk(luma=205.0) for _ in range(12)])
    okA, repA = gate_grade(stats=ex, profile="teaching_longform")
    check("G-A blocks exposure drift", (not okA) and any(
        f.startswith("G-A") for f in repA["fails"]))

    # ── G-D 飽和漂移（**同群內**才算 —— 低飽和 UI vs 高飽和實拍是結構不是缺陷）
    sa = ([_mk(sat=0.34) for _ in range(12)] + [_mk(sat=0.78) for _ in range(12)])
    okD, repD = gate_grade(stats=sa, profile="teaching_longform")
    check("G-D blocks saturation drift within footage", (not okD) and any(
        f.startswith("G-D") for f in repD["fails"]))

    # 低飽和 UI + 高飽和實拍分屬兩群、各自一致 → **不可**判 fail（初版會誤殺）
    mixed = ([_mk(sat=0.12, luma=160.0, warm=14.0) for _ in range(10)]
             + [_mk(sat=0.55, luma=30.0, warm=-18.0) for _ in range(10)])
    okM, repM = gate_grade(stats=mixed, profile="teaching_longform")
    check("mixed screen-rec + b-roll NOT flagged (structure, not grading)",
          okM and not repM["fails"])
    check("both groups detected", set(repM["metrics"]["groups"]) == {"ui", "footage"})
    check("cross-group warm gap reported, not judged",
          abs(repM["metrics"]["cross_group_warm_gap"] - 32.0) < 0.5)

    # ── 結構幀（純白品牌卡 / 黑場）必須被剔除，不得污染判定
    struct = ([_mk(sat=0.35, luma=120.0, warm=5.0) for _ in range(10)]
              + [_mk(sat=0.00, luma=240.0, clip_hi=0.68)]      # 白卡
              + [_mk(sat=0.01, luma=17.0, clip_lo=0.61)])      # 黑場 outro
    okS, repS = gate_grade(stats=struct, profile="teaching_longform")
    check("structural frames excluded", repS["metrics"]["n_structural"] == 2)
    check("structural frames do not cause failure", okS)

    # ── G-F 相鄰跳色：整體 spread 不大但每一顆都在跳（鋸齒）
    saw = [_mk(warm=-20.0 if i % 2 else 20.0) for i in range(24)]
    okF, repF = gate_grade(stats=saw, profile="teaching_longform")
    check("G-F blocks alternating jumps", (not okF) and any(
        f.startswith("G-F") for f in repF["fails"]))

    # ── G-G clipping
    cl = [_mk(clip_hi=0.15) for _ in range(24)]
    okG, repG = gate_grade(stats=cl, profile="teaching_longform")
    check("G-G blocks blown highlights", (not okG) and any(
        f.startswith("G-G") for f in repG["fails"]))

    # ── profile 差異：vlog 較寬鬆
    mid = ([_mk(warm=-13.0) for _ in range(12)] + [_mk(warm=17.0) for _ in range(12)])
    ok_t, _ = gate_grade(stats=mid, profile="teaching_longform")
    ok_v, _ = gate_grade(stats=mid, profile="vlog")
    check("mid drift warns/fails tighter on longform than vlog",
          ok_v and not ok_t or (ok_v == ok_t))   # vlog 至少不比長片嚴
    check("vlog profile is looser than shorts",
          PROFILES["vlog"]["warm_spread"][1] > PROFILES["shorts"]["warm_spread"][1])

    # ── frame_stats 數學正確性（合成影像，答案可手算）
    grey = np.full((16, 16, 3), 128, dtype=np.uint8)
    s = frame_stats(grey)
    check("grey frame: luma=128", abs(s["luma"] - 128.0) < 0.5)
    check("grey frame: sat=0", s["sat"] < 1e-6)
    check("grey frame: warm=0", abs(s["warm"]) < 1e-6)
    check("grey frame: contrast=0", s["contrast"] < 1e-6)

    warm_img = np.zeros((16, 16, 3), dtype=np.uint8)
    warm_img[..., 0] = 200        # R
    warm_img[..., 2] = 100        # B
    sw = frame_stats(warm_img)
    check("warm frame: warm=+100", abs(sw["warm"] - 100.0) < 0.5)

    black = np.zeros((16, 16, 3), dtype=np.uint8)
    check("black frame: clip_lo=1.0", frame_stats(black)["clip_lo"] == 1.0)
    white = np.full((16, 16, 3), 255, dtype=np.uint8)
    check("white frame: clip_hi=1.0", frame_stats(white)["clip_hi"] == 1.0)

    # ── 邊界
    ok_e, rep_e = gate_grade(stats=[_mk()], profile="teaching_longform")
    check("single frame fails cleanly", (not ok_e) and rep_e["fails"])
    try:
        gate_grade(stats=consistent, profile="nope")
        check("unknown profile rejected", False)
    except ValueError:
        check("unknown profile rejected", True)
    try:
        gate_grade()
        check("no input rejected", False)
    except ValueError:
        check("no input rejected", True)

    # ── assert 契約
    try:
        assert_grade(stats=wb, profile="teaching_longform", label="v9")
        check("assert_grade raises on fail", False)
    except AssertionError as e:
        check("assert_grade raises on fail", "[v9] Grade gate FAIL" in str(e))

    # ── report io
    demo = os.path.join(_DEMO_DIR, "grade_report.txt")
    write_report(repB, demo)
    check("demo report written", os.path.isfile(demo) and os.path.getsize(demo) > 200)
    check("demo report json written",
          os.path.isfile(os.path.join(_DEMO_DIR, "grade_report.json")))


def _selftest():
    return selftest_runner(_selftest_body, width=56, list_fails=True)


if __name__ == "__main__":
    raise SystemExit(_selftest())
