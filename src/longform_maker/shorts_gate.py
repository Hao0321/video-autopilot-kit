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
    except Exception:
        return None
    stem0 = os.path.splitext(os.path.basename(str(clip0)))[0]
    pool, chosen = [], None
    for c in j.get("clips", []):
        for r in c.get("rows", []):
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
            raise AssertionError("%s caps_by_seg 指到不存在的 seg%d" % (spec["name"], idx))
        b0, b1 = bounds[idx]
        items = by[idx]
        n = len(items)
        usable = (b1 - b0) - CAP_PAD * 2 - CAP_GAP * (n - 1)
        if usable <= 0.45 * n:
            raise AssertionError(
                "%s seg%d 長 %.1fs 塞不下 %d 條字幕" % (spec["name"], idx, b1 - b0, n))
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


def _battle_matchup_failures(spec: dict) -> list[str]:
    """驗證戰鬥陀螺對戰的名稱／真偽標示策略。

    `battle_matchup` 是明確資料，不從文案猜正版或盜版：
    official vs official 只顯示名稱；official vs counterfeit 才顯示真偽。
    """
    battle = spec.get("battle_matchup")
    if battle is None:
        return []
    if not isinstance(battle, dict):
        return ["S-T battle_matchup 必須是 dict"]

    left, right = battle.get("left") or {}, battle.get("right") or {}
    names = [str(left.get("name", "")).strip(), str(right.get("name", "")).strip()]
    auth = [str(left.get("authenticity", "")).strip(),
            str(right.get("authenticity", "")).strip()]
    fails = []
    if not all(names):
        fails.append("S-T battle_matchup 左右雙方都必須有 name")
    valid_auth = {"official", "counterfeit", "unknown"}
    if not all(a in valid_auth for a in auth):
        fails.append("S-T authenticity 僅可為 official/counterfeit/unknown")
    if fails:
        return fails

    caps = ["".join(t for t, _c in blocks).strip()
            for _idx, blocks, _kind in spec.get("caps_by_seg", [])]
    tracked = [str(x.get("text", "")).strip()
               for x in (spec.get("tracked_graphics") or {}).get("tracked_labels", [])]
    tracked_rows = list((spec.get("tracked_graphics") or {}).get("tracked_labels", []))
    motion = spec.get("tracked_graphics") or {}
    hud = [str(x.get("label", "")).strip()
           for x in ((spec.get("tracked_graphics") or {}).get("hud") or {}).get("items", [])]
    visible = [x for x in caps + tracked + hud if x]
    visible_joined = "\n".join(visible)

    # S-W：creator 的陀螺視覺語法是「物件貼附姓名牌＋主體 matte 斜角閃光」。
    # 競技盤鎖定框、HUD 卡片與三條線已被人工審核多次否決；對戰成片不得回退。
    if motion.get("lock_effects"):
        fails.append("S-W 戰鬥片禁止競技盤／中央鎖定框；請用物件 Tracking 姓名牌")
    if motion.get("hud"):
        fails.append("S-W 戰鬥片禁止框式 HUD；請用無框物件貼附標籤")
    if len(tracked_rows) < 2:
        fails.append("S-W 戰鬥片必須有兩顆陀螺的動態 Tracking 身分標籤")
    mixed_authenticity = set(auth) == {"official", "counterfeit"}
    for side, name, authenticity in zip(("left", "right"), names, auth):
        required_auth = (("正版" if authenticity == "official" else "盜版")
                         if mixed_authenticity else "")
        candidates = [row for row in tracked_rows
                      if name in str(row.get("text", ""))]
        if not candidates:
            fails.append("S-W %s 缺少跟隨主體的名稱標籤：%s" % (side, name))
            continue
        if required_auth and not any(required_auth in str(row.get("text", ""))
                                     for row in candidates):
            fails.append("S-W %s 的 Tracking 標籤缺少真偽：%s｜%s"
                         % (side, required_auth, name))
        if not all(str(row.get("evidence", "")).strip() for row in candidates):
            fails.append("S-W %s 的 Tracking 標籤缺少人工核對證據：%s" % (side, name))
        if any(str(row.get("style", "typography")) not in {"typography", "identity_callout"}
               for row in candidates):
            fails.append("S-W 陀螺身分標籤必須使用無框 typography／identity_callout，不可用面板式 telemetry")

    sheens = list(motion.get("mask_sheens") or [])
    if len(sheens) < 2:
        fails.append("S-W 戰鬥片必須為兩顆陀螺各提供一次主體內黑→彩斜角閃光")
    for index, sheen in enumerate(sheens):
        if str(sheen.get("target_kind", "subject_object")) != "subject_object":
            fails.append("S-W mask_sheens[%d] 只能作用在陀螺主體，不可掃文字／背景" % index)
        if str(sheen.get("subject_class", "")) != "battle_top":
            fails.append("S-W mask_sheens[%d] 必須標記 subject_class=battle_top" % index)
        if str(sheen.get("reveal_mode", "")) != "black_to_color":
            fails.append("S-W mask_sheens[%d] 必須使用 black_to_color 黑→彩斜角閃光" % index)
        if str(sheen.get("shape", "")) not in {"auto_sequence", "sequence", "alpha", "polygon"}:
            fails.append("S-W mask_sheens[%d] 禁止 ellipse／bbox 假遮罩；必須逐幀 matte" % index)
        if not str(sheen.get("evidence", "")).strip():
            fails.append("S-W mask_sheens[%d] 缺少 matte／追蹤人工核對證據" % index)

    # S-U：BEYBLADE X 官方對戰口號固定為「3・2・1 Go Shoot！」。
    # 「發射」可作一般動作名詞，但不能取代倒數口號。
    slogan_blob = "\n".join(visible + [str(spec.get("what", "")), str(spec.get("place", ""))])
    wrong_slogan = re.compile(r"(?:3\s*[・、，,.]?\s*2\s*[・、，,.]?\s*1|三\s*[、，]?\s*二\s*[、，]?\s*一)\s*(?:發射|发射)", re.I)
    if wrong_slogan.search(slogan_blob):
        fails.append("S-U 戰鬥陀螺倒數口號必須是『3・2・1 Go Shoot！』，禁止寫『3・2・1 發射』")

    if auth == ["official", "official"]:
        redundant = [x for x in visible if "正版" in x]
        if redundant:
            fails.append("S-T 正版對正版只顯示陀螺名稱，禁止真偽冗字：%s"
                         % "/".join(redundant))
        for competitor in names:
            if competitor not in visible_joined:
                fails.append("S-T 正版對正版缺少陀螺名稱：%s" % competitor)
            if any(x == competitor for x in caps):
                fails.append("S-T 名稱已用 Tracking 呈現，不可再用獨立底部字幕重複：%s"
                             % competitor)
    elif set(auth) == {"official", "counterfeit"}:
        for required in ("正版", "盜版"):
            if required not in visible_joined:
                fails.append("S-T 正版對盜版必須清楚標示：%s" % required)
    return fails


