# -*- coding: utf-8 -*-
"""shorts_gate.py — 直式 Shorts 機械閘門（2026-07-27 落地；creator「把 shorts 訓練全部寫進 skill 記死」）

把「剪 Shorts 的所有規則」變成 build 時就擋的 assert，不靠任何人記得。
知識來源 SoT → references/shorts-mastery-2026.md

規則分三層：
  【結構】S-A 開場識別 / S-B 片長雙峰 / S-C 首刀 2 秒 / S-D loop 對齊 / S-E 地址常駐
  【字幕】S-F 綁 segment 索引（禁手算時間）/ S-G loop 段禁字幕 / S-H 不跨 cut / S-I 白字為底
  【內容】S-J 讀畫面文字（品名+價格）/ S-K 運鏡不移開主體 / S-L 品名取該主體正上方那張牌

API:
    expand_caps(spec)     -> [(start, end, blocks, kind)]   # 由 segment 索引算時間
    gate_shorts(spec)     -> (ok, report)                   # 全規則檢查
    assert_shorts(spec)   -> spec（含展開後 caps）           # build 前呼叫，不過直接 raise

spec 結構（一支 Short）:
    {
      "name": "s13_bakery",
      "place": "新竹 酵想",              # 開場識別大字（必填）
      "what":  "木頭櫃甜品店",            # 一句這是什麼（必填）
      "addr":  "📍 酵想｜新竹市東區仁愛街76號",   # 地址常駐條（必填）
      "segs":  [(clip, in_sec, dur), ...],
      "caps_by_seg": [(seg_idx, [(text, color)], kind), ...],
      "bgm_folder": "咖啡廳甜點",
    }
cp950 安全：print 只 ASCII；I/O utf-8。
共用外殼（回傳結構 / assert 訊息 / self-test 印法）→ gate_core.py；規則本體留在本檔。
"""
from __future__ import annotations

import json
import math
import re

import os
import sys
from collections import defaultdict

try:
    from gate_core import make_assert, report as _report, selftest_runner
except ImportError:                                  # 從別的 cwd 或單檔複製時
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gate_core import make_assert, report as _report, selftest_runner

try:
    from .shorts_gate_validation import (
        GatePolicy,
        finalize_expanded_report,
        validate_caption_plan,
        validate_opening_and_battle,
        validate_required_fields,
        validate_timeline,
    )
except ImportError:                                  # 直接執行本檔時載入同層模組
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from shorts_gate_validation import (
        GatePolicy,
        finalize_expanded_report,
        validate_caption_plan,
        validate_opening_and_battle,
        validate_required_fields,
        validate_timeline,
    )

# ── 常數（實測校準，改前先看 shorts-mastery-2026.md）
DUR_MIN, DUR_MAX = 13.0, 25.0      # S-B 片長雙峰：13-25s（梗/單一驚奇型）；26-44s=死區
DUR_DEADZONE = (25.001, 44.999)    #      45-60s 是教學/demo 型，本 gate 只管短帶
FIRST_CUT_MAX = 2.05               # S-C 2 秒法則：第一刀 ≤2.0s
LOOP_TOL = 0.35                    # S-D loop：末段結束點 vs 首段起點容差
OPEN_WINDOW = 2.05                 # S-A 開場識別窗
TAIL_CLEAR = 0.5                   # loop 接點淨空
CAP_PAD, CAP_GAP = 0.15, 0.12      # 字幕在段內的留邊/間隔
NONWHITE_MAX_RATIO = 0.35          # S-I white-first
NONWHITE_MAX_COLORS = 2

# ── S-S 字幕美術模式（巨字／票券／2.5D 浮空只做語意節點，不可全片濫用）
CAPTION_KINDS = frozenset({
    "main", "hook", "sub", "addr", "impact", "ribbon", "float_left", "float_right", "chip",
})
KINETIC_KINDS = frozenset({"impact", "ribbon", "float_left", "float_right"})
KIND_CHAR_LIMIT = {"impact": 12, "ribbon": 14, "float_left": 8, "float_right": 8, "chip": 18}
KINETIC_MAX_RATIO = .40

