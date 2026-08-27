# -*- coding: utf-8 -*-
"""Color-grade calibration runner (public distribution).

Populate ``REGRESSION`` with creator-owned videos that should pass and
``BASELINE`` with videos that are measurement-only.  The public kit deliberately
ships both lists empty: maintainer paths, scores and dated evaluations are not
fixtures for another creator's thresholds.

PUBLIC_FIXTURE: local calibration media are excluded.
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

# 已達標 → 必須 PASS（creator 已經做得到的水準）
REGRESSION = []  # PUBLIC_FIXTURE: add creator-owned approved samples
# 現況追蹤 → 只量不判（這是 §2.5 的 taste-execution gap 本身）
BASELINE = []  # PUBLIC_FIXTURE: add creator-owned measurement samples

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
    print("[baseline] long-form / vlog — 只量測不判定（調色 = creator 自評第一痛點）")
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
        print("  -> 門檻比 creator 已達到的水準還嚴 = 訂錯（M114 rule 1）")
        return 1
    print("REGRESSION GREEN: all %d already-good videos pass" % len(reg_rows))
    print("baseline 區的 warn/fail 是**預期的** — 那是 §2.5 的 taste-execution gap，")
    print("不是 gate 的錯。改善後重跑本檔，數字會往下走。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(measure="--measure" in sys.argv))
