# -*- coding: utf-8 -*-
"""pace_gate.py — 剪輯層節奏機械閘門（2026-08-07 建）

補的是 hao-voice §2.5 的缺口：Hao 的第一品味軸是「好看 = 動態流暢」，
他 R5 明選四種不流暢**全部受不了**，但其中三種沒有任何機械檢查：

    畫面抖        → 已有 M92（靜止圖禁 zoompan）→ 本檔 D-D 補「plan 層先攔」
    鏡頭停太久    → 無 gate → 本檔 D-A
    節奏斷        → 無 gate（script_gate 的 M110 只管腳本層）→ 本檔 D-B
    轉場生硬      → 無 gate → 本檔 D-C
    每顆等長      → 平均刀速看不出來 → 本檔 D-E

門檻不是發明的，是 Hao 自己三支參考片的實測值（memory `hao_editing_signatures`）：
    v1 OiiOii 22.9 cuts/min (2.6s/shot) | v2 Flow 15.4 (3.9s) | v3 Suno 11.0 (5.5s)
    → 平均 ~16 cuts/min ≈ 3.75s/shot。最慢的 v3 = 11.0 cuts/min 當地板。

輸入 = shot list（任何 pipeline 都產得出的通用結構）：
    [{"dur": 3.2, "trans_in": "cut"|"wipe"|"whip"|"zoom"|None,
      "effect": "zoompan"|None, "label": "b01"}, ...]
只有 "dur" 是必填。

API:
    from_durations([1.2, 3.4, ...])          -> shots      # 只有秒數時的便利建構
    analyze(shots)                            -> stats dict
    gate_pace(shots, profile=...)             -> (ok, report)
    assert_pace(shots, profile=..., label="") -> shots      # 不過就 raise
    write_report(report, path)                -> path

profile：teaching_longform（預設）/ vlog / shorts —— 三種片型節奏本來就不同，
用同一組門檻會兩邊都錯（同 M68/M15「長片 vs Shorts 別搞混」的教訓）。

⚠️ gate 綠 != 流暢。運鏡順不順、轉場貼不貼拍點是人眼的事；
   本檔只擋「機械判得出來的呆板」。接 M111：交付仍需逐幀親看。

cp950 安全：print 只 ASCII；檔案 I/O 一律 encoding="utf-8"。
共用外殼（回傳結構 / raise 格式 / self-test 印法）→ gate_core.py；規則本體留本檔。
"""

from __future__ import annotations

import json
import os
import sys

try:
    from gate_core import report as _report, raise_if_failed, selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import report as _report, raise_if_failed, selftest_runner


# ═══════════════════════════════════════════════ profiles
# shot_warn / shot_fail = 單顆鏡頭秒數上限
# cpm_floor            = 整片 cuts/min 地板（低於 = 整體太黏）
# 數值錨點見檔頭：Hao 實測 11.0-22.9 cuts/min。

PROFILES = {
    # 教學長片：螢幕錄影本來就需要連續操作鏡頭，最寬鬆
    "teaching_longform": {
        "shot_warn": 10.0, "shot_fail": 18.0,
        "cpm_floor": 8.0,
        "drag_run": 3,          # 連續幾顆超 warn = 節奏斷
        "trans_fx_max_ratio": 0.35,
        "flat_cv_warn": 0.07,   # duration 變異太低＝節拍器式等長剪
    },
    # Vlog：時間戳結構、journey 敘事，中等
    "vlog": {
        "shot_warn": 8.0, "shot_fail": 14.0,
        "cpm_floor": 10.0,
        "drag_run": 3,
        "trans_fx_max_ratio": 0.40,
        "flat_cv_warn": 0.09,
    },
    # Shorts：直式短影音，最緊
    "shorts": {
        "shot_warn": 4.0, "shot_fail": 6.5,
        "cpm_floor": 18.0,
        "drag_run": 2,
        "trans_fx_max_ratio": 0.50,
        "flat_cv_warn": 0.11,
    },
}

# transitions.py 實際實作的三種（零抖動、確定性）+ 硬切
KNOWN_TRANSITIONS = {"cut", "wipe", "whip", "zoom", None, ""}

# M92：靜止圖禁 zoompan（pixel 抖動，Hao 2026-06-16「一直抖動」）
JITTER_EFFECTS = {"zoompan", "zoom_pan", "kenburns", "ken_burns"}

_DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_demo")


# ═══════════════════════════════════════════════ helpers

def _ascii(s) -> str:
    return str(s).encode("ascii", "replace").decode("ascii")