# ── 平台片長規則（2026-07-28 競品拆解校準）
# 死區 26-44s 的來源是 **YouTube Shorts** 第三方研究。實測 5 支 IG/FB Reels 競品，
# 其中 31.8s 與 30.1s 兩支正好落在該區間、表現正常（30.1s 那支 3.3 萬互動）
# → **死區不可跨平台套用**。不分平台硬擋 = 假 BLOCK（同 M111 家族）。
# 依據 → references/competitor-vertical-teardown-2026.md §7
PLATFORM_RULES = {
    "yt_shorts": {"dur_min": 13.0, "dur_max": 25.0, "deadzone": (25.001, 44.999)},
    "ig_reels":  {"dur_min": 13.0, "dur_max": 60.0, "deadzone": None},
    "fb_reels":  {"dur_min": 13.0, "dur_max": 60.0, "deadzone": None},
}
DEFAULT_PLATFORM = "yt_shorts"     # 不指定就沿用舊行為（向後相容）

# ── S-O 字幕節奏（2026-07-28 競品拆解 §2 落地）
# 逐幀量測 7 支市面直式短片：**每一支的換句速率都高於剪點速率**，
# 最極端一支 32s 只剪 5 刀卻換了 40 次字幕 —— 直式的節奏主體是「換句」不是「剪點」。
# 實測換句/分：39.7 / 52.0 / 57.6 / 59.7 / 71.1 / 75.0 / 75.4（中位 59.7、最低 39.7）
# ⚠️ 只 warn 不 fail：7 支**全是成功樣本、沒有失敗對照組**，
#    只能說「成功的都這樣」，不能說「這樣才會成功」。門檻取最低樣本再放寬。
# 依據 → references/competitor-vertical-teardown-2026.md §2 / §10
CAP_DWELL_WARN = 1.8               # 內容字幕中位停留 > 此值 = 太稀
CAP_RATE_WARN = 30.0               # 換句/分 < 此值 = 太稀（最低樣本 39.7 再放寬）

# ── S-R reading rate (PUBLIC_FIXTURE generic starter)
# Measure readable characters per display second.  The starter warn/fail
# values are configurable and carry no maintainer quote or project result.
SR_WARN = 5.0                      # 字/秒 > 5 → warn
SR_FAIL = 7.0                      # 字/秒 > 7 → fail（讀不完=白寫）


def _nchars(txt: str) -> int:
    return sum(1 for ch in txt if not ch.isspace())


def _is_official_go_shoot(txt: str) -> bool:
    """BEYBLADE X 固定口令；屬熟悉倒數節拍，不以一般敘述句讀速誤殺。"""
    return bool(re.fullmatch(
        r"3\s*[・、，,.]?\s*2\s*[・、，,.]?\s*1\s+Go\s*Shoot[!！]?",
        txt.strip(), re.I,
    ))

# ── S-P 高風險宣稱 lint（2026-08-04：一輪對抗稽核推翻 29 條字幕後歸納落地）
# 29 條裡八成落在六類**機器抓得到**的詞。規則不是禁用這些詞——
# 是「用了就要付得出證據」：SPEC["evidence"][字幕原文] = 怎麼驗過的
# （frame: 親抽哪格看到什麼 / sign: 哪張牌逐字讀 / web: 出處 / user: creator 告知）。
# 實例：「停滿」實際 3 隻、「原木」實為仿木、「墨綠」實測灰綠、「世界最大跨距單塔
# 斜張橋」漏掉官方紀錄名裡的「不對稱」——全是這六類。無佐證 = FAIL。
RISKY_PATTERNS = (
    ("絕對量詞", re.compile(r"[停擠鋪塞爆]滿|滿滿|都是|全是|全部|完全|"
                            r"整[片排桌條座面段街]|每[一片階格盤張條位]")),
    ("數量斷言", re.compile(r"[一兩二三四五六七八九十][盤樣種隻碗]")),
    ("材質斷言", re.compile(r"原木|石條|碎石|石階|檜木|大理石")),
    ("深色斷言", re.compile(r"墨綠|漆黑|烏黑")),
    ("最高級",   re.compile(r"世界最|全台|全國|僅此一家|首創|唯一")),
    ("方案宣稱", re.compile(r"吃到飽|無限暢飲|不限時|免費")),
)

# ── S-Q 首幀技術品質（2026-08-04：稽核抓到「用全資料夾最軟的一格當首幀」後落地）
# S-N（首幀內容強不強）仍是人工項——之前試過機械化失敗（銳利度/對比分不出好壞內容）。
# 但「同一格 vs 全素材池」的**相對**銳利度是另一回事：選到池裡最軟的格子＝技術面失分，
# 這抓得到。資料免費：scan 期的 _scan.json 已有每 0.5s 的 sharp/bright。warn 級——
# 內容判斷可以壓過技術分數，但 warn 會把更銳利的候選格印出來給人比對。
SQ_RATIO = 0.6                     # 首幀銳利度 < 全池最高的 60% → warn（實案 13.7/31.0=0.44）

