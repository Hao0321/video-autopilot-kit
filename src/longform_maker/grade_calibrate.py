# -*- coding: utf-8 -*-
"""grade_calibrate.py — grade_gate 的真成片量測（2026-08-07 建）

M114 說「self-test 綠不算數，要拿真 corpus 回歸」。但 grade_gate 有一個
**voice_gate 沒有的特殊性**，必須寫死在這裡免得以後有人搞錯：

    voice_gate 的 corpus（36 篇腳本）= **標準** —— Hao 對自己的語感滿意。
    grade_gate 的 corpus（成片調色）= **現況，不是標準** ——
        調色是 Hao **自評第一痛點**（hao-voice §2.5，R2 親選，勝過素材/包裝/構圖）。

→ **絕不可**把門檻調到「他現在的長片剛好通過」。那等於認證他想修的問題，
  並且違反 §2.5「taste-execution gap：分身不得安慰『已經很好了』」。

因此本檔分兩塊：

    [regression]  已達標的作品必須 PASS —— **Shorts**。
                  實測 s18 luma_spread=6.7 / s16=39.2 / s14=26.4，
                  他的直式短影音本來就色調一致 → 這是他**已經做得到**的水準，
                  gate 誤殺它們就是門檻訂錯（M114 rule 1 在此仍適用）。

    [baseline]    長片 / vlog 只**量測不判定** —— 記錄現況供追蹤改善。
                  這裡出現 warn/fail 是**預期的**，那就是他要關的差距。

用法：
    python grade_calibrate.py            # regression（0=綠 / 1=紅）+ baseline 報告
    python grade_calibrate.py --measure  # 只印數值 + 建議門檻
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AUTOPILOT not in sys.path:
    sys.path.insert(0, _AUTOPILOT)
from grade_gate import PROFILES, analyze, gate_grade, sample_video  # noqa: E402
from project_paths import video_path  # noqa: E402

V = str(video_path())

# 已達標 → 必須 PASS（Hao 已經做得到的水準）
REGRESSION = [
    ("shorts", os.path.join(V, r"_planning\Shorts_13-18\s14_longtan.mp4")),
    ("shorts", os.path.join(V, r"_planning\Shorts_13-18\s16_bamboo.mp4")),
    ("shorts", os.path.join(V, r"_planning\Shorts_13-18\s18_longteng.mp4")),
]
# 現況追蹤 → 只量不判（這是 §2.5 的 taste-execution gap 本身）
BASELINE = [
    ("teaching_longform", os.path.join(V, r"_planning\長片01_build\out\長片01_AI工具_v1.mp4")),
    ("teaching_longform", os.path.join(V, r"_planning\長片03_SocialPost\build\out\長片03_SocialPost_初剪.mp4")),
    ("vlog", os.path.join(V, r"_archive\malaysia-vlog\export\claude-90days-studio-v13-FINAL.mp4")),
]

KEYS = ["luma_spread", "warm_spread", "tint_spread", "sat_spread",
        "contrast_spread", "jump_luma", "jump_warm"]
N_FRAMES = 20


def _dims(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True)
    return out.stdout.strip().split("\n")[0]


def _run(profile, path):
    stats = sample_video(path, N_FRAMES)
    ok, rep = gate_grade(stats=stats, profile=profile)
    return analyze(stats), ok, rep


def _show(profile, path, m, ok, rep, judge=True):
    print("%-18s %-36s %s" % (profile, os.path.basename(path)[:36], _dims(path)))
    print("   frames=%d  structural=%d (品牌卡/黑場/白閃，已剔除)"
          % (m["frames"], m["n_structural"]))
    for gname, gm in sorted(m.get("groups", {}).items()):
        tag = "low-sat   " if gname == "ui" else "high-sat  "
        print("   %s n=%2d  luma=%3.0f warm=%+6.1f | %s"
              % (tag, gm["n"], gm["luma_mean"], gm["warm_mean"],
                 "  ".join("%s=%.1f" % (k.replace("_spread", "S")
                                        .replace("jump_", "J"), gm[k])
                           for k in KEYS)))
    if "cross_group_warm_gap" in m:
        print("   cross-group warm gap = %.1f (設計選擇，不判定)"
              % m["cross_group_warm_gap"])
    if judge:
        print("   verdict: %s   fails=%d warns=%d"
              % ("PASS" if ok else "FAIL", len(rep["fails"]), len(rep["warns"])))
    else:
        print("   [baseline only] fails=%d warns=%d  <- 這就是要關的差距"
              % (len(rep["fails"]), len(rep["warns"])))
    for f in rep["fails"]:
        print("      FAIL " + f)
    for w in rep["warns"]:
        print("      warn " + w)
    print("-" * 78)


def main(measure=False) -> int:
    print("=" * 78)
    print("[regression] 已達標作品 — 必須 PASS")
    print("=" * 78)
    reg_rows, bad = [], []
    for profile, path in REGRESSION:
        if not os.path.isfile(path):
            print("  skip (missing): %s" % os.path.basename(path))
            continue
        m, ok, rep = _run(profile, path)
        reg_rows.append((profile, path, m, ok, rep))
        _show(profile, path, m, ok, rep, judge=True)
        if not ok:
            bad.append(os.path.basename(path))

    print()
    print("=" * 78)
    print("[baseline] 長片 / vlog — 只量測不判定（調色 = Hao 自評第一痛點）")
    print("=" * 78)
    for profile, path in BASELINE:
        if not os.path.isfile(path):
            print("  skip (missing): %s" % os.path.basename(path))
            continue
        m, ok, rep = _run(profile, path)
        _show(profile, path, m, ok, rep, judge=False)

    if measure:
        print("\n建議門檻（regression 組實測 max x1.3 = warn, x1.8 = fail）")
        for prof in sorted({r[0] for r in reg_rows}):
            sub = [r[2] for r in reg_rows if r[0] == prof]
            vals = {}
            for s in sub:
                for gm in s.get("groups", {}).values():
                    for k in KEYS:
                        vals.setdefault(k, []).append(gm[k])
            print("\n  %r: {" % prof)
            for k in KEYS:
                mx = max(vals.get(k, [0.0]))
                print("      %-18s (%.1f, %.1f),   # regression max %.2f"
                      % ('"%s":' % k, mx * 1.3, mx * 1.8, mx))
            print("  },")
        return 0

    print()
    if bad:
        print("REGRESSION RED: %d already-good video(s) wrongly flagged: %s"
              % (len(bad), ", ".join(bad)))
        print("  -> 門檻比 Hao 已達到的水準還嚴 = 訂錯（M114 rule 1）")
        return 1
    print("REGRESSION GREEN: all %d already-good videos pass" % len(reg_rows))
    print("baseline 區的 warn/fail 是**預期的** — 那是 §2.5 的 taste-execution gap，")
    print("不是 gate 的錯。改善後重跑本檔，數字會往下走。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(measure="--measure" in sys.argv))