def _battle_result_findings(spec: dict) -> tuple[list[str], list[str]]:
    """禁止在沒有逐格證據時，把猜測包裝成官方 Finish 判定。"""
    battle = spec.get("battle_matchup")
    if battle is None:
        return [], []

    caps = ["".join(t for t, _c in blocks).strip()
            for _idx, blocks, _kind in spec.get("caps_by_seg", [])]
    tracked = [str(x.get("text", "")).strip()
               for x in (spec.get("tracked_graphics") or {}).get("tracked_labels", [])]
    hud = [str(x.get("label", "")).strip()
           for x in ((spec.get("tracked_graphics") or {}).get("hud") or {}).get("items", [])]
    visible_text = "\n".join(
        x for x in caps + tracked + hud
        + [str(spec.get("what", "")), str(spec.get("place", ""))] if x
    )

    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)
    try:
        from beyblade_x_rules import validate_battle_result, visible_finish
    except (ImportError, OSError, ValueError) as exc:
        return [f"S-V BEYBLADE X 規則驗證器無法載入：{exc}"], []

    shown = visible_finish(visible_text)
    result = spec.get("battle_result")
    if result is None:
        if shown:
            return ["S-V 畫面使用官方 Finish 名稱，但缺少 battle_result 逐格判定證據"], []
        return [], []

    verdict = validate_battle_result(
        result,
        matchup=battle,
        visible_text=visible_text,
    )
    failures = [f"S-V {message}" for message in verdict.get("failures", [])]
    warnings = [f"S-V {message}" for message in verdict.get("warnings", [])]
    return failures, warnings