_GATE_POLICY = GatePolicy(
    platform_rules=PLATFORM_RULES,
    default_platform=DEFAULT_PLATFORM,
    first_cut_max=FIRST_CUT_MAX,
    loop_tolerance=LOOP_TOL,
    tail_clear=TAIL_CLEAR,
    caption_kinds=CAPTION_KINDS,
    kinetic_kinds=KINETIC_KINDS,
    kind_char_limit=KIND_CHAR_LIMIT,
    kinetic_max_ratio=KINETIC_MAX_RATIO,
    nonwhite_max_ratio=NONWHITE_MAX_RATIO,
    nonwhite_max_colors=NONWHITE_MAX_COLORS,
    risky_patterns=RISKY_PATTERNS,
    reading_warn=SR_WARN,
    reading_fail=SR_FAIL,
    caption_dwell_warn=CAP_DWELL_WARN,
    caption_rate_warn=CAP_RATE_WARN,
    first_frame_ratio=SQ_RATIO,
)


def _first_frame_quality(spec: dict):
    """回 {chosen, best, top} 或 None（無 _scan.json 時靜默跳過=向後相容）。"""
    clip0, in0, _d = spec["segs"][0]
    scan_p = os.path.join(os.path.dirname(str(clip0)), "_scan.json")
    if not os.path.isfile(scan_p):
        return None
    try:
        with open(scan_p, encoding="utf-8") as f:
            j = json.load(f)
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(j, dict) or not isinstance(j.get("clips", []), list):
        return None
    stem0 = os.path.splitext(os.path.basename(str(clip0)))[0]
    pool, chosen = [], None
    for c in j.get("clips", []):
        if (not isinstance(c, dict) or not isinstance(c.get("name", "?"), str)
                or not isinstance(c.get("rows", []), list)):
            return None
        for r in c.get("rows", []):
            if not isinstance(r, dict):
                return None
            values = (r.get("bright", 128), r.get("sharp", 0.0), r.get("t", -9.0))
            try:
                if any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) for value in values):
                    return None
            except OverflowError:
                return None
            if 40 <= r.get("bright", 128) <= 225:          # 全黑/全爆的幀不算候選
                pool.append((r.get("sharp", 0.0), c.get("name", "?"), r.get("t", 0.0)))
            if c.get("name") == stem0 and abs(r.get("t", -9.0) - in0) <= 0.26:
                if chosen is None or abs(r["t"] - in0) < abs(chosen[2] - in0):
                    chosen = (r.get("sharp", 0.0), c.get("name"), r.get("t"))
    if not pool or chosen is None:
        return None
    return {"chosen": chosen, "best": max(pool),
            "top": sorted(pool, reverse=True)[:3]}


# ────────────────────────────────────────────── 字幕展開（S-F）

def expand_caps(spec: dict) -> list:
    """caps_by_seg（綁 segment 索引）→ 時間軸字幕；同段多條自動平分。

    人不再手算時間 → 「字幕配錯段」在結構上不可能發生（2026-07-27 s17 整組晚一段的教訓）。
    """
    bounds, acc = [], 0.0
    for _f, _i, d in spec["segs"]:
        bounds.append((round(acc, 3), round(acc + d, 3)))
        acc += d

    by = defaultdict(list)
    for idx, blocks, kind in spec["caps_by_seg"]:
        by[idx].append((blocks, kind))

    out = []
    for idx in sorted(by):
        if idx >= len(bounds):
            raise AssertionError("%s caps_by_seg 指到不存在的 seg%d" % (spec.get("name", "?"), idx))
        b0, b1 = bounds[idx]
        items = by[idx]
        n = len(items)
        usable = (b1 - b0) - CAP_PAD * 2 - CAP_GAP * (n - 1)
        if usable <= 0.45 * n:
            raise AssertionError(
                "%s seg%d 長 %.1fs 塞不下 %d 條字幕" % (spec.get("name", "?"), idx, b1 - b0, n))
        each = usable / n
        for i, (blocks, kind) in enumerate(items):
            st = round(b0 + CAP_PAD + i * (each + CAP_GAP), 2)
            out.append((st, round(st + each, 2), blocks, kind))
    return sorted(out)


def seg_bounds(spec: dict) -> list:
    bounds, acc = [], 0.0
    for _f, _i, d in spec["segs"]:
        bounds.append((round(acc, 3), round(acc + d, 3)))
        acc += d
    return bounds