def from_durations(durations) -> list:
    """只有秒數時的便利建構：[3.2, 1.1] -> [{"dur":3.2,...}, ...]"""
    return [{"dur": float(d), "trans_in": None, "effect": None,
             "label": "s%02d" % (i + 1)}
            for i, d in enumerate(durations)]


def _norm(shots) -> list:
    out = []
    for i, s in enumerate(shots or []):
        if isinstance(s, (int, float)):
            s = {"dur": float(s)}
        d = float(s.get("dur", 0.0) or 0.0)
        out.append({
            "dur": d,
            "trans_in": (s.get("trans_in") or None),
            "effect": (s.get("effect") or None),
            "label": s.get("label") or ("s%02d" % (i + 1)),
            "idx": i,
        })
    return out


def analyze(shots) -> dict:
    """基礎統計：總長 / 顆數 / cuts per minute / 平均與最長鏡頭。"""
    sh = _norm(shots)
    total = sum(s["dur"] for s in sh)
    n = len(sh)
    cpm = (n / (total / 60.0)) if total > 0 else 0.0
    longest = max(sh, key=lambda s: s["dur"]) if sh else None
    fx = [s for s in sh if s["trans_in"] not in (None, "", "cut")]
    mean = total / n if n else 0.0
    variance = (sum((s["dur"] - mean) ** 2 for s in sh) / n) if n else 0.0
    duration_cv = (variance ** .5 / mean) if mean > 0 else 0.0
    duration_range = ((max(s["dur"] for s in sh) - min(s["dur"] for s in sh)) if sh else 0.0)
    return {
        "shots": n,
        "total_sec": round(total, 2),
        "cuts_per_min": round(cpm, 1),
        "mean_shot_sec": round(mean, 2),
        "longest_shot_sec": round(longest["dur"], 2) if longest else 0.0,
        "longest_shot_label": longest["label"] if longest else "",
        "duration_cv": round(duration_cv, 3),
        "duration_range_sec": round(duration_range, 2),
        "fx_transitions": len(fx),
        "fx_ratio": round(len(fx) / float(n), 2) if n else 0.0,
    }


# ═══════════════════════════════════════════════ gate

def gate_pace(shots, profile: str = "teaching_longform"):
    """總閘門。回傳 (ok, report)。

    fail：D-A 單顆超硬上限 / D-B 連續拖戲 / D-D 抖動特效
    warn：D-A 單顆超 warn / D-B 整片 cuts/min 過低 / D-C 轉場問題
    """
    if profile not in PROFILES:
        raise ValueError("unknown profile %r; expected one of %s"
                         % (profile, sorted(PROFILES)))
    cfg = PROFILES[profile]
    sh = _norm(shots)
    fails, warns = [], []

    if not sh:
        return False, _report(["D-0 空 shot list，無法判定節奏"], [],
                              profile=profile, stats=analyze([]))

    stats = analyze(sh)

    # ── D-A 鏡頭停太久（Hao R5 明選）
    for s in sh:
        if s["dur"] > cfg["shot_fail"]:
            fails.append("D-A 鏡頭停太久：%s = %.1fs（%s 上限 %.1fs）"
                         % (s["label"], s["dur"], profile, cfg["shot_fail"]))
        elif s["dur"] > cfg["shot_warn"]:
            warns.append("D-A 鏡頭偏長：%s = %.1fs（建議 <%.1fs）"
                         % (s["label"], s["dur"], cfg["shot_warn"]))

    # ── D-B 節奏斷：連續 N 顆都超 warn = 整段黏住
    run, run_start = 0, None
    for s in sh:
        if s["dur"] > cfg["shot_warn"]:
            run += 1
            if run_start is None:
                run_start = s["label"]
            if run == cfg["drag_run"]:
                fails.append("D-B 節奏斷：%s 起連續 %d 顆都超過 %.1fs"
                             % (run_start, cfg["drag_run"], cfg["shot_warn"]))
        else:
            run, run_start = 0, None

    # ── D-B 整片密度地板
    if stats["total_sec"] >= 30 and stats["cuts_per_min"] < cfg["cpm_floor"]:
        warns.append("D-B 整片太黏：%.1f cuts/min（%s 地板 %.1f；Hao 參考片 11.0-22.9）"
                     % (stats["cuts_per_min"], profile, cfg["cpm_floor"]))

    # ── D-E 反節拍器：平均刀速對，但每顆幾乎等長，仍會看起來像自動拼接。
    if stats["shots"] >= 8 and stats["total_sec"] >= 20 \
            and stats["duration_cv"] < cfg["flat_cv_warn"]:
        warns.append("D-E 節奏過平：鏡頭時長 CV=%.3f < %.2f（range %.2fs）— "
                     "請排成 build→breath→payoff 波形，不要每顆等長"
                     % (stats["duration_cv"], cfg["flat_cv_warn"],
                        stats["duration_range_sec"]))

    # ── D-C 轉場生硬
    unknown = sorted({s["trans_in"] for s in sh
                      if s["trans_in"] not in KNOWN_TRANSITIONS})
    if unknown:
        warns.append("D-C 未知轉場：%s（transitions.py 只實作 wipe/whip/zoom；"
                     "其餘未驗證是否零抖動）" % ", ".join(_ascii(u) for u in unknown))
    if stats["fx_ratio"] > cfg["trans_fx_max_ratio"]:
        warns.append("D-C 轉場特效過密：%.0f%% 的接點有特效（上限 %.0f%%）— "
                     "Hao 關掉別人影片的四個點之一是『畫面很亂』"
                     % (stats["fx_ratio"] * 100, cfg["trans_fx_max_ratio"] * 100))
    if stats["shots"] >= 8 and stats["fx_transitions"] == 0:
        warns.append("D-C 全片硬切：%d 顆鏡頭 0 個轉場 — 檢查是否過於單調"
                     % stats["shots"])

    # ── D-D 抖動特效（M92 plan 層前攔）
    for s in sh:
        eff = (s["effect"] or "").lower()
        if any(j in eff for j in JITTER_EFFECTS):
            fails.append("D-D 抖動特效：%s 用了 %s（M92：靜止圖禁 zoompan，"
                         "Hao 2026-06-16『一直抖動』）" % (s["label"], _ascii(s["effect"])))

    rep = _report(fails, warns, profile=profile, stats=stats)
    return rep["ok"], rep