# ────────────────────────────────────────────── 總閘門

def gate_shorts(spec: dict):
    """回傳 (ok, report)。report["fails"] 非空 = 不准出片。"""
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
                            lambda spec: spec.get("name", "?"),
                            "Shorts gate FAIL",
                            post=_attach_addr)


# ────────────────────────────────────────────── self-test

def _selftest_fixture():
    here = os.path.dirname(os.path.abspath(__file__))
    dummy = os.path.join(here, "shorts_gate.py")   # 用本檔當「存在的檔案」

    def mk(**kw):
        base = dict(
            name="t", place="測試地", what="測試說明", addr="📍 測試地｜某路1號",
            segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                  (dummy, 13.0, 3.5), (dummy, 0.0, 2.0)],
            caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                         (0, [("測試說明", "white")], "sub"),
                         (1, [("內容一", "white")], "sub"),
                         (2, [("內容二", "white")], "sub"),
                         (3, [("內容三", "white")], "sub")],
            bgm_folder="_通用",
        )
        base.update(kw)
        return base

    good = mk()
    return dummy, mk, good


def _selftest_battle_rules(check, mk, good):
    ok, rep = gate_shorts(good)
    check("good spec passes", ok)
    check("good dur in 13-25 band", 13.4 < rep["dur"] < 13.6)

    battle_caps = [
        (0, [("三角龍 VS 榮耀女武神", "gold")], "impact"),
        (1, [("高速對撞", "white")], "sub"),
        (2, [("轉速還在", "white")], "sub"),
        (3, [("WIN｜三角龍", "white")], "sub"),
    ]
    battle_data = {
        "left": {"name": "三角龍", "authenticity": "official"},
        "right": {"name": "榮耀女武神", "authenticity": "official"},
        "label_policy": "names_only_when_same_authenticity",
    }
    battle_good = mk(
        place="三角龍 VS 榮耀女武神", what="三角龍 VS 榮耀女武神",
        caps_by_seg=battle_caps, battle_matchup=battle_data, loop_policy="forbidden",
        battle_edit_contract={
            "showcase_segments": [0], "result_segments": [3], "result_once": True,
            "ending": "single_pass",
        },
        tracked_graphics={
            "tracked_labels": [
                {"text": "三角龍", "evidence": "verified", "style": "typography"},
                {"text": "榮耀女武神", "evidence": "verified", "style": "typography"},
            ],
            "mask_sheens": [
                {"target_kind": "subject_object", "subject_class": "battle_top",
                 "shape": "auto_sequence", "reveal_mode": "black_to_color",
                 "evidence": "verified left matte"},
                {"target_kind": "subject_object", "subject_class": "battle_top",
                 "shape": "auto_sequence", "reveal_mode": "black_to_color",
                 "evidence": "verified right matte"},
            ],
        },
    )
    ok_bt, r_bt = gate_shorts(battle_good)
    check("S-T official vs official uses names only", ok_bt and not r_bt["fails"])
    battle_bad = dict(
        battle_good,
        tracked_graphics={"tracked_labels": [
            {"text": "正版"}, {"text": "榮耀女武神"},
        ]},
    )
    ok_bt_bad, r_bt_bad = gate_shorts(battle_bad)
    check("S-T official vs official rejects authentic label",
          not ok_bt_bad and any("S-T" in f for f in r_bt_bad["fails"]))
    mixed_data = {
        "left": {"name": "榮耀女武神", "authenticity": "official"},
        "right": {"name": "黃金神杖", "authenticity": "counterfeit"},
    }
    mixed_bad = dict(battle_good, battle_matchup=mixed_data)
    ok_mixed, r_mixed = gate_shorts(mixed_bad)
    check("S-T official vs counterfeit requires authenticity labels",
          not ok_mixed and any("正版對盜版" in f for f in r_mixed["fails"]))
    slogan_bad = dict(
        battle_good,
        caps_by_seg=battle_caps + [(2, [("3・2・1 發射", "white")], "impact")],
    )
    r_slogan_bad = _battle_matchup_failures(slogan_bad)
    check("S-U rejects translated launch slogan",
          any("S-U" in f for f in r_slogan_bad))
    slogan_good = dict(
        battle_good,
        caps_by_seg=battle_caps + [(2, [("3・2・1 Go Shoot！", "white")], "impact")],
    )
    r_slogan_good = _battle_matchup_failures(slogan_good)
    check("S-U official Go Shoot slogan passes",
          not any("S-U" in f for f in r_slogan_good))
    unlabeled_result = dict(
        battle_good,
        caps_by_seg=battle_caps + [(3, [("BURST FINISH +2", "white")], "impact")],
    )
    r_result_missing, _ = _battle_result_findings(unlabeled_result)
    check("S-V official Finish label requires structured evidence",
          any("S-V" in f for f in r_result_missing))
    verified_result = dict(
        unlabeled_result,
        battle_result={
            "finish": "burst",
            "winner": "三角龍",
            "human_verified": True,
            "evidence": {
                "sequence_reviewed": True,
                "confidence": 0.95,
                "first_event": "burst",
                "opponent_parts_separated": True,
                "opponent_intact_immediately_before": True,
                "same_opponent_transition_observed": True,
                "separation_event_visible": True,
                "loose_part_preexisting": False,
                "simultaneous": False,
            },
        },
    )
    r_result_good, _ = _battle_result_findings(verified_result)
    check("S-V verified Burst Finish passes", not r_result_good)