if __package__:
    from .shorts_battle_contract import (
        _battle_presentation_failures,
        _battle_matchup_failures,
        _battle_result_findings,
    )
else:
    from shorts_battle_contract import (
        _battle_presentation_failures,
        _battle_matchup_failures,
        _battle_result_findings,
    )


# ────────────────────────────────────────────── 總閘門

def gate_shorts(spec: dict):
    """回傳 (ok, report)；缺欄位或格式錯誤回 BLOCK，不進入媒體檢查。"""
    fails, warns = [], []
    validate_required_fields(spec, fails)
    if fails:
        return False, _report(fails, warns)

    timeline = validate_timeline(spec, _GATE_POLICY, fails)
    captions = validate_opening_and_battle(
        spec, fails, warns, _battle_matchup_failures, _battle_result_findings,
    )
    validate_caption_plan(
        spec, timeline, captions, _GATE_POLICY, fails, warns,
        _nchars, _is_official_go_shoot,
    )
    if fails:
        return False, _report(fails, warns, dur=timeline.duration)

    return finalize_expanded_report(
        spec, timeline, _GATE_POLICY, fails, warns,
        expand_caps=expand_caps,
        seg_bounds=seg_bounds,
        report=_report,
        first_frame_quality=_first_frame_quality,
        nchars=_nchars,
        is_official_go_shoot=_is_official_go_shoot,
    )

def _attach_addr(spec: dict, rep: dict) -> dict:
    """過關後的加工：依政策附地點條 + 展開後 caps + 片長。"""
    caps = list(rep["caps"])
    # required is legacy-only. New edits use intro: a short semantic chip,
    # never a permanent black strip competing with the footage.
    policy = str(spec.get("persistent_label_policy", "required"))
    if policy == "required":
        caps.append((0.2, round(rep["dur"] - 0.15, 2), [(spec["addr"], "white")], "addr"))
    elif policy == "intro":
        end = min(round(rep["dur"] - 0.15, 2), 3.0)
        label = str(spec.get("location_chip") or spec.get("place") or "").strip()
        caps.append((0.35, end, [(label, "white")], "chip"))
    return dict(spec, caps=sorted(caps), _dur=rep["dur"], _warns=rep["warns"])


# build 前呼叫：不過直接 raise；過了回傳含展開 caps 的 spec（附地址常駐條）。
assert_shorts = make_assert(gate_shorts,
                            lambda spec: spec.get("name", "?") if isinstance(spec, dict) else "?",
                            "Shorts gate FAIL",
                            post=_attach_addr)


# ────────────────────────────────────────────── self-test

def _selftest_fixture():
    if __package__:
        from .shorts_gate_commands import _selftest_fixture as _implementation
    else:
        from shorts_gate_commands import _selftest_fixture as _implementation
    return _implementation(globals())


def _selftest_battle_rules(check, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_battle_rules as _implementation
    else:
        from shorts_gate_commands import _selftest_battle_rules as _implementation
    return _implementation(globals(), check, mk, good)

def _selftest_gate_rules(check, dummy, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_gate_rules as _implementation
    else:
        from shorts_gate_commands import _selftest_gate_rules as _implementation
    return _implementation(globals(), check, dummy, mk, good)

def _selftest_caption_rendering(check, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_caption_rendering as _implementation
    else:
        from shorts_gate_commands import _selftest_caption_rendering as _implementation
    return _implementation(globals(), check, mk, good)

def _selftest_semantic_rules(check, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_semantic_rules as _implementation
    else:
        from shorts_gate_commands import _selftest_semantic_rules as _implementation
    return _implementation(globals(), check, mk, good)

def _selftest_first_frame_rules(check, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_first_frame_rules as _implementation
    else:
        from shorts_gate_commands import _selftest_first_frame_rules as _implementation
    return _implementation(globals(), check, mk, good)

def _selftest_reading_rules(check, mk, good):
    if __package__:
        from .shorts_gate_commands import _selftest_reading_rules as _implementation
    else:
        from shorts_gate_commands import _selftest_reading_rules as _implementation
    return _implementation(globals(), check, mk, good)


def _selftest_body(check):
    if __package__:
        from .shorts_gate_commands import _selftest_body as _implementation
    else:
        from shorts_gate_commands import _selftest_body as _implementation
    return _implementation(globals(), check)


def _selftest() -> int:
    if __package__:
        from .shorts_gate_commands import _selftest as _implementation
    else:
        from shorts_gate_commands import _selftest as _implementation
    return _implementation(globals())


if __name__ == "__main__":
    raise SystemExit(_selftest())