def assert_pace(shots, profile: str = "teaching_longform", label: str = ""):
    """不過就 raise AssertionError（訊息格式全系統統一）。"""
    _ok, rep = gate_pace(shots, profile)
    raise_if_failed(rep, label or profile, "Pace gate FAIL")
    for w in rep["warns"]:
        print("   WARN " + _ascii(w))
    return shots


# ═══════════════════════════════════════════════ report io

def write_report(report: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    st = report["stats"]
    lines = ["PACE GATE REPORT", "=" * 50,
             "verdict: %s" % ("PASS" if report["ok"] else "FAIL"),
             "profile: %s" % report["profile"], ""]
    lines.append("[stats] shots=%d total=%.1fs cuts/min=%.1f mean=%.2fs"
                 % (st["shots"], st["total_sec"], st["cuts_per_min"],
                    st["mean_shot_sec"]))
    lines.append("        longest=%s %.1fs | duration CV=%.3f range=%.2fs | fx transitions=%d (%.0f%%)"
                 % (st["longest_shot_label"], st["longest_shot_sec"],
                    st["duration_cv"], st["duration_range_sec"],
                    st["fx_transitions"], st["fx_ratio"] * 100))
    lines.append("")
    lines.append("[fails] %d" % len(report["fails"]))
    for f in report["fails"]:
        lines.append("  - " + f)
    lines.append("")
    lines.append("[warns] %d" % len(report["warns"]))
    for w in report["warns"]:
        lines.append("  - " + w)
    lines.append("")
    lines.append("NOTE: gate 綠 != 流暢。運鏡順不順 / 轉場貼不貼拍點是人眼的事。")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    jpath = os.path.splitext(path)[0] + ".json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


# ═══════════════════════════════════════════════ self-test
# M111 雙向自測：該擋的擋、該放的放。

def _selftest_body(check):
    # ── 正向：照 Hao 實測節奏的教學長片（~16 cuts/min）必須全過
    good = []
    wave = [3.0, 4.2, 3.4, 4.4]  # avg 3.75；有推進、呼吸、再加速
    for i in range(40):
        good.append({"dur": wave[i % len(wave)],
                     "trans_in": "wipe" if i % 5 == 0 else "cut",
                     "label": "b%02d" % i})
    ok, rep = gate_pace(good, "teaching_longform")
    check("Hao-calibrated 16 cuts/min passes", ok)
    check("stats cuts_per_min ~16", abs(rep["stats"]["cuts_per_min"] - 16.0) < 0.5)
    check("no warns on calibrated pace", not rep["warns"])

    flat = [{"dur": 3.75, "trans_in": "wipe" if i % 5 == 0 else "cut",
             "label": "f%02d" % i} for i in range(16)]
    ok_flat, rep_flat = gate_pace(flat, "teaching_longform")
    check("D-E flat metronome warns without blocking", ok_flat and any(
        w.startswith("D-E") for w in rep_flat["warns"]))

    # ── D-A 單顆超硬上限 → fail
    drag = from_durations([3.0] * 10 + [22.0] + [3.0] * 10)
    okA, repA = gate_pace(drag, "teaching_longform")
    check("D-A blocks overlong shot", (not okA) and any(
        f.startswith("D-A") for f in repA["fails"]))

    # ── D-A 偏長 → warn 不擋
    mild = from_durations([3.0] * 10 + [12.0] + [3.0] * 10)
    okA2, repA2 = gate_pace(mild, "teaching_longform")
    check("D-A warns on mildly long shot without blocking",
          okA2 and any(w.startswith("D-A") for w in repA2["warns"]))

    # ── D-B 連續拖戲 → fail
    run = from_durations([3.0] * 5 + [11.0, 11.5, 12.0] + [3.0] * 5)
    okB, repB = gate_pace(run, "teaching_longform")
    check("D-B blocks 3-in-a-row drag", (not okB) and any(
        f.startswith("D-B") for f in repB["fails"]))

    # ── D-B 整片太黏 → warn
    sticky = from_durations([9.0] * 8)      # 6.7 cuts/min，且沒有 3 連超 10s
    okB2, repB2 = gate_pace(sticky, "teaching_longform")
    check("D-B warns on low cuts/min",
          any(w.startswith("D-B 整片太黏") for w in repB2["warns"]))

    # ── D-C 未知轉場 → warn
    unk = [{"dur": 3.0, "trans_in": "starwipe", "label": "x1"}] + from_durations([3.0] * 5)
    _okC, repC = gate_pace(unk, "teaching_longform")
    check("D-C warns on unknown transition", any(
        w.startswith("D-C 未知轉場") for w in repC["warns"]))

    # ── D-C 轉場過密 → warn（Hao：畫面很亂）
    busy = [{"dur": 3.0, "trans_in": "whip", "label": "b%d" % i} for i in range(12)]
    _okC2, repC2 = gate_pace(busy, "teaching_longform")
    check("D-C warns on transition overload", any(
        "轉場特效過密" in w for w in repC2["warns"]))

    # ── D-C 全硬切 → warn
    allcut = from_durations([3.0] * 12)
    _okC3, repC3 = gate_pace(allcut, "teaching_longform")
    check("D-C warns on all-hard-cut", any("全片硬切" in w for w in repC3["warns"]))

    # ── D-D 抖動特效 → fail（M92）
    jitter = [{"dur": 3.0, "effect": "zoompan", "label": "img01"}] + from_durations([3.0] * 5)
    okD, repD = gate_pace(jitter, "teaching_longform")
    check("D-D blocks zoompan jitter", (not okD) and any(
        f.startswith("D-D") for f in repD["fails"]))
    check("D-D also catches kenburns alias", not gate_pace(
        [{"dur": 3.0, "effect": "kenBurns"}], "teaching_longform")[0])

    # ── profile 差異：同一組 shot 在 shorts 要被擋、在長片放行
    mid = from_durations([5.0] * 6)
    ok_long, _ = gate_pace(mid, "teaching_longform")
    ok_short, rep_short = gate_pace(mid, "shorts")
    check("same shots pass as longform", ok_long)
    check("same shots fail as shorts", not ok_short)
    check("shorts failure is D-A/D-B", any(
        f.startswith("D-A") or f.startswith("D-B") for f in rep_short["fails"]))

    # ── 邊界
    ok_e, rep_e = gate_pace([], "teaching_longform")
    check("empty shot list fails cleanly", (not ok_e) and rep_e["fails"])
    check("from_durations builds labels",
          from_durations([1.0, 2.0])[1]["label"] == "s02")
    check("bare numbers accepted", gate_pace([3.0] * 10, "teaching_longform")[0])
    try:
        gate_pace(good, "nope")
        check("unknown profile rejected", False)
    except ValueError:
        check("unknown profile rejected", True)

    # ── assert 契約
    try:
        assert_pace(jitter, "teaching_longform", label="v9")
        check("assert_pace raises on fail", False)
    except AssertionError as e:
        check("assert_pace raises on fail", "[v9] Pace gate FAIL" in str(e))
    check("assert_pace returns shots on pass",
          assert_pace(good, "teaching_longform") is good)

    # ── report io
    demo = os.path.join(_DEMO_DIR, "pace_report.txt")
    write_report(repA, demo)
    check("demo report written", os.path.isfile(demo) and os.path.getsize(demo) > 200)
    check("demo report json written",
          os.path.isfile(os.path.join(_DEMO_DIR, "pace_report.json")))


def _selftest():
    return selftest_runner(_selftest_body, width=56, list_fails=True)


if __name__ == "__main__":
    raise SystemExit(_selftest())