def _selftest_gate_rules(check, dummy, mk, good):
    # 片長死區
    dead = mk(segs=[(dummy, 2.0, 2.0)] + [(dummy, 5.0, 8.0)] * 4 + [(dummy, 0.5, 1.5)])
    ok2, r2 = gate_shorts(dead)
    check("dead-zone duration fails", not ok2 and any("S-B" in f for f in r2["fails"]))

    # 平台感知：同一支 ~35.5s 的片，YT Shorts 要擋、IG/FB Reels 要放行
    # （2026-07-28 競品實測：IG/FB 上 30-32s 表現正常，硬擋=假 BLOCK）
    # ⚠️ 兩個方向都驗 —— 只驗「會擋」的話，一個永遠擋人的 gate 看起來也像很嚴格（M111）
    ok_ig, r_ig = gate_shorts(dict(dead, platform="ig_reels"))
    check("ig_reels 放行死區長度", ok_ig and not any("S-B" in f for f in r_ig["fails"]))
    ok_fb, _ = gate_shorts(dict(dead, platform="fb_reels"))
    check("fb_reels 放行死區長度", ok_fb)
    ok_yt, r_yt = gate_shorts(dict(dead, platform="yt_shorts"))
    check("yt_shorts 明寫平台仍擋", not ok_yt and any("S-B" in f for f in r_yt["fails"]))
    ok_bad, r_bad = gate_shorts(dict(dead, platform="tiktok"))
    check("未知平台被擋", not ok_bad and any("未知平台" in f for f in r_bad["fails"]))
    # 預設不帶 platform 時行為必須跟舊版一模一樣（向後相容）
    check("預設平台=yt_shorts 舊行為不變",
          [f for f in r2["fails"] if "S-B" in f] == [f for f in r_yt["fails"] if "S-B" in f])

    # 首刀過長
    slow = mk(segs=[(dummy, 2.0, 3.5), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                    (dummy, 13.0, 3.5), (dummy, -1.5, 3.5)])
    ok3, r3 = gate_shorts(slow)
    check("slow first cut fails", not ok3 and any("S-C" in f for f in r3["fails"]))

    # loop 未對齊
    noloop = mk(segs=[(dummy, 2.0, 2.0), (dummy, 5.0, 3.0), (dummy, 9.0, 3.0),
                      (dummy, 13.0, 3.5), (dummy, 8.0, 2.0)])
    ok4, r4 = gate_shorts(noloop)
    check("misaligned loop fails", not ok4 and any("S-D" in f for f in r4["fails"]))

    # S-A 新語意（2026-08-06）：seg0 一條（place）+ what 在 seg1 首條 = 合法（warn 頂多）
    oneopen = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                             (1, [("測試說明", "white")], "sub"),
                             (2, [("內容二", "white")], "sub"),
                             (3, [("內容三", "white")], "sub")])
    ok5a, r5a = gate_shorts(oneopen)
    check("S-A seg0 單條+what 在 seg1 首條可過",
          ok5a and not any("S-A" in f for f in r5a["fails"]))
    # seg0 完全沒字幕 → 仍必須擋
    noopen = mk(caps_by_seg=[(1, [("內容一", "white")], "sub"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    ok5, r5 = gate_shorts(noopen)
    check("S-A seg0 零字幕仍擋", not ok5 and any("S-A" in f for f in r5["fails"]))

    # 首條不是 place
    wrongname = mk(caps_by_seg=[(0, [("隨便寫", "gold")], "hook"),
                               (0, [("測試說明", "white")], "sub"),
                               (1, [("內容一", "white")], "sub"),
                               (2, [("內容二", "white")], "sub"),
                               (3, [("內容三", "white")], "sub")])
    ok6, r6 = gate_shorts(wrongname)
    check("first caption must be place", not ok6)

    # loop 段掛字幕
    loopcap = mk(caps_by_seg=good["caps_by_seg"] + [(4, [("多的", "white")], "sub")])
    ok7, r7 = gate_shorts(loopcap)
    check("caption on loop seg fails", not ok7 and any("S-G" in f for f in r7["fails"]))

    # 缺地址
    noaddr = mk(addr="")
    ok8, _ = gate_shorts(noaddr)
    check("missing address fails", not ok8)
    noaddr_product = mk(addr="", persistent_label_policy="omit")
    ok8b, _ = gate_shorts(noaddr_product)
    check("non-location content can explicitly omit persistent label", ok8b)

    # 非白色超標
    colorful = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                              (0, [("測試說明", "cream")], "sub"),
                              (1, [("內容一", "orange")], "sub"),
                              (2, [("內容二", "green")], "sub"),
                              (3, [("內容三", "blue")], "sub")])
    ok9, r9 = gate_shorts(colorful)
    check("too many accent colors fails", not ok9 and any("S-I" in f for f in r9["fails"]))

def _selftest_caption_rendering(check, mk, good):
    # S-S：巨字／票券／浮空可用，但只能短、只能少數語意節點
    selective = mk(caps_by_seg=[(0, [("測試地", "gold")], "impact"),
                                (0, [("測試說明", "white")], "ribbon"),
                                (1, [("內容一", "white")], "sub"),
                                (2, [("內容二", "white")], "sub"),
                                (3, [("內容三", "white")], "sub")])
    oks, rs = gate_shorts(selective)
    check("S-S selective kinetic captions pass", oks and not any("S-S" in f for f in rs["fails"]))
    bad_kind = mk(caps_by_seg=[(0, [("測試地", "gold")], "explode"),
                               (0, [("測試說明", "white")], "sub")])
    okk, rk = gate_shorts(bad_kind)
    check("S-S unknown kind fails", not okk and any("S-S" in f for f in rk["fails"]))
    long_float = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                                 (0, [("測試說明", "white")], "sub"),
                                 (1, [("這一句浮空文字真的太長", "white")], "float_left")])
    okl, rl = gate_shorts(long_float)
    check("S-S long float fails", not okl and any("S-S" in f for f in rl["fails"]))
    noisy = mk(caps_by_seg=[(0, [("測試地", "gold")], "impact"),
                            (0, [("測試說明", "white")], "ribbon"),
                            (1, [("內容一", "white")], "float_left"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    okn, rn = gate_shorts(noisy)
    check("S-S too many kinetic captions fail", not okn and any("動態字幕" in f for f in rn["fails"]))

    # expand_caps 不跨 cut + 同段平分
    caps = expand_caps(good)
    bounds = seg_bounds(good)
    inside = all(any(b0 - 0.01 <= s and e <= b1 + 0.01 for b0, b1 in bounds)
                 for s, e, _b, _k in caps)
    check("expanded caps never cross cuts", inside)
    seg0caps = [c for c in caps if c[0] < bounds[0][1]]
    check("same-seg captions split evenly", len(seg0caps) == 2 and seg0caps[0][1] < seg0caps[1][0])

    # assert_shorts 附地址軌
    done = assert_shorts(good)
    check("assert_shorts attaches addr track",
          any(k == "addr" for _s, _e, _b, k in done["caps"]))
    check("addr track spans whole video",
          any(k == "addr" and s <= 0.25 and e >= done["_dur"] - 0.3
              for s, e, _b, k in done["caps"]))
    done_noaddr = assert_shorts(mk(addr="", persistent_label_policy="omit"))
    check("omit policy does not attach addr track",
          not any(k == "addr" for _s, _e, _b, k in done_noaddr["caps"]))
    done_intro = assert_shorts(mk(persistent_label_policy="intro"))
    check("intro policy attaches a short semantic chip",
          any(k == "chip" and s >= .3 and e <= 3.01
              for s, e, _b, k in done_intro["caps"]))

def _selftest_semantic_rules(check, mk, good):
    # ── S-O 字幕節奏（warn 級）雙向驗證（M111：只驗會 warn 抓不到壞掉的規則）
    # ⚠️ 稀疏案例**必須保留 S-A 的開場兩條**，否則 gate 在 S-A 就 return，根本跑不到 S-O
    OPEN2 = [(0, [("測試地", "gold")], "hook"), (0, [("測試說明", "white")], "sub")]

    # 開場兩條 + 中間一條 = 3 條 / 13.5s ≈ 13.3 句/分（非白字 33% < 35% 不會先被 S-I 擋）
    sparse = mk(caps_by_seg=OPEN2 + [(1, [("內容一", "white")], "sub")])
    ok_sp, r_sp = gate_shorts(sparse)
    check("S-O 字幕太稀會 warn", any("S-O" in w for w in r_sp["warns"]))
    check("S-O 只 warn 不擋出片", ok_sp is True)
    check("S-O 回報 cap_rate/cap_dwell",
          r_sp.get("cap_rate") is not None and r_sp.get("cap_dwell") is not None)

    # 密：開場兩條 + 中間三段各三條 = 11 條 / 13.5s ≈ 48.9 句/分 → 不可以 warn
    dense = mk(caps_by_seg=OPEN2 + [(i, [("字%d%d" % (i, j), "white")], "sub")
                                    for i in (1, 2, 3) for j in range(3)])
    ok_dn, r_dn = gate_shorts(dense)
    check("S-O 字幕夠密不 warn", ok_dn and not any("S-O" in w for w in r_dn["warns"]))

    # ── S-P 高風險宣稱 lint（雙向：無佐證要擋、有佐證要放、平凡句不誤傷）
    risky = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                            (0, [("測試說明", "white")], "sub"),
                            (1, [("樹上停滿獨角仙", "white")], "sub"),
                            (2, [("內容二", "white")], "sub"),
                            (3, [("內容三", "white")], "sub")])
    okp, rp = gate_shorts(risky)
    check("S-P 絕對量詞無佐證被擋", not okp and any("S-P" in f for f in rp["fails"]))
    okp2, rp2 = gate_shorts(dict(risky, evidence={"樹上停滿獨角仙": "frame: IMG@1.4 數過 8 隻"}))
    check("S-P 附佐證即放行", okp2 and not any("S-P" in f for f in rp2["fails"]))
    for cls_txt in ("欄杆都是原木做的", "一盤裝三樣", "墨綠色水潭",
                    "世界最大跨距", "小菜吃到飽"):
        r_ = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                             (0, [("測試說明", "white")], "sub"),
                             (1, [(cls_txt, "white")], "sub"),
                             (2, [("內容二", "white")], "sub"),
                             (3, [("內容三", "white")], "sub")])
        ok_, rr_ = gate_shorts(r_)
        check("S-P 抓到 %r" % cls_txt[:6], not ok_ and any("S-P" in f for f in rr_["fails"]))
    check("S-P 平凡句不誤傷", gate_shorts(good)[0])   # good 無風險詞、無 evidence，必須過

def _selftest_first_frame_rules(check, mk, good):
    # ── S-Q 首幀品質（雙向：軟首幀要 warn、銳首幀不 warn；無 _scan.json 靜默跳過）
    import shutil as _sh
    import tempfile as _tf
    td = _tf.mkdtemp()
    try:
        clip = os.path.join(td, "C1.mp4")
        io_open = open(clip, "w")
        io_open.write("x")
        io_open.close()
        scan = {"clips": [
            {"name": "C1", "rows": [{"t": 2.0, "sharp": 12.0, "bright": 120},
                                    {"t": 5.0, "sharp": 31.0, "bright": 120}]},
            {"name": "C2", "rows": [{"t": 1.0, "sharp": 28.0, "bright": 120},
                                    {"t": 3.0, "sharp": 200.0, "bright": 240}]},  # 過曝不算候選
        ]}
        with open(os.path.join(td, "_scan.json"), "w", encoding="utf-8") as f:
            json.dump(scan, f)
        soft = mk(segs=[(clip, 2.0, 2.0), (clip, 5.0, 3.0), (clip, 9.0, 3.0),
                        (clip, 13.0, 3.5), (clip, 0.0, 2.0)])
        _oq, rq = gate_shorts(soft)
        check("S-Q 軟首幀（12 vs 31）會 warn", any("S-Q" in w for w in rq["warns"]))
        check("S-Q 過曝幀不當候選", not any("200" in w for w in rq["warns"]))
        sharp_ff = mk(segs=[(clip, 5.0, 2.0), (clip, 9.0, 3.0), (clip, 2.0, 3.0),
                            (clip, 13.0, 3.5), (clip, 3.0, 2.0)])
        _oq2, rq2 = gate_shorts(sharp_ff)
        check("S-Q 銳首幀（31=池最高）不 warn", not any("S-Q" in w for w in rq2["warns"]))
        check("S-Q 無 _scan.json 靜默跳過", not any("S-Q" in w for w in gate_shorts(good)[1]["warns"]))
    finally:
        _sh.rmtree(td, ignore_errors=True)

def _selftest_reading_rules(check, mk, good):
    # ── S-R 閱讀速率（雙向：讀不完要擋、偏快要 warn、正常不誤傷）
    # seg0 兩條各 ~0.74s：14 字 = 18.9 字/秒 → fail
    toolong = mk(caps_by_seg=[(0, [("測試地", "gold")], "hook"),
                              (0, [("排骨蛋炒飯號稱平價版鼎泰豐", "white")], "sub"),
                              (1, [("內容一", "white")], "sub"),
                              (2, [("內容二", "white")], "sub"),
                              (3, [("內容三", "white")], "sub")])
    okr, rr = gate_shorts(toolong)
    check("S-R 讀不完（18.9 字/秒）被擋", not okr and any("S-R" in f for f in rr["fails"]))
    check("S-R 正常長句不誤傷",                      # 7 字配 2.7s 段 = 2.9 字/秒
          not any("S-R" in w for w in gate_shorts(mk(caps_by_seg=[
              (0, [("測試地", "gold")], "hook"),
              (1, [("七個字的內容句", "white")], "sub"),
              (2, [("內容二", "white")], "sub"),
              (3, [("內容三", "white")], "sub")]))[1]["warns"]))
    check("S-R 偏快（5.4 字/秒）有 warn",            # base seg0 第二條 4 字/0.74s
          any("S-R" in w for w in gate_shorts(good)[1]["warns"]))

    # assert_shorts 不過必須 raise（訊息帶片名 + Shorts gate FAIL）
    try:
        assert_shorts(mk(addr=""))
        check("assert_shorts raises on fail", False)
    except AssertionError as e:
        check("assert_shorts raises on fail", "Shorts gate FAIL" in str(e))


def _selftest_body(check):
    dummy, mk, good = _selftest_fixture()
    _selftest_battle_rules(check, mk, good)
    _selftest_gate_rules(check, dummy, mk, good)
    _selftest_caption_rendering(check, mk, good)
    _selftest_semantic_rules(check, mk, good)
    _selftest_first_frame_rules(check, mk, good)
    _selftest_reading_rules(check, mk, good)


def _selftest() -> int:
    return selftest_runner(_selftest_body, width=52)


if __name__ == "__main__":
    raise SystemExit(_selftest())
